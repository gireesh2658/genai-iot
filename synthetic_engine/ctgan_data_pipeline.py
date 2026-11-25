"""
IoTSynth AI - CTGAN Data Pipeline Module (Phase 5.1)

Provides the training-data preparation pipeline for CTGAN-based synthetic
IoT network traffic generation. Handles:
  - Loading and validating data against the 44-column canonical schema.
  - Identifying feature types (continuous, discrete, binary, categorical, metadata, targets).
  - Specifying discrete columns for the SDV CTGANSynthesizer API.
  - Producing reproducible train/validation splits with optional stratification.
  - Subsample-size capping for CPU-bound training (Phase 5.2).
  - Anomaly-detection target leakage prevention.

This module does NOT train any model. Model fitting is strictly Phase 5.2.
"""

from dataclasses import dataclass, field
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from simulator.traffic_schema import (
    BINARY_INDICATOR_FEATURES,
    CANONICAL_SCHEMA_COLUMNS,
    CATEGORICAL_STRING_FEATURES,
    COLUMN_DATA_TYPES,
    CONTINUOUS_NUMERICAL_FEATURES,
    DISCRETE_COUNT_FEATURES,
    MODEL_INPUT_FEATURES,
    TOTAL_ATTRIBUTES_COUNT,
    validate_schema_columns,
)


# ==============================================================================
# Configuration
# ==============================================================================

# Columns that carry ground-truth labelling or device-simulation metadata.
# They must NEVER be used as input features for anomaly-detection models,
# but they ARE valid conditioning columns for CTGAN's conditional generator.
METADATA_COLUMNS: List[str] = [
    "device_id",
    "device_category",
]

LABEL_AND_TARGET_COLUMNS: List[str] = [
    "label_raw",
    "label_category",
    "is_attack",
]

# Columns derived from Protocol Type that are not independent features
# but useful for conditional generation.
DERIVED_PROTOCOL_COLUMNS: List[str] = [
    "protocol_name",
]

# Columns CTGAN must treat as discrete (SDV `discrete_columns` parameter).
# This includes every integer-valued count, every binary indicator, and every
# categorical string except for metadata columns that are excluded from
# training by default.
CTGAN_DISCRETE_COLUMNS: List[str] = sorted(
    set(
        DISCRETE_COUNT_FEATURES       # Protocol Type, Number, syn_count, ...
        + BINARY_INDICATOR_FEATURES   # HTTP, HTTPS, ..., is_attack
        + CATEGORICAL_STRING_FEATURES # device_id, device_category, protocol_name, label_raw, label_category
    )
)

# CTGAN v2 refined feature schema (preserves v1 CTGAN_DISCRETE_COLUMNS untouched):
# Reclassifies 15 protocol proportions and 5 numeric counts as numerical, restricting
# discrete/categorical conditioning strictly to authentic categorical & device columns.
CTGAN_V2_PROTOCOL_PROPORTION_COLUMNS: List[str] = [
    c for c in BINARY_INDICATOR_FEATURES if c != "is_attack"
]
CTGAN_V2_NUMERIC_COUNT_COLUMNS: List[str] = [
    "Number",
    "ack_count",
    "syn_count",
    "fin_count",
    "rst_count",
]
CTGAN_V2_DISCRETE_COLUMNS: List[str] = [
    "device_id",
    "device_category",
    "protocol_name",
    "Protocol Type",
    "label_raw",
    "label_category",
    "is_attack",
]



