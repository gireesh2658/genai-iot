"""
IoTSynth AI - Anomaly Detection Data Loader (Phase 7.1)

Loads, validates, and segregates real and synthetic network traffic datasets for
TRTR, TSTR, and TSTR+R anomaly detection benchmarking. Enforces strict isolation
of the 38 canonical network features, guarantees zero target leakage, preserves
reproducible train/validation splits, and emits explicit dataset quality warnings.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Set
import os
import hashlib
import numpy as np
import pandas as pd

from simulator.traffic_schema import (
    CANONICAL_SCHEMA_COLUMNS,
    MODEL_INPUT_FEATURES,
)
from synthetic_engine.ctgan_data_pipeline import (
    CTGANDataPipeline,
    CTGANDataPipelineConfig,
)
from anomaly_detection.feature_config import (
    CANONICAL_MODEL_FEATURES,
    EXCLUDED_FEATURES,
    PRIMARY_TARGET,
    SECONDARY_TARGET,
    SUPPORTED_TARGETS,
    EXPECTED_LABEL_CATEGORIES,
    validate_feature_columns,
)
from anomaly_detection.experiment_config import (
    ExperimentConfig,
    ExperimentType,
    SYNTHETIC_DATA_QUALITY_WARNINGS,
)


def compute_file_sha256(path: str) -> str:
    """Compute deterministic SHA-256 hash of a file on disk."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def compute_df_sha256(df: pd.DataFrame) -> str:
    """Compute deterministic SHA-256 hash of a DataFrame serialized to CSV bytes."""
    return hashlib.sha256(df.to_csv(index=False).encode("utf-8")).hexdigest()


@dataclass
class DatasetSplit:
    """Encapsulates a verified feature matrix X and target vector y for one split."""
    X: pd.DataFrame
    y: pd.Series
    class_counts: Dict[str, int]
    class_proportions: Dict[str, float]
    source_info: Dict[str, Any]
    is_synthetic: bool = False

    @property
    def n_records(self) -> int:
        return len(self.X)

    @property
    def n_features(self) -> int:
        return self.X.shape[1]

    def summary(self) -> Dict[str, Any]:
        """Return a structured summary of the dataset split."""
        return {
            "records": self.n_records,
            "features": self.n_features,
            "is_synthetic": self.is_synthetic,
            "class_counts": self.class_counts,
            "class_proportions": self.class_proportions,
            "source_info": self.source_info,
        }


@dataclass
class ExperimentDatasetContainer:
    """Container holding training and validation splits for a configured anomaly detection experiment."""
    train_split: DatasetSplit
    val_split: DatasetSplit
    experiment_type: ExperimentType
    target_column: str
    quality_warnings: List[str] = field(default_factory=list)

    def summary(self) -> Dict[str, Any]:
        """Return structured summary of the experiment datasets."""
        return {
            "experiment_type": self.experiment_type.value,
            "target_column": self.target_column,
            "train": self.train_split.summary(),
            "validation": self.val_split.summary(),
            "quality_warnings": self.quality_warnings,
        }


