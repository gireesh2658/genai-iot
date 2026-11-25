"""
IoTSynth AI - Backend Service for Anomaly Detection API (Phase 8.2.4)
Manages model discovery, lazy artifact loading, input validation, and inference.
Guarantees thread-safe process-local caching, zero startup weight loading,
strict 38-feature canonical alignment, and leakage prevention.
"""

from datetime import datetime, timezone
import json
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd

from backend.config import Settings, get_settings
from backend.exceptions import (
    BadRequestError,
    InvalidFeatureSchemaError,
    ResourceNotFoundError,
)
from backend.schemas.anomaly import (
    AnomalyModelDetailResponse,
    AnomalyModelListResponse,
    AnomalyModelSummary,
    AnomalyTrainRequest,
    AnomalyTrainResponse,
    ExperimentComparisonResponse,
    ExperimentListResponse,
    PredictBatchRequest,
    PredictBatchResponse,
    PredictionItem,
    PredictSingleRequest,
    PredictSingleResponse,
)
from anomaly_detection.data_loader import AnomalyDetectionDataLoader, compute_file_sha256
from anomaly_detection.evaluator import AnomalyDetectionEvaluator
from anomaly_detection.experiment_config import (
    ExperimentConfig,
    SYNTHETIC_DATA_QUALITY_WARNINGS,
    ExperimentType,
)
from anomaly_detection.feature_config import (
    CANONICAL_MODEL_FEATURES,
    EXCLUDED_FEATURES,
    EXPECTED_LABEL_CATEGORIES,
    PRIMARY_TARGET,
)
from anomaly_detection.model_factory import (
    SUPPORTED_BASELINE_MODELS,
    create_baseline_pipeline,
    get_model_metadata,
)


