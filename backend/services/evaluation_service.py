"""
IoTSynth AI - Synthetic Data Statistical Quality Evaluation Service
"""

from datetime import datetime, timezone
from pathlib import Path
import json
import re
from typing import Any, Dict, List, Optional
import uuid

from backend.config import Settings, get_settings
from backend.exceptions import BadRequestError, ResourceNotFoundError
from backend.schemas.evaluation import (
    EvaluationDetailResponse,
    EvaluationResultSummary,
    EvaluationResultsListResponse,
    EvaluationRunRequest,
    EvaluationRunResponse,
    EvaluationStatusResponse,
)
from synthetic_engine.ctgan_model import CTGANModel
from synthetic_engine.evaluation.orchestrator import EvaluationPipelineOrchestrator


class EvaluationService:
    """Service layer executing isolated quantitative fidelity & validity audits."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.APPROVED_REFERENCE_DATASETS: Dict[str, Path] = {
            "ciciot2023_preprocessed_sample": self.settings.DATASETS_PROCESSED_DIR
            / "ciciot2023_preprocessed_sample.parquet",
        }

    def _discover_synthetic_datasets(self) -> Dict[str, Path]:
        discovered: Dict[str, Path] = {}
        for gen_dir in reversed(self.settings.iter_generated_search_dirs()):
            if not gen_dir.exists():
                continue
            for ext in ("*.csv", "*.parquet"):
                for fp in sorted(gen_dir.glob(ext)):
                    if fp.is_file() and re.match(r"^[a-zA-Z0-9_\-]+$", fp.stem):
                        discovered[fp.stem] = fp
        return discovered

    def get_status(self) -> EvaluationStatusResponse:
        synth_map = self._discover_synthetic_datasets()
        return EvaluationStatusResponse(
            engine_available=True,
            engine_class="EvaluationPipelineOrchestrator",
            available_reference_datasets=list(self.APPROVED_REFERENCE_DATASETS.keys()),
            available_synthetic_datasets=list(synth_map.keys()),
            capabilities=[
                "schema_and_domain_validity",
                "statistical_similarity_ks_ws_js",
                "feature_correlation_mace",
                "class_distribution_fidelity",
                "diversity_and_memorization_analysis",
                "device_aware_44_to_42_projection",
            ],
        )

    def run_evaluation(self, request: EvaluationRunRequest) -> EvaluationRunResponse:
        if request.reference_dataset_id not in self.APPROVED_REFERENCE_DATASETS:
            raise BadRequestError(
                f"Unknown reference dataset '{request.reference_dataset_id}'."
            )
        synth_map = self._discover_synthetic_datasets()
        if request.synthetic_dataset_id not in synth_map:
            raise BadRequestError(
                f"Dataset '{request.synthetic_dataset_id}' not found in datasets/generated/."
            )

        ref_file = self.APPROVED_REFERENCE_DATASETS[request.reference_dataset_id]
        synth_file = synth_map[request.synthetic_dataset_id]
        if not ref_file.exists():
            raise ResourceNotFoundError("Reference Dataset File", str(ref_file.name))
        if not synth_file.exists():
            raise ResourceNotFoundError("Synthetic Dataset File", str(synth_file.name))

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        evaluation_id = f"eval_{timestamp_str}_{uuid.uuid4().hex[:6]}"
        run_reports_dir = self.settings.EVALUATION_RUNS_DIR / evaluation_id
        run_reports_dir.mkdir(parents=True, exist_ok=True)

        _, _, default_v1_weights = CTGANModel.resolve_artifact_paths(
            self.settings.CTGAN_MODELS_DIR, "ctgan_full_v1", for_write=False
        )
        orchestrator = EvaluationPipelineOrchestrator(
            reports_dir=str(run_reports_dir),
            model_path=str(default_v1_weights),
        )
        eval_output = orchestrator.run_full_evaluation(
            reference_path=str(ref_file),
            synthetic_path=str(synth_file),
            generate_plots=False,
            generate_corrected_dataset=False,
            test_conditional_sampling=request.test_conditional_sampling,
        )

        stat_full = eval_output.get("statistical_similarity", {})
        stat_summary = stat_full.get("summary_metrics", {})
        corr_summary = eval_output.get("feature_correlation", {}).get("summary", {})
        div_full = eval_output.get("diversity_and_memorization", {})
        div_summary = div_full.get("summary", {})
        nn_summary = div_full.get("nearest_neighbor_distance", {})

        summary_metrics = {
            "average_ks_statistic_vs_train": stat_summary.get("average_ks_statistic_vs_train"),
            "average_wasserstein_distance_vs_train": stat_summary.get("average_wasserstein_distance_vs_train"),
            "average_jensen_shannon_distance_vs_train": stat_summary.get("average_jensen_shannon_distance_vs_train"),
            "pearson_mace": corr_summary.get("pearson_mace"),
            "spearman_mace": corr_summary.get("spearman_mace"),
            "exact_duplicate_rows_in_train": div_summary.get("exact_training_overlaps", 0),
            "min_nearest_neighbor_distance": nn_summary.get("min_distance"),
            "median_nearest_neighbor_distance": nn_summary.get("median_distance"),
        }

        return EvaluationRunResponse(
            evaluation_id=evaluation_id,
            status="completed",
            timestamp=datetime.now(timezone.utc).isoformat(),
            reference_dataset_id=request.reference_dataset_id,
            synthetic_dataset_id=request.synthetic_dataset_id,
            summary_metrics=summary_metrics,
            reports={
                "data_validity": eval_output.get("data_validity", {}),
                "statistical_similarity": stat_full,
                "feature_correlation": eval_output.get("feature_correlation", {}),
                "class_distribution": eval_output.get("class_distribution", {}).get("distribution_comparison", {}),
                "diversity_summary": div_full,
            },
            isolated_reports_dir=str(run_reports_dir.relative_to(self.settings.PROJECT_ROOT)),
        )

    def list_results(self) -> EvaluationResultsListResponse:
        results: List[EvaluationResultSummary] = []

        phase6_dir = self.settings.PHASE6_REPORTS_DIR
        if phase6_dir.exists():
            reports_found = [
                n.replace(".json", "")
                for n in [
                    "data_validity_report.json",
                    "statistical_similarity_report.json",
                    "feature_correlation_report.json",
                    "class_distribution_report.json",
                    "diversity_report.json",
                    "three_candidate_comparison.json",
                ]
                if (phase6_dir / n).exists()
            ]
            if reports_found:
                results.append(
                    EvaluationResultSummary(
                        evaluation_id="phase6_approved",
                        title="Baseline CTGAN Benchmark Audit (5,000 Flows vs CICIoT2023)",
                        source="baseline_benchmark",
                        created_at="Baseline Reference",
                        available_reports=reports_found,
                    )
                )

        runs_dir = self.settings.EVALUATION_RUNS_DIR
        if runs_dir.exists():
            for item in sorted(runs_dir.iterdir(), reverse=True):
                if item.is_dir() and item.name.startswith("eval_"):
                    results.append(
                        EvaluationResultSummary(
                            evaluation_id=item.name,
                            title=f"Live Dataset Audit ({item.name})",
                            source="isolated_run",
                            created_at=datetime.fromtimestamp(item.stat().st_mtime, tz=timezone.utc).isoformat(),
                            available_reports=[f.stem for f in item.glob("*.json")],
                        )
                    )

        return EvaluationResultsListResponse(total_results=len(results), results=results)

    def get_result_detail(self, evaluation_id: str) -> EvaluationDetailResponse:
        if not re.match(r"^[a-zA-Z0-9_\-]+$", evaluation_id):
            raise BadRequestError(f"Invalid evaluation_id '{evaluation_id}'.")

        if evaluation_id in ("phase6", "phase6_approved"):
            target_dir = self.settings.PHASE6_REPORTS_DIR
            source = "baseline_benchmark"
        else:
            target_dir = (self.settings.EVALUATION_RUNS_DIR / evaluation_id).resolve()
            source = "isolated_run"

        if not self.settings.is_safe_path(target_dir) or not target_dir.is_dir():
            raise ResourceNotFoundError("Evaluation Result", evaluation_id)

        def load_json_report(filename: str) -> Optional[Dict[str, Any]]:
            rf = target_dir / filename
            if rf.exists() and rf.is_file():
                try:
                    with open(rf, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    return None
            return None

        return EvaluationDetailResponse(
            evaluation_id=evaluation_id,
            source=source,
            data_validity=load_json_report("data_validity_report.json"),
            statistical_similarity=load_json_report("statistical_similarity_report.json"),
            feature_correlation=load_json_report("feature_correlation_report.json"),
            class_distribution=load_json_report("class_distribution_report.json"),
            diversity_and_memorization=load_json_report("diversity_report.json"),
            three_candidate_comparison=load_json_report("three_candidate_comparison.json"),
        )
