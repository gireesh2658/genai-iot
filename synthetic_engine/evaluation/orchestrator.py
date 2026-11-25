"""
IoTSynth AI - Evaluation Pipeline Orchestrator
Executes statistical quality, validity, correlation, class distribution, and diversity audits.
"""

import json
import os
from typing import Any, Dict

from synthetic_engine.ctgan_model import CTGANModel
from synthetic_engine.evaluation.classes import ClassDistributionEvaluator
from synthetic_engine.evaluation.correlation import FeatureCorrelationEvaluator
from synthetic_engine.evaluation.data_loader import (
    LoadedEvaluationDatasets,
    load_evaluation_datasets,
)
from synthetic_engine.evaluation.diversity import DiversityAndMemorizationEvaluator
from synthetic_engine.evaluation.statistical import StatisticalDistributionEvaluator
from synthetic_engine.evaluation.validity import SyntheticDataValidityEvaluator


class EvaluationPipelineOrchestrator:
    """Coordinates quantitative synthetic quality evaluation across all statistical axes."""

    def __init__(
        self,
        reports_dir: str = "reports/phase6",
        plots_dir: str = "reports/phase6",
        model_path: str = "models/ctgan/v1/ctgan_full_v1.pkl",
    ):
        self.reports_dir = reports_dir
        self.plots_dir = plots_dir
        self.model_path = model_path
        os.makedirs(self.reports_dir, exist_ok=True)

    def run_full_evaluation(
        self,
        reference_path: str = "datasets/processed/ciciot2023_preprocessed_sample.parquet",
        synthetic_path: str = "datasets/generated/ctgan_initial_sample_v1_domain_corrected.parquet",
        generate_plots: bool = False,
        generate_corrected_dataset: bool = False,
        test_conditional_sampling: bool = False,
    ) -> Dict[str, Any]:
        """Execute end-to-end quantitative evaluation workflow."""
        datasets: LoadedEvaluationDatasets = load_evaluation_datasets(
            reference_path=reference_path,
            synthetic_path=synthetic_path,
        )
        train_df = datasets.train_df
        val_df = datasets.val_df
        synth_df = datasets.synth_df
        meta = datasets.metadata

        # 1. Domain & Semantic Validity
        validity_evaluator = SyntheticDataValidityEvaluator()
        validity_res = validity_evaluator.evaluate_all(synth_df, expected_columns=list(train_df.columns))
        with open(os.path.join(self.reports_dir, "data_validity_report.json"), "w", encoding="utf-8") as f:
            json.dump(validity_res, f, indent=2)

        # 2. Marginal Statistical Similarity (KS, Wasserstein, JS)
        stat_evaluator = StatisticalDistributionEvaluator()
        stat_res = stat_evaluator.evaluate_distributions(
            real_train=train_df,
            real_val=val_df,
            synth_df=synth_df,
            discrete_columns=meta["discrete_columns"],
        )
        with open(os.path.join(self.reports_dir, "statistical_similarity_report.json"), "w", encoding="utf-8") as f:
            json.dump(stat_res, f, indent=2)

        # 3. Multivariate Correlation Preservation (Pearson & Spearman MACE)
        corr_evaluator = FeatureCorrelationEvaluator()
        corr_res = corr_evaluator.evaluate_all(real_df=train_df, synth_df=synth_df)
        with open(os.path.join(self.reports_dir, "feature_correlation_report.json"), "w", encoding="utf-8") as f:
            json.dump(corr_res, f, indent=2)

        # 4. Class Distribution & Optional Conditional Fidelity
        class_evaluator = ClassDistributionEvaluator()
        class_dist_res = class_evaluator.compare_class_distributions(
            real_train=train_df,
            real_val=val_df,
            synth_df=synth_df,
        )

        cond_gen_res = []
        if test_conditional_sampling and os.path.exists(self.model_path):
            try:
                model_name = os.path.splitext(os.path.basename(self.model_path))[0]
                model = CTGANModel.load(
                    directory=os.path.dirname(os.path.dirname(self.model_path)),
                    model_name=model_name,
                )
                cond_gen_res = class_evaluator.evaluate_conditional_generation(model)
            except Exception:
                cond_gen_res = []

        class_full_report = {
            "distribution_comparison": class_dist_res,
            "conditional_generation_evaluation": cond_gen_res,
        }
        with open(os.path.join(self.reports_dir, "class_distribution_report.json"), "w", encoding="utf-8") as f:
            json.dump(class_full_report, f, indent=2)

        # 5. Diversity & Memorization Analysis
        diversity_evaluator = DiversityAndMemorizationEvaluator()
        diversity_res = diversity_evaluator.evaluate_all(real_train=train_df, synth_df=synth_df)
        with open(os.path.join(self.reports_dir, "diversity_report.json"), "w", encoding="utf-8") as f:
            json.dump(diversity_res, f, indent=2)

        return {
            "metadata": meta,
            "data_validity": validity_res,
            "statistical_similarity": stat_res,
            "feature_correlation": corr_res,
            "class_distribution": class_full_report,
            "diversity_and_memorization": diversity_res,
        }