class AnomalyService:
    """Service layer managing trained Scikit-learn anomaly detection models and inference.

    Architectural Invariant:
    Zero model weights are loaded during application startup or service instantiation.
    Artifacts are loaded strictly on-demand (lazy loading) and cached within a thread-safe
    process-local registry. Note that separate Uvicorn worker processes maintain independent
    in-memory caches.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

        # Process-local model cache protected by thread-safe reentrant lock
        self._model_cache: Dict[str, Any] = {}
        self._cache_lock = threading.Lock()

        # Build registry of all 20 approved model artifacts
        self.APPROVED_MODELS: Dict[str, Dict[str, Any]] = self._build_model_registry()

    def _build_model_registry(self) -> Dict[str, Dict[str, Any]]:
        """Construct static registry of the 20 approved models across TRTR, TSTR, and TSTR+R."""
        registry: Dict[str, Dict[str, Any]] = {}
        classifiers = [
            "extra_trees",
            "hist_gradient_boosting",
            "logistic_regression",
            "random_forest",
        ]

        # 1. TRTR Models (4)
        for clf in classifiers:
            model_id = f"{clf}_trtr"
            registry[model_id] = {
                "model_id": model_id,
                "classifier_name": clf,
                "experiment_type": ExperimentType.TRTR.value,
                "augmentation_percentage": None,
                "file_path": Path("anomaly_detection/models") / f"{model_id}.joblib",
                "metrics_path": Path("anomaly_detection/results") / f"{clf}_metrics.json",
                "cm_path": Path("anomaly_detection/results") / f"{clf}_confusion_matrix.json",
                "is_custom": False,
            }

        # 2. TSTR Models (4)
        for clf in classifiers:
            model_id = f"{clf}_tstr"
            registry[model_id] = {
                "model_id": model_id,
                "classifier_name": clf,
                "experiment_type": ExperimentType.TSTR.value,
                "augmentation_percentage": None,
                "file_path": Path("anomaly_detection/models/tstr") / f"{model_id}.joblib",
                "metrics_path": Path("anomaly_detection/results/tstr") / f"{clf}_metrics.json",
                "cm_path": Path("anomaly_detection/results/tstr") / f"{clf}_confusion_matrix.json",
                "is_custom": False,
            }

        # 3. TSTR+R Models (12)
        for clf in classifiers:
            for aug in [25, 50, 100]:
                model_id = f"{clf}_tstr_r_{aug}"
                registry[model_id] = {
                    "model_id": model_id,
                    "classifier_name": clf,
                    "experiment_type": ExperimentType.TSTR_PLUS_R.value,
                    "augmentation_percentage": aug,
                    "file_path": Path("anomaly_detection/models/tstr_plus_r") / f"{model_id}.joblib",
                    "metrics_path": Path("anomaly_detection/results/tstr_plus_r") / f"{model_id}_metrics.json",
                    "cm_path": Path("anomaly_detection/results/tstr_plus_r") / f"{model_id}_confusion_matrix.json",
                    "is_custom": False,
                }

        assert len(registry) == 20, f"Expected exactly 20 approved models, got {len(registry)}"
        return registry

    def _discover_custom_models(self) -> Dict[str, Dict[str, Any]]:
        """Discover user-trained custom anomaly detection models on disk."""
        custom: Dict[str, Dict[str, Any]] = {}
        custom_dir = self.settings.CUSTOM_ANOMALY_MODELS_DIR
        results_dir = self.settings.CUSTOM_ANOMALY_RESULTS_DIR
        if not custom_dir.exists():
            return custom

        for model_file in sorted(custom_dir.glob("*.joblib"), key=lambda p: p.stat().st_mtime, reverse=True):
            mid = model_file.stem
            if not re.match(r"^[a-zA-Z0-9_\-]+$", mid):
                continue
            metrics_file = results_dir / f"{mid}_metrics.json"
            cm_file = results_dir / f"{mid}_confusion_matrix.json"
            metrics_data = (
                self._read_metrics_file(metrics_file.relative_to(self.settings.PROJECT_ROOT))
                if metrics_file.exists()
                else {}
            )
            custom[mid] = {
                "model_id": mid,
                "classifier_name": metrics_data.get("model_name", "custom"),
                "experiment_type": metrics_data.get("experiment_type", "CUSTOM"),
                "augmentation_percentage": metrics_data.get("augmentation_percentage"),
                "file_path": model_file.relative_to(self.settings.PROJECT_ROOT),
                "metrics_path": metrics_file.relative_to(self.settings.PROJECT_ROOT) if metrics_file.exists() else None,
                "cm_path": cm_file.relative_to(self.settings.PROJECT_ROOT) if cm_file.exists() else None,
                "is_custom": True,
                "synthetic_source": (metrics_data.get("provenance_info") or {}).get("synthetic_dataset_id"),
            }
        return custom

    def _resolve_model_info(self, model_id: str) -> Dict[str, Any]:
        """Resolve either one of the 20 baseline models or a custom trained model."""
        if model_id in self.APPROVED_MODELS:
            return self.APPROVED_MODELS[model_id]
        custom = self._discover_custom_models()
        if model_id in custom:
            return custom[model_id]
        raise ResourceNotFoundError("Anomaly Model", model_id)

    def is_model_loaded(self, model_id: str) -> bool:
        """Check whether a model's weights are currently resident in this worker's memory."""
        return model_id in self._model_cache

    def get_or_load_model(self, model_id: str) -> Any:
        """Retrieve model from cache or load lazily from disk with thread-safe locking."""
        info = self._resolve_model_info(model_id)

        # Fast-path check without acquiring lock
        if model_id in self._model_cache:
            return self._model_cache[model_id]

        with self._cache_lock:
            # Double-checked locking pattern
            if model_id not in self._model_cache:
                model_path = self.settings.PROJECT_ROOT / info["file_path"]
                if not model_path.exists():
                    raise ResourceNotFoundError("Model Artifact File", str(info["file_path"]))

                # Load scikit-learn pipeline artifact
                loaded_pipeline = joblib.load(model_path)
                self._model_cache[model_id] = loaded_pipeline

            return self._model_cache[model_id]

    def list_models(self) -> AnomalyModelListResponse:
        """List all 20 approved baseline models plus any custom-trained models."""
        summaries: List[AnomalyModelSummary] = []

        all_entries = list(self.APPROVED_MODELS.items()) + list(self._discover_custom_models().items())
        for model_id, info in all_entries:
            metrics_path = info.get("metrics_path")
            metrics_data = self._read_metrics_file(metrics_path) if metrics_path else {}
            overall_metrics = metrics_data.get("overall_metrics", {})

            summaries.append(
                AnomalyModelSummary(
                    model_id=model_id,
                    classifier_name=info["classifier_name"],
                    experiment_type=info["experiment_type"],
                    augmentation_percentage=info.get("augmentation_percentage"),
                    is_loaded=self.is_model_loaded(model_id),
                    is_custom=bool(info.get("is_custom", False)),
                    synthetic_source=info.get("synthetic_source"),
                    train_records=metrics_data.get("train_records"),
                    supported_capabilities=["predict", "predict_proba"],
                    macro_f1=overall_metrics.get("macro_f1"),
                    balanced_accuracy=overall_metrics.get("balanced_accuracy"),
                )
            )

        return AnomalyModelListResponse(
            total_models=len(summaries),
            loaded_models_count=len(self._model_cache),
            models=summaries,
        )

    def get_model_detail(self, model_id: str) -> AnomalyModelDetailResponse:
        """Retrieve comprehensive metadata, metrics, and confusion matrix for an approved or custom model."""
        info = self._resolve_model_info(model_id)
        metrics_path = info.get("metrics_path")
        metrics_data = self._read_metrics_file(metrics_path) if metrics_path else {}
        cm_path = info.get("cm_path")
        cm_data = self._read_metrics_file(cm_path) if cm_path else None

        steps = ["classifier"]
        if info["classifier_name"] == "logistic_regression":
            steps = ["scaler", "classifier"]

        return AnomalyModelDetailResponse(
            model_id=model_id,
            classifier_name=info["classifier_name"],
            experiment_type=info["experiment_type"],
            augmentation_percentage=info.get("augmentation_percentage"),
            is_loaded=self.is_model_loaded(model_id),
            features_count=len(CANONICAL_MODEL_FEATURES),
            target_column=PRIMARY_TARGET,
            classes=EXPECTED_LABEL_CATEGORIES,
            pipeline_steps=steps,
            train_records=metrics_data.get("train_records"),
            val_records=metrics_data.get("val_records"),
            model_file_sha256=metrics_data.get("model_file_sha256"),
            overall_metrics=metrics_data.get("overall_metrics"),
            per_class_metrics=metrics_data.get("per_class_metrics"),
            confusion_matrix=cm_data or None,
            hyperparameters=metrics_data.get("model_metadata", {}).get("hyperparameters"),
            provenance_info=metrics_data.get("provenance_info"),
            is_custom=bool(info.get("is_custom", False)),
        )

    def _resolve_generated_dataset_file(self, dataset_id: str) -> Path:
        """Safely locate a .parquet or .csv synthetic/simulator dataset inside generated search dirs."""
        clean_id = dataset_id.strip()
        if not re.match(r"^[a-zA-Z0-9_\-]+$", clean_id):
            raise BadRequestError(
                f"Invalid synthetic_dataset_id '{dataset_id}'. Alphanumeric, hyphens, and underscores only."
            )
        for raw_dir in self.settings.iter_generated_search_dirs():
            gen_dir = raw_dir.resolve()
            for ext in (".parquet", ".csv"):
                candidate = (gen_dir / f"{clean_id}{ext}").resolve()
                if candidate.is_relative_to(gen_dir) and candidate.exists() and candidate.is_file():
                    return candidate
        raise ResourceNotFoundError("Synthetic dataset", clean_id)

    def train_model(self, request: AnomalyTrainRequest) -> AnomalyTrainResponse:
        """Train and evaluate a classifier on TRTR, TSTR, or TSTR+R (including minority-balanced augmentation)."""
        clf_name = request.classifier_name.strip().lower()
        if clf_name not in SUPPORTED_BASELINE_MODELS:
            raise BadRequestError(
                f"Unsupported classifier '{request.classifier_name}'. Supported: {SUPPORTED_BASELINE_MODELS}"
            )

        exp_upper = request.experiment_type.strip().upper()
        if exp_upper not in ("TRTR", "TSTR", "TSTR+R"):
            raise BadRequestError(
                f"Unsupported experiment_type '{request.experiment_type}'. Choose from: TRTR, TSTR, TSTR+R."
            )

        exp_enum = (
            ExperimentType.TRTR if exp_upper == "TRTR"
            else (ExperimentType.TSTR if exp_upper == "TSTR" else ExperimentType.TSTR_PLUS_R)
        )
        cfg = ExperimentConfig(experiment_type=exp_enum, target_column=PRIMARY_TARGET, random_seed=request.random_seed)
        loader = AnomalyDetectionDataLoader(cfg)
        real_train_split, real_val_split = loader.load_real_train_and_val_splits()

        synthetic_used_count = 0
        synth_sha256: Optional[str] = None
        synth_dataset_id = request.synthetic_dataset_id if exp_upper != "TRTR" else None

        if exp_upper == "TRTR":
            train_X = real_train_split.X
            train_y = real_train_split.y
        else:
            if not request.synthetic_dataset_id:
                raise BadRequestError("synthetic_dataset_id is required for TSTR and TSTR+R training.")
            synth_path = self._resolve_generated_dataset_file(request.synthetic_dataset_id)
            synth_sha256 = compute_file_sha256(str(synth_path))
            synth_df = loader.load_file(str(synth_path))
            synth_df = synth_df.drop(columns=["device_id", "device_category"], errors="ignore")
            loader.validate_dataframe(synth_df, target_col=PRIMARY_TARGET, dataset_name=synth_path.name)

            n_target = max(1, min(len(synth_df), int(round(len(synth_df) * request.augmentation_fraction))))
            rng = np.random.default_rng(request.random_seed)

            if exp_upper == "TSTR+R" and request.balance_minority_classes:
                real_counts = real_train_split.y.value_counts().to_dict()
                rare_order = sorted(synth_df[PRIMARY_TARGET].unique().tolist(), key=lambda c: real_counts.get(c, 0))
                selected_parts: List[pd.DataFrame] = []
                remaining_budget = n_target
                for cls_label in rare_order:
                    if remaining_budget <= 0:
                        break
                    cls_rows = synth_df[synth_df[PRIMARY_TARGET] == cls_label]
                    real_n = real_counts.get(cls_label, 0)
                    cap = len(cls_rows) if real_n < 2000 else max(1, min(len(cls_rows), n_target // max(1, len(rare_order))))
                    take = min(cap, remaining_budget, len(cls_rows))
                    if take > 0:
                        perm = rng.permutation(len(cls_rows))[:take]
                        selected_parts.append(cls_rows.iloc[perm])
                        remaining_budget -= take
                if remaining_budget > 0:
                    chosen_idx = pd.concat(selected_parts).index if selected_parts else pd.Index([])
                    leftover = synth_df.drop(index=chosen_idx)
                    if len(leftover) > 0:
                        extra_take = min(remaining_budget, len(leftover))
                        perm = rng.permutation(len(leftover))[:extra_take]
                        selected_parts.append(leftover.iloc[perm])
                sampled_synth = pd.concat(selected_parts, ignore_index=True) if selected_parts else synth_df.iloc[:0]
            else:
                perm = rng.permutation(len(synth_df))[:n_target]
                sampled_synth = synth_df.iloc[perm].copy()

            synth_X = sampled_synth[CANONICAL_MODEL_FEATURES].copy()
            synth_y = sampled_synth[PRIMARY_TARGET].copy()
            synthetic_used_count = len(sampled_synth)

            if exp_upper == "TSTR":
                train_X = synth_X
                train_y = synth_y
            else:
                train_X = pd.concat([real_train_split.X, synth_X], ignore_index=True)
                train_y = pd.concat([real_train_split.y, synth_y], ignore_index=True)

        pipeline = create_baseline_pipeline(model_name=clf_name, random_state=request.random_seed)
        metadata = get_model_metadata(model_name=clf_name, pipeline=pipeline, random_state=request.random_seed)

        start_fit = time.perf_counter()
        pipeline.fit(train_X, train_y)
        fit_duration = round(time.perf_counter() - start_fit, 4)

        val_X, val_y = real_val_split.X, real_val_split.y
        y_pred = pipeline.predict(val_X)
        y_prob = pipeline.predict_proba(val_X) if hasattr(pipeline, "predict_proba") else None

        evaluator = AnomalyDetectionEvaluator(target_categories=list(EXPECTED_LABEL_CATEGORIES))
        eval_result = evaluator.evaluate_predictions(
            y_true=val_y,
            y_pred=y_pred,
            y_prob=y_prob,
            model_name=clf_name,
            fit_duration_seconds=fit_duration,
            inference_duration_seconds=0.0,
        )

        clean_tag = re.sub(r"[^a-zA-Z0-9_\-]", "_", (request.model_tag or "").strip())
        ts_suffix = f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
        exp_slug = exp_upper.lower().replace("+", "_plus_")
        model_id = f"custom_{clean_tag}" if clean_tag else f"custom_{clf_name}_{exp_slug}_{ts_suffix}"

        models_dir = self.settings.CUSTOM_ANOMALY_MODELS_DIR
        results_dir = self.settings.CUSTOM_ANOMALY_RESULTS_DIR
        models_dir.mkdir(parents=True, exist_ok=True)
        results_dir.mkdir(parents=True, exist_ok=True)

        model_path = models_dir / f"{model_id}.joblib"
        metrics_path = results_dir / f"{model_id}_metrics.json"
        cm_path = results_dir / f"{model_id}_confusion_matrix.json"

        joblib.dump(pipeline, model_path)
        sha256_hash = compute_file_sha256(str(model_path))

        provenance = {
            "synthetic_dataset_id": synth_dataset_id,
            "synthetic_sha256": synth_sha256,
            "augmentation_fraction": request.augmentation_fraction if exp_upper != "TRTR" else 0.0,
            "balance_minority_classes": request.balance_minority_classes if exp_upper == "TSTR+R" else False,
            "synthetic_records_used": synthetic_used_count,
            "real_train_records_used": real_train_split.n_records if exp_upper != "TSTR" else 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        quality_warnings = list(SYNTHETIC_DATA_QUALITY_WARNINGS) if exp_upper != "TRTR" else []

        metrics_payload = {
            "model_name": clf_name,
            "experiment_type": exp_upper,
            "augmentation_percentage": int(round(request.augmentation_fraction * 100)) if exp_upper == "TSTR+R" else None,
            "target_column": PRIMARY_TARGET,
            "train_records": len(train_X),
            "val_records": len(val_X),
            "features_count": len(CANONICAL_MODEL_FEATURES),
            "fit_duration_seconds": fit_duration,
            "overall_metrics": eval_result["overall_metrics"],
            "per_class_metrics": eval_result["per_class_metrics"],
            "model_metadata": metadata,
            "provenance_info": provenance,
            "quality_warnings": quality_warnings,
            "model_file_sha256": sha256_hash,
        }
        with open(metrics_path, "w", encoding="utf-8") as mf:
            json.dump(metrics_payload, mf, indent=2)
        with open(cm_path, "w", encoding="utf-8") as cf:
            json.dump(eval_result["confusion_matrix"], cf, indent=2)

        with self._cache_lock:
            self._model_cache[model_id] = pipeline

        trtr_info = self.APPROVED_MODELS.get(f"{clf_name}_trtr")
        trtr_metrics = self._read_metrics_file(trtr_info["metrics_path"]) if trtr_info else {}
        trtr_overall = trtr_metrics.get("overall_metrics", {})
        trtr_per_class = trtr_metrics.get("per_class_metrics", {})

        trtr_f1 = trtr_overall.get("macro_f1")
        trtr_bal = trtr_overall.get("balanced_accuracy")
        new_f1 = eval_result["overall_metrics"].get("macro_f1", 0.0)
        new_bal = eval_result["overall_metrics"].get("balanced_accuracy", 0.0)

        per_class_deltas: Dict[str, float] = {}
        for cls_name in EXPECTED_LABEL_CATEGORIES:
            base_c = (trtr_per_class.get(cls_name) or {}).get("f1_score")
            new_c = (eval_result["per_class_metrics"].get(cls_name) or {}).get("f1_score")
            if isinstance(base_c, (int, float)) and isinstance(new_c, (int, float)):
                per_class_deltas[cls_name] = round(float(new_c) - float(base_c), 4)

        return AnomalyTrainResponse(
            status="completed",
            model_id=model_id,
            classifier_name=clf_name,
            experiment_type=exp_upper,
            synthetic_dataset_id=synth_dataset_id,
            train_records=len(train_X),
            synthetic_records_used=synthetic_used_count,
            val_records=len(val_X),
            fit_duration_seconds=fit_duration,
            overall_metrics=eval_result["overall_metrics"],
            per_class_metrics=eval_result["per_class_metrics"],
            trtr_baseline_macro_f1=trtr_f1,
            macro_f1_delta_vs_trtr=round(float(new_f1) - float(trtr_f1), 4) if isinstance(trtr_f1, (int, float)) else None,
            balanced_accuracy_delta_vs_trtr=round(float(new_bal) - float(trtr_bal), 4) if isinstance(trtr_bal, (int, float)) else None,
            per_class_f1_deltas_vs_trtr=per_class_deltas,
            confusion_matrix=eval_result["confusion_matrix"],
            quality_warnings=quality_warnings,
        )

    def delete_custom_model(self, model_id: str) -> Dict[str, Any]:
        """Delete a user-trained custom model artifact while protecting the 20 Phase 7 baselines."""
        if model_id in self.APPROVED_MODELS:
            raise BadRequestError(
                f"Baseline benchmark model '{model_id}' cannot be deleted."
            )
        custom = self._discover_custom_models()
        if model_id not in custom:
            raise ResourceNotFoundError("Custom Anomaly Model", model_id)

        with self._cache_lock:
            self._model_cache.pop(model_id, None)

        for suffix_path in [
            self.settings.CUSTOM_ANOMALY_MODELS_DIR / f"{model_id}.joblib",
            self.settings.CUSTOM_ANOMALY_RESULTS_DIR / f"{model_id}_metrics.json",
            self.settings.CUSTOM_ANOMALY_RESULTS_DIR / f"{model_id}_confusion_matrix.json",
        ]:
            if suffix_path.exists():
                suffix_path.unlink(missing_ok=True)

        return {"status": "deleted", "model_id": model_id}

    def validate_and_prepare_features(self, features: Dict[str, Any]) -> pd.DataFrame:
        """Validate input features against the 38 canonical features and prevent data leakage.

        Strict Rules:
        - Must contain exactly the 38 CANONICAL_MODEL_FEATURES.
        - Must NOT contain missing features.
        - Must NOT contain extra or unexpected features.
        - Must NOT contain excluded target or metadata columns (label_raw, label_category, is_attack,
          protocol_name, device_id, device_category).
        - Must NOT contain non-numeric types (including booleans).
        - Must NOT contain NaN or Infinite values.
        - Preserves exact canonical feature order.
        """
        keys_set = set(features.keys())
        expected_set = set(CANONICAL_MODEL_FEATURES)

        # 1. Missing features check
        missing = [f for f in CANONICAL_MODEL_FEATURES if f not in keys_set]

        # 2. Extra features check
        unexpected = [f for f in features if f not in expected_set]

        if missing or unexpected:
            raise InvalidFeatureSchemaError(
                missing_features=missing,
                unexpected_features=unexpected,
            )

        # 3. Explicit leakage guard
        leakage_detected = [f for f in EXCLUDED_FEATURES if f in keys_set]
        if leakage_detected:
            raise InvalidFeatureSchemaError(
                unexpected_features=leakage_detected,
                details=[{
                    "error": "Forbidden target or metadata leakage feature detected",
                    "features": leakage_detected,
                }],
            )

        # 4. Strict numerical type and finiteness check in exact canonical sequence
        row: Dict[str, float] = {}
        for feat in CANONICAL_MODEL_FEATURES:
            val = features[feat]
            # In Python, bool is a subclass of int (isinstance(True, int) == True)
            if isinstance(val, bool):
                raise BadRequestError(
                    f"Feature '{feat}' cannot be boolean; a float or integer is required."
                )
            if not isinstance(val, (int, float)):
                raise BadRequestError(
                    f"Feature '{feat}' must be numeric (int or float), got {type(val).__name__}: '{val}'"
                )
            if np.isnan(val) or np.isinf(val):
                raise BadRequestError(
                    f"Feature '{feat}' contains invalid numeric value '{val}'. NaN and Infinity are forbidden."
                )
            row[feat] = float(val)

        # Construct DataFrame to maintain column names and eliminate scikit-learn feature name warnings
        return pd.DataFrame([row], columns=CANONICAL_MODEL_FEATURES)

    def validate_and_prepare_batch_features(
        self, records: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """Validate a batch of feature dictionaries against the 38 canonical features."""
        if not records:
            raise BadRequestError("Batch records list cannot be empty.")
        if len(records) > 1000:
            raise BadRequestError(
                f"Batch size {len(records)} exceeds maximum allowable limit of 1,000 records."
            )

        expected_set = set(CANONICAL_MODEL_FEATURES)
        rows: List[Dict[str, float]] = []

        for idx, record in enumerate(records):
            keys_set = set(record.keys())
            missing = [f for f in CANONICAL_MODEL_FEATURES if f not in keys_set]
            unexpected = [f for f in record if f not in expected_set]

            if missing or unexpected:
                raise InvalidFeatureSchemaError(
                    missing_features=missing,
                    unexpected_features=unexpected,
                    details=[{"record_index": idx}],
                )

            leakage_detected = [f for f in EXCLUDED_FEATURES if f in keys_set]
            if leakage_detected:
                raise InvalidFeatureSchemaError(
                    unexpected_features=leakage_detected,
                    details=[{
                        "record_index": idx,
                        "error": "Forbidden target or metadata leakage feature detected",
                        "features": leakage_detected,
                    }],
                )

            row: Dict[str, float] = {}
            for feat in CANONICAL_MODEL_FEATURES:
                val = record[feat]
                if isinstance(val, bool):
                    raise BadRequestError(
                        f"Record {idx}: Feature '{feat}' cannot be boolean."
                    )
                if not isinstance(val, (int, float)):
                    raise BadRequestError(
                        f"Record {idx}: Feature '{feat}' must be numeric, got {type(val).__name__}."
                    )
                if np.isnan(val) or np.isinf(val):
                    raise BadRequestError(
                        f"Record {idx}: Feature '{feat}' contains NaN or Infinity."
                    )
                row[feat] = float(val)

            rows.append(row)

        return pd.DataFrame(rows, columns=CANONICAL_MODEL_FEATURES)

    def predict_single(self, request: PredictSingleRequest) -> PredictSingleResponse:
        """Execute single-flow anomaly detection inference."""
        model = self.get_or_load_model(request.model_id)
        df_x = self.validate_and_prepare_features(request.features)

        start_time = time.perf_counter()
        raw_pred = model.predict(df_x)[0]
        raw_proba = model.predict_proba(df_x)[0]
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        predicted_category = str(raw_pred)
        is_attack = 0 if predicted_category == "Benign" else 1

        # Format probability distribution across the 8 macro classes
        classes = list(getattr(model, "classes_", EXPECTED_LABEL_CATEGORIES))
        probabilities: Dict[str, float] = {
            str(cls_name): round(float(prob), 6)
            for cls_name, prob in zip(classes, raw_proba)
        }
        confidence = round(float(np.max(raw_proba)), 6)

        return PredictSingleResponse(
            model_id=request.model_id,
            predicted_category=predicted_category,
            is_attack=is_attack,
            confidence=confidence,
            probabilities=probabilities,
            latency_ms=round(latency_ms, 2),
        )

    def predict_batch(self, request: PredictBatchRequest) -> PredictBatchResponse:
        """Execute batch anomaly detection inference across multiple flow records."""
        model = self.get_or_load_model(request.model_id)
        df_x = self.validate_and_prepare_batch_features(request.records)

        start_time = time.perf_counter()
        raw_preds = model.predict(df_x)
        raw_probas = model.predict_proba(df_x)
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        classes = list(getattr(model, "classes_", EXPECTED_LABEL_CATEGORIES))
        predictions: List[PredictionItem] = []
        attack_count = 0
        benign_count = 0

        for idx, (pred, proba) in enumerate(zip(raw_preds, raw_probas)):
            category = str(pred)
            is_attack = 0 if category == "Benign" else 1
            if is_attack:
                attack_count += 1
            else:
                benign_count += 1

            prob_dict = {
                str(cls_name): round(float(p), 6)
                for cls_name, p in zip(classes, proba)
            }
            conf = round(float(np.max(proba)), 6)

            predictions.append(
                PredictionItem(
                    index=idx,
                    predicted_category=category,
                    is_attack=is_attack,
                    confidence=conf,
                    probabilities=prob_dict,
                )
            )

        return PredictBatchResponse(
            model_id=request.model_id,
            total_records=len(predictions),
            attack_count=attack_count,
            benign_count=benign_count,
            predictions=predictions,
            latency_ms=round(latency_ms, 2),
        )

    def list_experiments(self) -> ExperimentListResponse:
        """Return experimental paradigms, available classifiers, and synthetic quality warnings."""
        return ExperimentListResponse(
            experiments=[e.value for e in ExperimentType],
            available_classifiers=[
                "extra_trees",
                "hist_gradient_boosting",
                "logistic_regression",
                "random_forest",
            ],
            augmentation_levels=["0%", "25%", "50%", "100%"],
            total_models=len(self.APPROVED_MODELS),
            quality_warnings=list(SYNTHETIC_DATA_QUALITY_WARNINGS),
        )

    def compare_experiments(
        self,
        experiment_type: Optional[str] = None,
        classifier: Optional[str] = None,
        augmentation_level: Optional[str] = None,
    ) -> ExperimentComparisonResponse:
        """Retrieve audited comparison metrics across TRTR, TSTR, and TSTR+R (25%, 50%, 100%)."""
        comp_file = (
            self.settings.PROJECT_ROOT
            / "anomaly_detection"
            / "results"
            / "tstr_plus_r"
            / "tstr_plus_r_comprehensive_comparison.json"
        )
        if not comp_file.exists():
            raise ResourceNotFoundError("Comparison Artifact", "tstr_plus_r_comprehensive_comparison.json")

        with open(comp_file, "r", encoding="utf-8") as f:
            all_records: List[Dict[str, Any]] = json.load(f)

        # Apply optional filters
        filtered = all_records
        if experiment_type:
            exp_clean = experiment_type.strip().upper()
            filtered = [
                r for r in filtered if exp_clean in str(r.get("Experiment", "")).upper()
            ]
        if classifier:
            clf_clean = classifier.strip().lower()
            filtered = [
                r for r in filtered if clf_clean == str(r.get("Model", "")).lower()
            ]
        if augmentation_level:
            aug_clean = augmentation_level.strip()
            if not aug_clean.endswith("%"):
                aug_clean = f"{aug_clean}%"
            filtered = [
                r for r in filtered if str(r.get("Augmentation Level", "")).strip() == aug_clean
            ]

        # Read TRTR vs TSTR comparative baseline if available
        trtr_tstr_file = (
            self.settings.PROJECT_ROOT
            / "anomaly_detection"
            / "results"
            / "tstr"
            / "trtr_vs_tstr_comparison.json"
        )
        trtr_vs_tstr_data = None
        if trtr_tstr_file.exists():
            try:
                with open(trtr_tstr_file, "r", encoding="utf-8") as f:
                    trtr_vs_tstr_data = json.load(f)
            except Exception:
                trtr_vs_tstr_data = None

        return ExperimentComparisonResponse(
            total_comparisons=len(filtered),
            comparisons=filtered,
            trtr_vs_tstr_summary=trtr_vs_tstr_data,
            quality_warnings=list(SYNTHETIC_DATA_QUALITY_WARNINGS),
        )

    def _read_metrics_file(self, relative_path: Path) -> Dict[str, Any]:
        """Safely read persisted JSON metrics file."""
        full_path = self.settings.PROJECT_ROOT / relative_path
        if full_path.exists() and full_path.is_file():
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