@dataclass
class CTGANDataPipelineConfig:
    """Configuration for training-data preparation.

    Attributes:
        train_ratio: Fraction of data for training (remainder goes to validation).
        val_ratio: Fraction of data for validation (must equal 1 - train_ratio).
        sample_size: Optional cap on the number of rows loaded. None = use all rows.
        stratify_by: Column to stratify the train/val split on. None = no stratification.
        random_seed: Seed for reproducible splits and subsampling.
        exclude_metadata_cols: If True, drop ``device_id`` and ``device_category``
            from the CTGAN training DataFrame. Labels (``label_raw``, ``label_category``,
            ``is_attack``) are retained for conditional generation.
    """

    train_ratio: float = 0.80
    val_ratio: float = 0.20
    sample_size: Optional[int] = None
    stratify_by: Optional[str] = "label_category"
    random_seed: int = 42
    exclude_metadata_cols: bool = True

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate pipeline configuration parameters.

        Raises:
            ValueError: On any invalid parameter.
        """
        if not isinstance(self.train_ratio, (int, float)):
            raise ValueError(
                f"train_ratio must be a float, got {type(self.train_ratio).__name__}"
            )
        if not isinstance(self.val_ratio, (int, float)):
            raise ValueError(
                f"val_ratio must be a float, got {type(self.val_ratio).__name__}"
            )

        if not (0.0 < self.train_ratio < 1.0):
            raise ValueError(
                f"train_ratio must be in (0, 1), got {self.train_ratio}"
            )
        if not (0.0 < self.val_ratio < 1.0):
            raise ValueError(
                f"val_ratio must be in (0, 1), got {self.val_ratio}"
            )

        ratio_sum = self.train_ratio + self.val_ratio
        if abs(ratio_sum - 1.0) > 1e-6:
            raise ValueError(
                f"train_ratio + val_ratio must equal 1.0, got {ratio_sum:.8f}"
            )

        if self.sample_size is not None:
            if not isinstance(self.sample_size, int) or self.sample_size < 1:
                raise ValueError(
                    f"sample_size must be a positive integer or None, got {self.sample_size}"
                )

        if not isinstance(self.random_seed, int):
            raise ValueError(
                f"random_seed must be an integer, got {type(self.random_seed).__name__}"
            )

        if self.stratify_by is not None and not isinstance(self.stratify_by, str):
            raise ValueError(
                f"stratify_by must be a string column name or None, got {type(self.stratify_by).__name__}"
            )


# ==============================================================================
# Data Pipeline
# ==============================================================================

class CTGANDataPipeline:
    """Training-data preparation pipeline for CTGAN / TVAE synthesis.

    Responsibilities (Phase 5.1 scope only):
      1. Load CSV or Parquet data.
      2. Validate against the canonical 44-column schema.
      3. Classify columns into feature-type groups for CTGAN configuration.
      4. Prepare reproducible train / validation splits.
      5. Guard against anomaly-detection target leakage.

    This class does NOT fit or sample from any generative model.
    """

    def __init__(
        self,
        config: Optional[CTGANDataPipelineConfig] = None,
    ) -> None:
        self.config = config or CTGANDataPipelineConfig()

    # ------------------------------------------------------------------
    # 1. Data Loading
    # ------------------------------------------------------------------

    @staticmethod
    def load_data(path: Union[str, Path]) -> pd.DataFrame:
        """Load a dataset from CSV or Parquet.

        Args:
            path: File path with ``.csv`` or ``.parquet`` extension.

        Returns:
            Raw DataFrame as loaded from disk.

        Raises:
            FileNotFoundError: If the path does not exist.
            ValueError: If the file extension is unsupported.
        """
        filepath = Path(path)
        if not filepath.exists():
            raise FileNotFoundError(f"Dataset file not found: {filepath}")

        ext = filepath.suffix.lower()
        if ext == ".csv":
            return pd.read_csv(filepath)
        elif ext == ".parquet":
            return pd.read_parquet(filepath)
        else:
            raise ValueError(
                f"Unsupported file format '{ext}'. Only .csv and .parquet are supported."
            )

    # ------------------------------------------------------------------
    # 2. Schema Validation
    # ------------------------------------------------------------------

    @staticmethod
    def validate_schema(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """Validate that a DataFrame conforms to the 44-column canonical schema.

        Checks:
          - Exact column presence (no missing, no extra).
          - Canonical column ordering.
          - No null / NaN values.
          - No infinite values in numeric columns.

        Args:
            df: DataFrame to validate.

        Returns:
            Tuple of (is_valid, list_of_error_messages).
        """
        errors: List[str] = []

        # Column presence and ordering
        col_valid, col_errors = validate_schema_columns(
            list(df.columns), check_ordering=True
        )
        errors.extend(col_errors)

        # Null / NaN check
        null_counts = df.isnull().sum()
        cols_with_nulls = null_counts[null_counts > 0]
        if len(cols_with_nulls) > 0:
            errors.append(
                f"Null/NaN values found in {len(cols_with_nulls)} column(s): "
                f"{dict(cols_with_nulls)}"
            )

        # Infinite check on numeric columns
        numeric_cols = [
            c for c in df.columns
            if c in CONTINUOUS_NUMERICAL_FEATURES or c in DISCRETE_COUNT_FEATURES
        ]
        for col in numeric_cols:
            if col in df.columns:
                vals = pd.to_numeric(df[col], errors="coerce")
                inf_count = int(np.isinf(vals.dropna()).sum())
                if inf_count > 0:
                    errors.append(
                        f"Column '{col}' contains {inf_count} infinite value(s)."
                    )

        return (len(errors) == 0, errors)

    # ------------------------------------------------------------------
    # 3. Feature-Type Identification
    # ------------------------------------------------------------------

    @staticmethod
    def identify_feature_types(
        df: pd.DataFrame,
    ) -> Dict[str, List[str]]:
        """Classify DataFrame columns into ML feature-type groups.

        Returns:
            Dictionary with keys:
              - ``continuous``: Columns with continuous float distributions.
              - ``discrete``: Integer-valued count / ID columns.
              - ``binary_indicators``: 0/1 protocol mask columns (incl. ``is_attack``).
              - ``categorical_string``: String-typed categorical columns.
              - ``metadata``: Simulation metadata not suitable as ML features
                (``device_id``, ``device_category``).
              - ``targets``: Ground-truth labels (``label_raw``, ``label_category``,
                ``is_attack``). These may condition CTGAN but must NOT be used
                as anomaly-detection model inputs.
              - ``ctgan_discrete_columns``: Union of discrete, binary, and
                categorical columns that SDV's CTGANSynthesizer requires as
                the ``discrete_columns`` list.
              - ``model_input_features``: The 38 columns suitable for downstream
                ML models (excludes metadata + labels + derived protocol name).
        """
        present = set(df.columns)

        continuous = [c for c in CONTINUOUS_NUMERICAL_FEATURES if c in present]
        discrete = [c for c in DISCRETE_COUNT_FEATURES if c in present]
        binary = [c for c in BINARY_INDICATOR_FEATURES if c in present]
        categorical = [c for c in CATEGORICAL_STRING_FEATURES if c in present]
        metadata = [c for c in METADATA_COLUMNS if c in present]
        targets = [c for c in LABEL_AND_TARGET_COLUMNS if c in present]

        # Columns CTGAN should treat as discrete (non-continuous).
        # Includes counts, binary indicators, and categorical strings present
        # in the actual DataFrame.
        ctgan_discrete = sorted(set(discrete + binary + categorical) & present)

        # Downstream ML model input features (excludes labels and metadata).
        model_inputs = [c for c in MODEL_INPUT_FEATURES if c in present]

        return {
            "continuous": continuous,
            "discrete": discrete,
            "binary_indicators": binary,
            "categorical_string": categorical,
            "metadata": metadata,
            "targets": targets,
            "ctgan_discrete_columns": ctgan_discrete,
            "model_input_features": model_inputs,
        }

    # ------------------------------------------------------------------
    # 4. Training Data Preparation
    # ------------------------------------------------------------------

    def prepare_training_data(
        self,
        df: pd.DataFrame,
        config: Optional[CTGANDataPipelineConfig] = None,
    ) -> Dict[str, Any]:
        """Prepare train / validation splits for CTGAN training.

        Steps:
          1. Optionally subsample to ``config.sample_size``.
          2. Optionally drop metadata columns (``device_id``, ``device_category``).
          3. Stratified (or random) train/val split.
          4. Identify feature types and CTGAN discrete columns.
          5. Compile preparation summary.

        Args:
            df: Canonical 44-column DataFrame (must pass ``validate_schema``).
            config: Override pipeline config for this call. If None, uses ``self.config``.

        Returns:
            Dictionary with keys:
              - ``train_df``: Training DataFrame.
              - ``val_df``: Validation DataFrame.
              - ``feature_types``: Output of ``identify_feature_types``.
              - ``discrete_columns``: List of discrete column names for CTGANSynthesizer.
              - ``excluded_columns``: Columns dropped from training data.
              - ``sample_size_applied``: Actual number of rows used (after subsampling).
              - ``random_seed``: Seed used.
              - ``target_leakage_guard``: Dict documenting leakage-prevention metadata.

        Raises:
            ValueError: If the DataFrame fails schema validation.
        """
        cfg = config or self.config
        rng = np.random.default_rng(cfg.random_seed)

        # --- Schema validation ---
        is_valid, schema_errors = self.validate_schema(df)
        if not is_valid:
            raise ValueError(
                f"DataFrame fails canonical schema validation: {schema_errors}"
            )

        working_df = df.copy()

        # --- Subsampling (Stratified to protect rare classes) ---
        discarded_classes: List[str] = []
        if cfg.sample_size is not None and cfg.sample_size < len(working_df):
            if cfg.stratify_by and cfg.stratify_by in working_df.columns:
                working_df, discarded_classes = self._stratified_subsample(
                    working_df, cfg.stratify_by, cfg.sample_size, rng
                )
            else:
                orig_classes = (
                    set(working_df[cfg.stratify_by].unique())
                    if (cfg.stratify_by and cfg.stratify_by in working_df.columns)
                    else set()
                )
                working_df = working_df.sample(
                    n=cfg.sample_size,
                    random_state=cfg.random_seed,
                ).reset_index(drop=True)
                if orig_classes:
                    discarded_classes = sorted(
                        list(orig_classes - set(working_df[cfg.stratify_by].unique()))
                    )

        sample_size_applied = len(working_df)

        # --- Drop metadata columns ---
        excluded_columns: List[str] = []
        if cfg.exclude_metadata_cols:
            cols_to_drop = [c for c in METADATA_COLUMNS if c in working_df.columns]
            excluded_columns.extend(cols_to_drop)
            working_df = working_df.drop(columns=cols_to_drop)

        # --- Feature-type identification ---
        feature_types = self.identify_feature_types(working_df)

        # Discrete columns for CTGANSynthesizer (only those remaining after drops)
        discrete_columns = feature_types["ctgan_discrete_columns"]

        # --- Train / Validation Split ---
        n_total = len(working_df)
        n_train = max(1, int(round(n_total * cfg.train_ratio)))
        n_val = n_total - n_train

        if cfg.stratify_by and cfg.stratify_by in working_df.columns:
            train_df, val_df = self._stratified_split(
                working_df, cfg.stratify_by, cfg.train_ratio, rng
            )
        else:
            indices = rng.permutation(n_total)
            train_indices = indices[:n_train]
            val_indices = indices[n_train:]
            train_df = working_df.iloc[train_indices].reset_index(drop=True)
            val_df = working_df.iloc[val_indices].reset_index(drop=True)

        # --- Class Representation & Insufficient Records Tracking ---
        if cfg.stratify_by and cfg.stratify_by in working_df.columns:
            train_counts = (
                train_df[cfg.stratify_by].value_counts().to_dict()
                if not train_df.empty and cfg.stratify_by in train_df.columns
                else {}
            )
            val_counts = (
                val_df[cfg.stratify_by].value_counts().to_dict()
                if not val_df.empty and cfg.stratify_by in val_df.columns
                else {}
            )
            all_classes = sorted(list(working_df[cfg.stratify_by].unique()))
            unrepresented_in_val = [c for c in all_classes if val_counts.get(c, 0) == 0]
            unrepresented_in_train = [c for c in all_classes if train_counts.get(c, 0) == 0]
            single_split_classes = sorted(
                list(set(unrepresented_in_val) | set(unrepresented_in_train))
            )
            class_totals = working_df[cfg.stratify_by].value_counts().to_dict()
            classes_with_insufficient_records = [
                c for c in all_classes if class_totals.get(c, 0) < 2
            ]
        else:
            train_counts = {}
            val_counts = {}
            unrepresented_in_val = []
            unrepresented_in_train = []
            single_split_classes = []
            classes_with_insufficient_records = []

        class_representation = {
            "stratification_column": cfg.stratify_by,
            "train_class_counts": train_counts,
            "val_class_counts": val_counts,
            "unrepresented_in_val": unrepresented_in_val,
            "unrepresented_in_train": unrepresented_in_train,
            "single_split_classes": single_split_classes,
            "classes_with_insufficient_records": classes_with_insufficient_records,
            "subsampling_discarded_classes": discarded_classes,
        }

        # --- Target leakage guard documentation ---
        target_leakage_guard = {
            "conditioning_columns": [
                c for c in LABEL_AND_TARGET_COLUMNS if c in working_df.columns
            ],
            "forbidden_as_anomaly_detection_input": LABEL_AND_TARGET_COLUMNS.copy(),
            "explanation": (
                "Columns 'is_attack', 'label_raw', and 'label_category' are "
                "generation-conditioning labels / ground-truth targets. They "
                "condition the CTGAN's conditional generator but must NEVER be "
                "used as feature inputs for downstream anomaly-detection models "
                "(Phase 7). Using them would cause perfect but trivial "
                "classification via label leakage."
            ),
        }

        return {
            "train_df": train_df,
            "val_df": val_df,
            "feature_types": feature_types,
            "discrete_columns": discrete_columns,
            "excluded_columns": excluded_columns,
            "sample_size_applied": sample_size_applied,
            "random_seed": cfg.random_seed,
            "target_leakage_guard": target_leakage_guard,
            "class_representation": class_representation,
            "unrepresented_in_val": unrepresented_in_val,
            "single_split_classes": single_split_classes,
            "subsampling_discarded_classes": discarded_classes,
        }

    # ------------------------------------------------------------------
    # 5. Stratified Subsampling & Split Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _stratified_subsample(
        df: pd.DataFrame,
        stratify_col: str,
        sample_size: int,
        rng: np.random.Generator,
    ) -> Tuple[pd.DataFrame, List[str]]:
        """Perform deterministic stratified subsampling preserving rare classes.

        Allocation Policy:
          - If sample_size >= number of classes (K):
            Every class receives at least 1 record (base quota = 1) so no class
            is silently discarded. Remaining slots are distributed proportionally
            using the largest remainder method.
          - If sample_size < K:
            It is mathematically impossible to give every class >= 1 sample.
            The sample_size largest classes each receive 1 record; classes with 0
            allocation are returned in ``discarded_classes``.
          - Records are sampled without replacement.

        Args:
            df: DataFrame to subsample.
            stratify_col: Column name to stratify on.
            sample_size: Desired number of samples.
            rng: NumPy Generator for reproducibility.

        Returns:
            Tuple of (subsampled_df, list_of_discarded_classes).
        """
        n_total = len(df)
        if sample_size >= n_total:
            return df.copy(), []

        groups = {name: group for name, group in df.groupby(stratify_col, sort=True)}
        sorted_classes = sorted(groups.keys(), key=lambda c: (-len(groups[c]), str(c)))
        k = len(sorted_classes)

        discarded_classes: List[str] = []

        if sample_size < k:
            # Mathematical impossibility: cannot represent all classes
            selected_classes = sorted_classes[:sample_size]
            discarded_classes = sorted_classes[sample_size:]
            parts = [groups[c].iloc[rng.permutation(len(groups[c]))[:1]] for c in selected_classes]
            subsampled = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=df.columns)
            return subsampled, discarded_classes

        # sample_size >= k: every class gets at least 1 record
        # Base quota = 1 for all classes
        quotas: Dict[str, int] = {c: 1 for c in sorted_classes}
        rem_slots = sample_size - k
        class_counts = {c: len(groups[c]) for c in sorted_classes}
        denom = max(1, n_total - k)

        # Largest remainder method for extra slots
        remainders: List[Tuple[float, str]] = []
        allocated_extra = 0
        for c in sorted_classes:
            w = (class_counts[c] - 1) / denom
            exact_share = w * rem_slots
            base_extra = int(math.floor(exact_share))
            # Cap extra so quota cannot exceed available records for that class
            max_extra_allowed = class_counts[c] - 1
            extra = min(base_extra, max_extra_allowed)
            quotas[c] += extra
            allocated_extra += extra
            remainders.append((exact_share - extra, c))

        # Distribute remaining deficit to largest remainders
        deficit = rem_slots - allocated_extra
        remainders.sort(key=lambda x: (x[0], -len(groups[x[1]])), reverse=True)
        for _, c in remainders:
            if deficit <= 0:
                break
            if quotas[c] < class_counts[c]:
                quotas[c] += 1
                deficit -= 1

        parts = []
        for c in sorted(sorted_classes):
            q = quotas[c]
            group = groups[c]
            perm = rng.permutation(len(group))[:q]
            parts.append(group.iloc[perm])

        subsampled = pd.concat(parts, ignore_index=True)
        return subsampled, []

    @staticmethod
    def _stratified_split(
        df: pd.DataFrame,
        stratify_col: str,
        train_ratio: float,
        rng: np.random.Generator,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Perform a deterministic stratified train/validation split.

        Each stratum (unique value of ``stratify_col``) is split independently.
        Representable classes (n >= 2) preserve representation in BOTH splits
        by allocating at least 1 record to train and at least 1 to validation:
            n_train = max(1, min(n - 1, int(round(n * train_ratio))))
            n_val = n - n_train

        Classes with n = 1 record cannot be split into two non-empty sets
        without duplication (which is forbidden); they are assigned entirely
        to the training set and reported as single-split classes.

        Args:
            df: DataFrame to split.
            stratify_col: Column name for stratification.
            train_ratio: Fraction allocated to training.
            rng: NumPy Generator for reproducibility.

        Returns:
            Tuple of (train_df, val_df).
        """
        train_parts: List[pd.DataFrame] = []
        val_parts: List[pd.DataFrame] = []

        for _, group in df.groupby(stratify_col, sort=True):
            n = len(group)
            if n <= 1:
                # Mathematically impossible to split into both without duplication
                train_parts.append(group)
                continue

            # For n >= 2, guarantee at least 1 sample in train and 1 in val
            n_train = max(1, min(n - 1, int(round(n * train_ratio))))
            perm = rng.permutation(n)
            train_parts.append(group.iloc[perm[:n_train]])
            val_parts.append(group.iloc[perm[n_train:]])

        train_df = (
            pd.concat(train_parts, ignore_index=True)
            if train_parts
            else pd.DataFrame(columns=df.columns)
        )
        val_df = (
            pd.concat(val_parts, ignore_index=True)
            if val_parts
            else pd.DataFrame(columns=df.columns)
        )

        return train_df, val_df
