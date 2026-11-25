"""
IoTSynth AI - Anomaly Detection Experiment Configuration (Phase 7.1)

Defines experimental paradigms (TRTR, TSTR, TSTR+R), reproducible execution defaults,
target configurations, and dataset quality warnings.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import os

from anomaly_detection.feature_config import (
    CANONICAL_MODEL_FEATURES,
    PRIMARY_TARGET,
    SECONDARY_TARGET,
    SUPPORTED_TARGETS,
)


class ExperimentType(str, Enum):
    """Supported anomaly detection benchmarking experimental paradigms."""
    TRTR = "TRTR"            # Train on Real, Test on Real (real-data comparative baseline)
    TSTR = "TSTR"            # Train on Synthetic, Test on Real (generative transfer quality)
    TSTR_PLUS_R = "TSTR+R"    # Train on Real + Synthetic, Test on Real (minority augmentation)


# Explicit data quality limitations documented for synthetic datasets
SYNTHETIC_DATA_QUALITY_WARNINGS: List[str] = [
    "Min <= AVG <= Max packet length bounds remain unresolved by design in synthetic datasets "
    "(3,157 records violate ordering in ctgan_initial_sample_v1_domain_corrected; artificial sorting was rejected to prevent +57% KS degradation).",
    "AVG ≈ Tot sum / Number flow aggregation ratios remain unresolved by design "
    "(2,354 records violate exact quotient; overwriting values was rejected to prevent distribution distortion).",
    "Syntactic label consistency does not independently establish authentic physical traffic dynamics "
    "(continuous features reflect learned Gaussian mixture clusters rather than verified hardware packet dynamics).",
    "Protocol and application indicators (HTTP, TCP, UDP, IPv, LLC) represent flow-window packet proportion ratios in [0.0, 1.0], not pure binary flags.",
]


@dataclass
class ExperimentConfig:
    """Central configuration for anomaly detection experiments."""
    experiment_type: ExperimentType = ExperimentType.TRTR
    target_column: str = PRIMARY_TARGET
    features: List[str] = field(default_factory=lambda: list(CANONICAL_MODEL_FEATURES))
    random_seed: int = 42

    # Dataset paths
    real_dataset_path: str = "datasets/processed/ciciot2023_preprocessed_sample.parquet"
    synthetic_dataset_path: str = "datasets/generated/ctgan_initial_sample_v1_domain_corrected.parquet"
    synthetic_ablation_path: str = "datasets/generated/ctgan_initial_sample_v1.parquet"

    # Split parameters (must match approved Phase 5.1/5.4/6 deterministic 80/20 split)
    train_split_ratio: float = 0.80
    validation_split_ratio: float = 0.20
    split_stratify_column: str = "label_raw"

    # Expected split counts for verification
    expected_real_train_rows: int = 38466
    expected_real_val_rows: int = 9616
    expected_synthetic_train_rows: int = 5000

    # Output directories (aligned with active repository artifacts)
    reports_dir: str = "anomaly_detection/results"
    models_dir: str = "anomaly_detection/models"

    def __post_init__(self) -> None:
        """Validate configuration integrity upon initialization."""
        self.validate()

    def validate(self) -> None:
        """Check configuration values for consistency and raise ValueError on error."""
        if self.target_column not in SUPPORTED_TARGETS:
            raise ValueError(
                f"Unsupported target column '{self.target_column}'. Must be one of {SUPPORTED_TARGETS}."
            )

        if len(self.features) != 38:
            raise ValueError(
                f"Expected exactly 38 model input features, got {len(self.features)}."
            )

        if self.features != CANONICAL_MODEL_FEATURES:
            raise ValueError(
                "Features list must strictly match the canonical ordering of MODEL_INPUT_FEATURES."
            )

        if self.train_split_ratio + self.validation_split_ratio != 1.0:
            raise ValueError(
                f"Train ({self.train_split_ratio}) and validation ({self.validation_split_ratio}) ratios must sum to 1.0."
            )

    def get_quality_warnings(self, experiment_type: Optional[ExperimentType] = None) -> List[str]:
        """Return dataset quality warnings applicable to the configured experiment type."""
        target_type = experiment_type or self.experiment_type
        if target_type in (ExperimentType.TSTR, ExperimentType.TSTR_PLUS_R):
            return list(SYNTHETIC_DATA_QUALITY_WARNINGS)
        return []

    def to_dict(self) -> Dict[str, Any]:
        """Serialize configuration to a dictionary."""
        return {
            "experiment_type": self.experiment_type.value,
            "target_column": self.target_column,
            "total_features": len(self.features),
            "random_seed": self.random_seed,
            "real_dataset_path": self.real_dataset_path,
            "synthetic_dataset_path": self.synthetic_dataset_path,
            "synthetic_ablation_path": self.synthetic_ablation_path,
            "train_split_ratio": self.train_split_ratio,
            "validation_split_ratio": self.validation_split_ratio,
            "split_stratify_column": self.split_stratify_column,
            "expected_real_train_rows": self.expected_real_train_rows,
            "expected_real_val_rows": self.expected_real_val_rows,
            "expected_synthetic_train_rows": self.expected_synthetic_train_rows,
            "quality_warnings": self.get_quality_warnings(),
        }