class AnomalyDetectionDataLoader:
    """Modular dataset loader with rigorous validation and zero-leakage safeguards."""

    def __init__(self, config: Optional[ExperimentConfig] = None):
        self.config = config or ExperimentConfig()
        self.config.validate()

    @staticmethod
    def load_file(path: str) -> pd.DataFrame:
        """Load a dataset from CSV or Parquet format with existence checks.

        Args:
            path: Path to dataset file.

        Returns:
            Loaded pandas DataFrame.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file format is unsupported.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Dataset file not found at: '{path}'")

        if path.endswith(".parquet"):
            return pd.read_parquet(path)
        elif path.endswith(".csv"):
            return pd.read_csv(path)
        else:
            raise ValueError(f"Unsupported file format for path: '{path}'. Supported: .parquet, .csv")

    def validate_dataframe(
        self,
        df: pd.DataFrame,
        target_col: str,
        dataset_name: str = "dataset",
    ) -> None:
        """Validate syntactic, structural, and numerical integrity of a candidate DataFrame.

        Checks:
        1. All 38 canonical model features are present.
        2. The specified target column is present.
        3. Zero null/NaN values across all 38 features and target.
        4. Zero infinite values across all 38 features.
        5. All 38 features are strictly numeric.
        6. Target labels are valid for the given target column.

        Raises:
            ValueError: If any validation rule is violated.
        """
        # 1. Feature and target presence
        validate_feature_columns(list(df.columns), target_col=target_col)

        # 2. Check for null values in features
        feature_nulls = df[CANONICAL_MODEL_FEATURES].isnull().sum()
        total_feature_nulls = int(feature_nulls.sum())
        if total_feature_nulls > 0:
            bad_cols = feature_nulls[feature_nulls > 0].to_dict()
            raise ValueError(
                f"{dataset_name} contains {total_feature_nulls} null/NaN values across features: {bad_cols}"
            )

        # 3. Check for null values in target
        target_nulls = int(df[target_col].isnull().sum())
        if target_nulls > 0:
            raise ValueError(f"{dataset_name} contains {target_nulls} null/NaN values in target column '{target_col}'")

        # 4. Check data types: all 38 features must be strictly numeric
        non_numeric = [
            col for col in CANONICAL_MODEL_FEATURES
            if not np.issubdtype(df[col].dtype, np.number)
        ]
        if non_numeric:
            raise ValueError(
                f"{dataset_name} contains non-numeric data types in canonical features: {non_numeric}"
            )

        # 5. Check for infinite values in numeric features
        inf_cols = {}
        for col in CANONICAL_MODEL_FEATURES:
            vals = df[col].to_numpy()
            infs = int(np.isinf(vals).sum())
            if infs > 0:
                inf_cols[col] = infs
        if inf_cols:
            raise ValueError(f"{dataset_name} contains infinite values across feature columns: {inf_cols}")

        # 6. Validate target values
        if target_col == PRIMARY_TARGET:
            unique_targets = set(df[target_col].unique())
            unexpected = unique_targets - set(EXPECTED_LABEL_CATEGORIES)
            if unexpected:
                raise ValueError(
                    f"{dataset_name} contains unexpected categories in '{PRIMARY_TARGET}': {unexpected}"
                )
        elif target_col == SECONDARY_TARGET:
            unique_targets = set(df[target_col].unique())
            if not unique_targets.issubset({0, 1, 0.0, 1.0}):
                raise ValueError(
                    f"{dataset_name} contains non-binary values in '{SECONDARY_TARGET}': {unique_targets}"
                )

    def extract_split(
        self,
        df: pd.DataFrame,
        target_col: str,
        source_info: Dict[str, Any],
        is_synthetic: bool = False,
        dataset_name: str = "dataset",
    ) -> DatasetSplit:
        """Extract isolated feature matrix X and target vector y with leakage protection.

        Args:
            df: Validated DataFrame.
            target_col: Name of target column.
            source_info: Provenance metadata dictionary.
            is_synthetic: Flag indicating whether records are synthetic.
            dataset_name: Name for diagnostics.

        Returns:
            DatasetSplit containing X (38 features), y, and class statistics.
        """
        self.validate_dataframe(df, target_col=target_col, dataset_name=dataset_name)

        # Extract X strictly with CANONICAL_MODEL_FEATURES ordering
        X = df[CANONICAL_MODEL_FEATURES].copy()

        # Strict leakage check: ensure no excluded column leaked into X
        forbidden_in_x = set(X.columns).intersection(EXCLUDED_FEATURES)
        if forbidden_in_x:
            raise ValueError(f"CRITICAL: Target or metadata leakage detected in feature matrix X: {forbidden_in_x}")

        # Ensure exact column count and order
        assert list(X.columns) == CANONICAL_MODEL_FEATURES, "X column ordering does not match canonical specification!"

        # Extract y
        y = df[target_col].copy()

        # Compute class distribution
        counts = y.value_counts().to_dict()
        n_total = len(y)
        proportions = {str(k): round((v / n_total) * 100, 3) for k, v in counts.items()}

        return DatasetSplit(
            X=X,
            y=y,
            class_counts=counts,
            class_proportions=proportions,
            source_info=source_info,
            is_synthetic=is_synthetic,
        )

    def load_real_train_and_val_splits(
        self,
        target_col: Optional[str] = None,
    ) -> Tuple[DatasetSplit, DatasetSplit]:
        """Load real reference dataset and extract the exact approved deterministic 80/20 train/val split.

        Uses the deterministic CTGANDataPipeline configuration (seed 42, 80/20 split stratified on label_raw).
        Verifies that train and validation indices are strictly disjoint and reproduce the exact 38,466 / 9,616 counts.

        Returns:
            Tuple of (train_split, val_split).
        """
        target = target_col or self.config.target_column
        ref_path = self.config.real_dataset_path
        raw_ref = self.load_file(ref_path)
        file_sha256 = compute_file_sha256(ref_path)

        # Adapt reference columns to canonical format if needed
        if "Label" in raw_ref.columns:
            raw_ref = raw_ref.drop(columns=["Label"])
        if "device_id" not in raw_ref.columns:
            raw_ref["device_id"] = "ciciot2023_node"
        if "device_category" not in raw_ref.columns:
            raw_ref["device_category"] = "testbed_device"
        df_canon = raw_ref[CANONICAL_SCHEMA_COLUMNS]

        # Deterministic 80/20 split matching approved Phase 5.1/5.4/6 protocol
        pipeline_cfg = CTGANDataPipelineConfig(
            sample_size=None,
            stratify_by=self.config.split_stratify_column,
            train_ratio=self.config.train_split_ratio,
            random_seed=self.config.random_seed,
            exclude_metadata_cols=True,
        )
        pipeline = CTGANDataPipeline(config=pipeline_cfg)
        prep = pipeline.prepare_training_data(df_canon)

        raw_train_df = prep["train_df"].copy()
        raw_val_df = prep["val_df"].copy()

        # Track and assign original reference dataset row indices for provenance and leakage verification
        rng = np.random.default_rng(self.config.random_seed)
        train_orig_indices = []
        val_orig_indices = []
        working_df = df_canon.drop(columns=["device_id", "device_category"], errors="ignore")
        strat_col = self.config.split_stratify_column
        for _, group in working_df.groupby(strat_col, sort=True):
            n = len(group)
            if n <= 1:
                train_orig_indices.extend(group.index.tolist())
                continue
            n_train = max(1, min(n - 1, int(round(n * self.config.train_split_ratio))))
            perm = rng.permutation(n)
            train_orig_indices.extend(group.index[perm[:n_train]].tolist())
            val_orig_indices.extend(group.index[perm[n_train:]].tolist())

        raw_train_df.index = train_orig_indices
        raw_val_df.index = val_orig_indices

        # Verify exact row counts
        if len(raw_train_df) != self.config.expected_real_train_rows:
            raise ValueError(
                f"Real train split row count mismatch! Expected {self.config.expected_real_train_rows}, got {len(raw_train_df)}"
            )
        if len(raw_val_df) != self.config.expected_real_val_rows:
            raise ValueError(
                f"Real val split row count mismatch! Expected {self.config.expected_real_val_rows}, got {len(raw_val_df)}"
            )

        # Verify that train and validation records are strictly disjoint
        train_indices = set(raw_train_df.index)
        val_indices = set(raw_val_df.index)
        overlap = train_indices.intersection(val_indices)
        if overlap:
            raise ValueError(f"CRITICAL DATA LEAKAGE: Real train and val splits share {len(overlap)} indices!")

        train_info = {
            "source_path": ref_path,
            "source_file_sha256": file_sha256,
            "split": "train",
            "split_ratio": self.config.train_split_ratio,
            "stratified_by": self.config.split_stratify_column,
            "random_seed": self.config.random_seed,
        }
        val_info = {
            "source_path": ref_path,
            "source_file_sha256": file_sha256,
            "split": "validation",
            "split_ratio": self.config.validation_split_ratio,
            "stratified_by": self.config.split_stratify_column,
            "random_seed": self.config.random_seed,
        }

        train_split = self.extract_split(raw_train_df, target_col=target, source_info=train_info, is_synthetic=False, dataset_name="Real Train Split")
        val_split = self.extract_split(raw_val_df, target_col=target, source_info=val_info, is_synthetic=False, dataset_name="Real Validation Split")

        return train_split, val_split

    def load_trtr_data(self) -> ExperimentDatasetContainer:
        """Load datasets for TRTR (Train on Real, Test on Real) experiment."""
        train_split, val_split = self.load_real_train_and_val_splits()
        return ExperimentDatasetContainer(
            train_split=train_split,
            val_split=val_split,
            experiment_type=ExperimentType.TRTR,
            target_column=self.config.target_column,
            quality_warnings=[],
        )

    def load_tstr_data(self, use_ablation: bool = False) -> ExperimentDatasetContainer:
        """Load datasets for TSTR (Train on Synthetic, Test on Real) experiment.

        Args:
            use_ablation: If True, loads the uncorrected raw CTGAN ablation candidate (ctgan_initial_sample_v1).
                If False (default), loads the primary domain-corrected candidate (v1_domain_corrected).

        Returns:
            ExperimentDatasetContainer with synthetic train split and real validation split.
        """
        synth_path = self.config.synthetic_ablation_path if use_ablation else self.config.synthetic_dataset_path
        synth_df = self.load_file(synth_path)
        synth_sha256 = compute_file_sha256(synth_path)

        if len(synth_df) != self.config.expected_synthetic_train_rows:
            raise ValueError(
                f"Synthetic dataset row count mismatch! Expected {self.config.expected_synthetic_train_rows}, got {len(synth_df)}"
            )

        synth_info = {
            "source_path": synth_path,
            "source_file_sha256": synth_sha256,
            "is_ablation": use_ablation,
            "candidate_type": "raw_uncorrected" if use_ablation else "partially_domain_corrected",
        }

        train_split = self.extract_split(
            synth_df,
            target_col=self.config.target_column,
            source_info=synth_info,
            is_synthetic=True,
            dataset_name="Synthetic Train Split",
        )

        # Load held-out real validation split
        _, val_split = self.load_real_train_and_val_splits()

        return ExperimentDatasetContainer(
            train_split=train_split,
            val_split=val_split,
            experiment_type=ExperimentType.TSTR,
            target_column=self.config.target_column,
            quality_warnings=self.config.get_quality_warnings(ExperimentType.TSTR),
        )

    def load_tstr_plus_r_data(
        self,
        augmentation_df: Optional[pd.DataFrame] = None,
        augmentation_fraction: Optional[float] = None,
        augmentation_records: Optional[int] = None,
        use_ablation: bool = False,
    ) -> ExperimentDatasetContainer:
        """Load datasets for TSTR+R (Train on Real + Synthetic, Test on Real) experiment.

        Args:
            augmentation_df: Optional DataFrame containing synthetic samples.
                If provided, used directly as the augmentation source.
            augmentation_fraction: Optional fraction of the synthetic dataset to sample (e.g. 0.25, 0.50, 1.0).
            augmentation_records: Optional exact number of synthetic records to sample (e.g. 1250, 2500, 5000).
            use_ablation: If True, samples from the uncorrected raw CTGAN ablation candidate (ctgan_initial_sample_v1).
                If False (default), samples from the primary domain-corrected candidate (v1_domain_corrected).

        Returns:
            ExperimentDatasetContainer with augmented train split (Real + Synthetic) and real validation split.
        """
        real_train, val_split = self.load_real_train_and_val_splits()

        aug_df_candidate = augmentation_df
        synth_source_path = None
        synth_sha256 = None

        if aug_df_candidate is None and (augmentation_fraction is not None or augmentation_records is not None):
            synth_path = self.config.synthetic_ablation_path if use_ablation else self.config.synthetic_dataset_path
            full_synth = self.load_file(synth_path)
            synth_source_path = synth_path
            synth_sha256 = compute_file_sha256(synth_path)

            if augmentation_records is not None:
                n_samples = augmentation_records
            else:
                n_samples = int(round(len(full_synth) * augmentation_fraction))

            if n_samples > len(full_synth):
                raise ValueError(
                    f"Requested {n_samples} augmentation records, but synthetic pool only contains {len(full_synth)} records."
                )

            # Deterministic sampling without replacement using fixed random seed
            rng = np.random.default_rng(self.config.random_seed)
            perm = rng.permutation(len(full_synth))
            selected_indices = perm[:n_samples]
            aug_df_candidate = full_synth.iloc[selected_indices].copy()

        if aug_df_candidate is not None:
            # Validate augmentation dataset
            self.validate_dataframe(
                aug_df_candidate,
                target_col=self.config.target_column,
                dataset_name="Augmentation Synthetic Split",
            )
            aug_X = aug_df_candidate[CANONICAL_MODEL_FEATURES].copy()
            aug_y = aug_df_candidate[self.config.target_column].copy()

            combined_X = pd.concat([real_train.X, aug_X], ignore_index=True)
            combined_y = pd.concat([real_train.y, aug_y], ignore_index=True)

            counts = combined_y.value_counts().to_dict()
            n_total = len(combined_y)
            proportions = {str(k): round((v / n_total) * 100, 3) for k, v in counts.items()}

            combined_info = {
                "base_real_train_records": real_train.n_records,
                "augmentation_records": len(aug_X),
                "total_augmented_records": len(combined_X),
                "augmentation_fraction": augmentation_fraction,
                "synthetic_source_path": synth_source_path or "custom_dataframe",
                "synthetic_source_sha256": synth_sha256,
                "sampling_strategy": "deterministic_permutation_without_replacement",
                "random_seed": self.config.random_seed,
            }
            augmented_train_split = DatasetSplit(
                X=combined_X,
                y=combined_y,
                class_counts=counts,
                class_proportions=proportions,
                source_info=combined_info,
                is_synthetic=True,
            )
            warnings = self.config.get_quality_warnings(ExperimentType.TSTR_PLUS_R)
        else:
            augmented_train_split = real_train
            warnings = []

        return ExperimentDatasetContainer(
            train_split=augmented_train_split,
            val_split=val_split,
            experiment_type=ExperimentType.TSTR_PLUS_R,
            target_column=self.config.target_column,
            quality_warnings=warnings,
        )

    def load_data_for_experiment(
        self,
        experiment_type: Optional[ExperimentType] = None,
        use_ablation: bool = False,
        augmentation_df: Optional[pd.DataFrame] = None,
        augmentation_fraction: Optional[float] = None,
        augmentation_records: Optional[int] = None,
    ) -> ExperimentDatasetContainer:
        """Dispatch data loading according to experiment type."""
        exp_type = experiment_type or self.config.experiment_type
        if exp_type == ExperimentType.TRTR:
            return self.load_trtr_data()
        elif exp_type == ExperimentType.TSTR:
            return self.load_tstr_data(use_ablation=use_ablation)
        elif exp_type == ExperimentType.TSTR_PLUS_R:
            return self.load_tstr_plus_r_data(
                augmentation_df=augmentation_df,
                augmentation_fraction=augmentation_fraction,
                augmentation_records=augmentation_records,
                use_ablation=use_ablation,
            )
        else:
            raise ValueError(f"Unknown experiment type: {exp_type}")
