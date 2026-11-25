"""
IoTSynth AI - Anomaly Detection Package
Provides data loading, feature segregation, experiment configs, model factory, and evaluator.
"""

from anomaly_detection.feature_config import (
    CANONICAL_MODEL_FEATURES,
    TOTAL_MODEL_FEATURES_COUNT,
    EXCLUDED_FEATURES,
    PRIMARY_TARGET,
    SECONDARY_TARGET,
    SUPPORTED_TARGETS,
    EXPECTED_LABEL_CATEGORIES,
    MODEL_CONTINUOUS_FEATURES,
    MODEL_DISCRETE_FEATURES,
    MODEL_INDICATOR_FEATURES,
    validate_feature_columns,
)
from anomaly_detection.experiment_config import (
    ExperimentType,
    ExperimentConfig,
    SYNTHETIC_DATA_QUALITY_WARNINGS,
)
from anomaly_detection.data_loader import (
    DatasetSplit,
    ExperimentDatasetContainer,
    AnomalyDetectionDataLoader,
    compute_file_sha256,
    compute_df_sha256,
)
from anomaly_detection.model_factory import (
    SUPPORTED_BASELINE_MODELS,
    DEFAULT_HYPERPARAMETERS,
    create_baseline_pipeline,
    get_model_metadata,
)
from anomaly_detection.evaluator import AnomalyDetectionEvaluator

__all__ = [
    "CANONICAL_MODEL_FEATURES",
    "TOTAL_MODEL_FEATURES_COUNT",
    "EXCLUDED_FEATURES",
    "PRIMARY_TARGET",
    "SECONDARY_TARGET",
    "SUPPORTED_TARGETS",
    "EXPECTED_LABEL_CATEGORIES",
    "MODEL_CONTINUOUS_FEATURES",
    "MODEL_DISCRETE_FEATURES",
    "MODEL_INDICATOR_FEATURES",
    "validate_feature_columns",
    "ExperimentType",
    "ExperimentConfig",
    "SYNTHETIC_DATA_QUALITY_WARNINGS",
    "DatasetSplit",
    "ExperimentDatasetContainer",
    "AnomalyDetectionDataLoader",
    "compute_file_sha256",
    "compute_df_sha256",
    "SUPPORTED_BASELINE_MODELS",
    "DEFAULT_HYPERPARAMETERS",
    "create_baseline_pipeline",
    "get_model_metadata",
    "AnomalyDetectionEvaluator",
]
