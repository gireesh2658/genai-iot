"""
IoTSynth AI - Baseline Model Factory (Phase 7.2)

Constructs standardized Scikit-learn Pipeline instances for TRTR baseline
anomaly detection models with strict 38-feature inputs and leakage isolation.
"""

from typing import Dict, Any, List, Optional
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import (
    RandomForestClassifier,
    ExtraTreesClassifier,
    HistGradientBoostingClassifier,
)

from anomaly_detection.feature_config import (
    CANONICAL_MODEL_FEATURES,
    EXPECTED_LABEL_CATEGORIES,
)

SUPPORTED_BASELINE_MODELS: List[str] = [
    "logistic_regression",
    "random_forest",
    "extra_trees",
    "hist_gradient_boosting",
]

DEFAULT_HYPERPARAMETERS: Dict[str, Dict[str, Any]] = {
    "logistic_regression": {
        "class_weight": "balanced",
        "max_iter": 1000,
        "solver": "lbfgs",
        "random_state": 42,
    },
    "random_forest": {
        "class_weight": "balanced",
        "n_estimators": 100,
        "max_depth": 20,
        "min_samples_split": 5,
        "random_state": 42,
        "n_jobs": -1,
    },
    "extra_trees": {
        "class_weight": "balanced",
        "n_estimators": 100,
        "max_depth": 20,
        "min_samples_split": 5,
        "random_state": 42,
        "n_jobs": -1,
    },
    "hist_gradient_boosting": {
        "class_weight": "balanced",
        "max_iter": 100,
        "max_depth": 15,
        "random_state": 42,
        "early_stopping": True,
    },
}


def create_baseline_pipeline(
    model_name: str,
    random_state: int = 42,
    custom_params: Optional[Dict[str, Any]] = None,
) -> Pipeline:
    """Create a standardized Scikit-learn Pipeline for a baseline model.

    Enforces disciplined preprocessing:
    - Logistic Regression: fitted with StandardScaler on training data only.
    - Tree-based Models (RF, ExtraTrees, HistGradientBoosting): passed directly without
      unnecessary scaling, preserving natural feature scales and split geometries.

    Args:
        model_name: One of 'logistic_regression', 'random_forest', 'extra_trees', 'hist_gradient_boosting'.
        random_state: Random seed for model reproducibility.
        custom_params: Optional dictionary overriding default hyperparameters.

    Returns:
        Configured sklearn.pipeline.Pipeline instance.

    Raises:
        ValueError: If model_name is not supported.
    """
    if model_name not in SUPPORTED_BASELINE_MODELS:
        raise ValueError(
            f"Unsupported model '{model_name}'. Supported models: {SUPPORTED_BASELINE_MODELS}"
        )

    params = dict(DEFAULT_HYPERPARAMETERS[model_name])
    params["random_state"] = random_state
    if custom_params:
        params.update(custom_params)

    if model_name == "logistic_regression":
        classifier = LogisticRegression(**params)
        pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", classifier),
        ])
    elif model_name == "random_forest":
        classifier = RandomForestClassifier(**params)
        pipeline = Pipeline([
            ("classifier", classifier),
        ])
    elif model_name == "extra_trees":
        classifier = ExtraTreesClassifier(**params)
        pipeline = Pipeline([
            ("classifier", classifier),
        ])
    elif model_name == "hist_gradient_boosting":
        classifier = HistGradientBoostingClassifier(**params)
        pipeline = Pipeline([
            ("classifier", classifier),
        ])
    else:
        raise ValueError(f"Unhandled model name '{model_name}'")

    return pipeline


def get_model_metadata(
    model_name: str,
    pipeline: Pipeline,
    random_state: int = 42,
) -> Dict[str, Any]:
    """Extract metadata and hyperparameters from a model pipeline."""
    classifier_step = pipeline.named_steps["classifier"]
    has_scaler = "scaler" in pipeline.named_steps

    return {
        "model_name": model_name,
        "classifier_class": classifier_step.__class__.__name__,
        "pipeline_steps": list(pipeline.named_steps.keys()),
        "has_feature_scaling": has_scaler,
        "scaler_class": pipeline.named_steps["scaler"].__class__.__name__ if has_scaler else None,
        "hyperparameters": classifier_step.get_params(),
        "input_features": list(CANONICAL_MODEL_FEATURES),
        "total_features": len(CANONICAL_MODEL_FEATURES),
        "target_categories": list(EXPECTED_LABEL_CATEGORIES),
        "random_state": random_state,
    }
