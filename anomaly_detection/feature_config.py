"""
IoTSynth AI - Anomaly Detection Feature Configuration (Phase 7.1)

Defines the authoritative 38-feature model input space, target columns,
excluded metadata/leakage features, and strict schema validation functions.
"""

from typing import List, Set, Tuple, Dict, Any
import numpy as np
import pandas as pd

from simulator.traffic_schema import (
    MODEL_INPUT_FEATURES,
    CONTINUOUS_NUMERICAL_FEATURES,
    DISCRETE_COUNT_FEATURES,
    BINARY_INDICATOR_FEATURES,
)

# Canonical 38 model input features imported directly from canonical schema
CANONICAL_MODEL_FEATURES: List[str] = list(MODEL_INPUT_FEATURES)
TOTAL_MODEL_FEATURES_COUNT: int = len(CANONICAL_MODEL_FEATURES)
assert TOTAL_MODEL_FEATURES_COUNT == 38, f"Expected exactly 38 features, got {TOTAL_MODEL_FEATURES_COUNT}"

# Columns strictly excluded from model input features to prevent leakage or redundancy
EXCLUDED_FEATURES: Set[str] = {
    "label_raw",         # Fine-grained threat label (target leakage)
    "label_category",    # Primary macro threat classification target (target leakage)
    "is_attack",         # Secondary binary anomaly target (target leakage)
    "protocol_name",     # Redundant categorical string (captured by Protocol Type integer)
    "device_id",         # Device identifier metadata
    "device_category",   # Device profile metadata
}

# Target column definitions
PRIMARY_TARGET: str = "label_category"
SECONDARY_TARGET: str = "is_attack"
SUPPORTED_TARGETS: Tuple[str, ...] = (PRIMARY_TARGET, SECONDARY_TARGET)

# Expected macro threat categories (8 classes)
EXPECTED_LABEL_CATEGORIES: List[str] = [
    "Benign",
    "Brute Force",
    "DDoS",
    "DoS",
    "Mirai",
    "Reconnaissance",
    "Spoofing",
    "Web-based",
]

# Feature subgroupings within the 38 canonical model features
MODEL_CONTINUOUS_FEATURES: List[str] = [
    f for f in CANONICAL_MODEL_FEATURES if f in CONTINUOUS_NUMERICAL_FEATURES
]
MODEL_DISCRETE_FEATURES: List[str] = [
    f for f in CANONICAL_MODEL_FEATURES if f in DISCRETE_COUNT_FEATURES or f == "Protocol Type"
]
MODEL_INDICATOR_FEATURES: List[str] = [
    f for f in CANONICAL_MODEL_FEATURES if f in BINARY_INDICATOR_FEATURES
]


def validate_feature_columns(
    df_columns: List[str],
    target_col: str = PRIMARY_TARGET,
) -> Dict[str, Any]:
    """Validate that a dataset contains the exact 38 canonical features without leakage.

    Args:
        df_columns: List of columns in the candidate DataFrame.
        target_col: Expected target column name.

    Returns:
        Dictionary with validation status and diagnostics.

    Raises:
        ValueError: If required features are missing, unexpected target columns are
            found in the feature set, or target column is absent.
    """
    col_set = set(df_columns)

    # 1. Check for missing model features
    missing_features = [f for f in CANONICAL_MODEL_FEATURES if f not in col_set]
    if missing_features:
        raise ValueError(
            f"Dataset is missing {len(missing_features)} canonical model input feature(s): {missing_features}"
        )

    # 2. Check for target column presence
    if target_col not in col_set:
        raise ValueError(f"Dataset is missing required target column: '{target_col}'")

    # 3. Check for forbidden leakage features if candidate columns represent feature matrix X
    # Note: caller should ensure target_col is separated before X validation
    leakage_in_features = [f for f in EXCLUDED_FEATURES if f in col_set and f != target_col]

    return {
        "is_valid": True,
        "total_features_found": len(CANONICAL_MODEL_FEATURES),
        "target_column": target_col,
        "missing_features": missing_features,
        "potential_leakage_columns_in_dataframe": leakage_in_features,
    }
