"""
IoTSynth AI - CTGAN Model Wrapper Module (Phase 5.2)

Provides a production-grade, modular wrapper around SDV's CTGANSynthesizer (SDV 2.2.0 / CTGAN 0.13.0).
Integrates with CTGANDataPipeline to enforce:
  - Canonical 44-column schema adherence.
  - Correct categorical/numerical feature type classification.
  - Anomaly detection target leakage safeguards.
  - Safe model artifact serialization with overwrite protection.
  - Training state tracking and loss diagnostics.

This module provides the model interface for Phase 5.2.
Model fitting (model.fit) is executed in Phase 5.3 during actual training runs.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import random
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import cloudpickle
import numpy as np
import pandas as pd
from sdv.metadata import Metadata
from sdv.single_table import CTGANSynthesizer

from simulator.traffic_schema import (
    CANONICAL_SCHEMA_COLUMNS,
    CONTINUOUS_NUMERICAL_FEATURES,
    DISCRETE_COUNT_FEATURES,
    BINARY_INDICATOR_FEATURES,
    CATEGORICAL_STRING_FEATURES,
    MODEL_INPUT_FEATURES,
)
from synthetic_engine.ctgan_config import CTGANConfig
from synthetic_engine.ctgan_data_pipeline import (
    CTGAN_DISCRETE_COLUMNS,
    LABEL_AND_TARGET_COLUMNS,
    METADATA_COLUMNS,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# CTGAN Model Wrapper
# ==============================================================================

class CTGANModel:
    """Production wrapper for CTGAN tabular synthesis under SDV 2.2.0.

    Responsibilities:
      1. Model configuration and hyperparameter validation.
      2. Automated SDV Metadata construction and feature-role mapping.
      3. Training data validation (nulls, infinities, minimum row checks).
      4. Fitting interface with training-state tracking.
      5. Conditional and unconditional synthetic sampling interface.
      6. Safe artifact persistence (config, metadata, weights) with overwrite guards.
      7. Model deserialization and restoration.
    """

    MODEL_VERSION: str = "1.0.0"

    def __init__(
        self,
        config: Optional[CTGANConfig] = None,
    ) -> None:
        """Initialize CTGANModel with configuration.

        Args:
            config: CTGANConfig instance. If None, default CTGANConfig is used.
        """
        self.config = config or CTGANConfig()
        self.config.validate()

        self.synthesizer: Optional[CTGANSynthesizer] = None
        self.sdv_metadata: Optional[Metadata] = None
        self.is_fitted: bool = False
        self.training_metadata: Dict[str, Any] = {}
        self.feature_columns: List[str] = []
        self.discrete_columns: List[str] = []

    # ------------------------------------------------------------------
    # 1. Metadata & Feature Handling
    # ------------------------------------------------------------------

    @classmethod
    def build_sdv_metadata(
        cls,
        df: pd.DataFrame,
        discrete_columns: Optional[List[str]] = None,
        table_name: str = "traffic",
    ) -> Tuple[Metadata, List[str]]:
        """Construct SDV 2.2.0 Metadata from a prepared training DataFrame.

        Explicitly sets discrete/categorical features as sdtype='categorical'
        and continuous features as sdtype='numerical'.

        Args:
            df: Training DataFrame (e.g., from CTGANDataPipeline).
            discrete_columns: List of column names that must be treated as discrete.
                If None, uses canonical CTGAN_DISCRETE_COLUMNS filtered by df.columns.
            table_name: Name of the table in SDV Metadata. Defaults to 'traffic'.

        Returns:
            Tuple of (sdv_metadata, verified_discrete_columns).
        """
        if df.empty:
            raise ValueError("Cannot build SDV Metadata from an empty DataFrame.")

        # Detect initial metadata
        metadata = Metadata.detect_from_dataframes({table_name: df})
        table_meta = metadata.tables[table_name]

        # Resolve discrete columns
        if discrete_columns is not None:
            resolved_discrete = [c for c in discrete_columns if c in df.columns]
        else:
            resolved_discrete = [c for c in CTGAN_DISCRETE_COLUMNS if c in df.columns]

        # Enforce categorical sdtype on discrete columns
        for col in resolved_discrete:
            if col in table_meta.columns:
                current_sdtype = table_meta.columns[col].get("sdtype")
                if current_sdtype != "categorical":
                    table_meta.update_column(col, sdtype="categorical")

        # Enforce numerical sdtype on continuous columns
        for col in list(table_meta.columns):
            if col not in resolved_discrete:
                current_sdtype = table_meta.columns[col].get("sdtype")
                if current_sdtype != "numerical":
                    table_meta.update_column(col, sdtype="numerical")

        return metadata, sorted(resolved_discrete)

    # ------------------------------------------------------------------
    # 2. Training Data Validation
    # ------------------------------------------------------------------

    def validate_training_data(self, df: pd.DataFrame) -> None:
        """Verify that training data meets CTGAN architectural preconditions.

        Checks:
          - DataFrame is non-empty.
          - Row count >= batch_size.
          - No NaN / null values.
          - No infinite values in numeric columns.
          - Conditioning labels are present.

        Args:
            df: Prepared training DataFrame.

        Raises:
            ValueError: If training data fails any check.
        """
        if not isinstance(df, pd.DataFrame):
            raise ValueError(f"train_df must be a pandas DataFrame, got: {type(df).__name__}")

        if df.empty:
            raise ValueError("Training DataFrame is empty.")

        if len(df) < self.config.batch_size:
            raise ValueError(
                f"Training data has {len(df)} rows, but batch_size is {self.config.batch_size}. "
                f"Training data row count must be >= batch_size."
            )

        # Check for nulls
        null_counts = df.isnull().sum()
        if null_counts.any():
            cols_with_null = null_counts[null_counts > 0].to_dict()
            raise ValueError(f"Training data contains null/NaN values: {cols_with_null}")

        # Check for infinities in numeric columns
        num_cols = df.select_dtypes(include=[np.number]).columns
        for col in num_cols:
            vals = df[col].to_numpy()
            if not np.all(np.isfinite(vals)):
                raise ValueError(f"Training column '{col}' contains infinite values.")

        # Verify conditioning labels exist
        missing_labels = [c for c in LABEL_AND_TARGET_COLUMNS if c not in df.columns]
        if missing_labels:
            logger.warning(
                f"Conditioning labels missing from training data: {missing_labels}. "
                "Class-conditioned generation may not be possible."
            )

    # ------------------------------------------------------------------
    # 3. Model Fitting Interface
    # ------------------------------------------------------------------

    def fit(
        self,
        train_df: pd.DataFrame,
        discrete_columns: Optional[List[str]] = None,
        dataset_name: str = "ciciot2023_prepared",
        table_name: str = "traffic",
    ) -> "CTGANModel":
        """Fit the CTGAN generative model on prepared training data.

        NOTE: In Phase 5.2, this interface is verified without executing actual
        training runs. Actual model fitting is performed in Phase 5.3.

        Args:
            train_df: Prepared training DataFrame.
            discrete_columns: Optional list of discrete columns overriding defaults.
            dataset_name: Identifier for the source dataset.
            table_name: Table name in SDV Metadata.

        Returns:
            self with is_fitted=True.
        """
        self.validate_training_data(train_df)

        # Set seeds for reproducibility
        if self.config.random_seed is not None:
            random.seed(self.config.random_seed)
            np.random.seed(self.config.random_seed)

        # Build SDV metadata
        self.sdv_metadata, self.discrete_columns = self.build_sdv_metadata(
            df=train_df,
            discrete_columns=discrete_columns,
            table_name=table_name,
        )
        self.feature_columns = list(train_df.columns)

        # Instantiate CTGANSynthesizer
        sdv_kwargs = self.config.to_sdv_kwargs()
        self.synthesizer = CTGANSynthesizer(
            metadata=self.sdv_metadata,
            **sdv_kwargs,
        )

        start_time = time.time()
        start_iso = datetime.now(timezone.utc).isoformat()

        logger.info(
            f"Fitting CTGAN on {len(train_df)} rows × {len(train_df.columns)} cols "
            f"for {self.config.epochs} epochs (batch_size={self.config.batch_size}, "
            f"pac={self.config.pac}, cuda={self.config.cuda})..."
        )

        # Execute training
        self.synthesizer.fit({table_name: train_df})

        elapsed_sec = time.time() - start_time
        end_iso = datetime.now(timezone.utc).isoformat()

        self.is_fitted = True
        self.training_metadata = {
            "dataset_name": dataset_name,
            "table_name": table_name,
            "num_rows": len(train_df),
            "num_columns": len(train_df.columns),
            "feature_columns": self.feature_columns,
            "discrete_columns": self.discrete_columns,
            "start_time": start_iso,
            "end_time": end_iso,
            "elapsed_seconds": round(elapsed_sec, 2),
            "config": self.config.to_dict(),
            "model_version": self.MODEL_VERSION,
            "training_completed": True,
        }

        return self

    # ------------------------------------------------------------------
    # 4. Sampling Interface
    # ------------------------------------------------------------------

    def sample(
        self,
        num_rows: int,
        conditions: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """Sample synthetic IoT network traffic records from the fitted model.

        Args:
            num_rows: Number of synthetic rows to generate. Must be positive.
            conditions: Optional dictionary of column-value pairs for conditional sampling
                (e.g., {'label_category': 'DDoS'} or {'is_attack': 1}).

        Returns:
            pd.DataFrame of synthetic network traffic records.

        Raises:
            RuntimeError: If called before model is fitted.
            ValueError: If num_rows <= 0.
        """
        if not self.is_fitted or self.synthesizer is None:
            raise RuntimeError(
                "CTGANModel must be fitted before sampling synthetic records. "
                "Call model.fit() first or load a pre-trained model via CTGANModel.load()."
            )

        if not isinstance(num_rows, int) or num_rows <= 0:
            raise ValueError(f"num_rows must be a positive integer, got: {num_rows}")

        if conditions:
            # Conditional sampling via SDV Condition objects
            from sdv.sampling import Condition
            condition_obj = Condition(num_rows=num_rows, column_values=conditions)
            synthetic = self.synthesizer.sample_from_conditions(
                conditions=[condition_obj],
                max_tries_per_batch=200,
            )
        else:
            synthetic = self.synthesizer.sample(num_rows=num_rows)

        if isinstance(synthetic, dict):
            t_name = self.training_metadata.get("table_name", "traffic")
            synthetic_df = synthetic.get(t_name, next(iter(synthetic.values())))
        else:
            synthetic_df = synthetic

        log1p_bounds = self.training_metadata.get("log1p_bounds")
        if isinstance(log1p_bounds, dict) and log1p_bounds:
            from synthetic_engine.ctgan_v2_pipeline import invert_log1p_transform
            synthetic_df = invert_log1p_transform(synthetic_df, log1p_bounds)

        return synthetic_df

    # ------------------------------------------------------------------
    # 5. Training Diagnostics
    # ------------------------------------------------------------------

    def get_loss_history(self) -> Optional[pd.DataFrame]:
        """Retrieve training loss history from the fitted synthesizer.

        Returns:
            pd.DataFrame with Generator and Discriminator loss per epoch,
            or None if the model is not fitted or loss values are unavailable.
        """
        if not self.is_fitted or self.synthesizer is None:
            return None

        try:
            return self.synthesizer.get_loss_values()
        except Exception as e:
            logger.warning(f"Could not retrieve loss values: {e}")
            return None

    def get_training_metadata(self) -> Dict[str, Any]:
        """Retrieve comprehensive training metadata."""
        return dict(self.training_metadata)

    # ------------------------------------------------------------------
    # 6. Model Artifact Persistence (Save / Load)
    # ------------------------------------------------------------------

    @classmethod
    def resolve_artifact_paths(
        cls,
        directory: Union[str, Path] = "models/ctgan",
        model_name: str = "ctgan_model",
        for_write: bool = False,
    ) -> Tuple[Path, Path, Path]:
        """Resolve config, metadata, and weights paths across v1/, v2/, custom/, and legacy layouts."""
        root = Path(directory)

        def _dir_tuple(base: Path) -> Tuple[Path, Path, Path]:
            return (
                base / f"{model_name}_config.json",
                base / f"{model_name}_metadata.json",
                base / f"{model_name}.pkl",
            )

        if model_name == "ctgan_device_aware_v2":
            preferred_dir = root / "v2"
        elif model_name == "ctgan_full_v1":
            preferred_dir = root / "v1"
        else:
            preferred_dir = root / "custom" / model_name

        candidates: List[Tuple[Path, Path, Path]] = [
            _dir_tuple(preferred_dir),
            _dir_tuple(root / model_name),
            (
                root / "configs" / f"{model_name}_config.json",
                root / "metadata" / f"{model_name}_metadata.json",
                root / "trained_models" / f"{model_name}.pkl",
            ),
        ]

        if not for_write:
            for cfg_p, meta_p, pkl_p in candidates:
                if pkl_p.exists():
                    return cfg_p, meta_p, pkl_p

        return candidates[0]

    @classmethod
    def discover_model_ids(
        cls,
        directory: Union[str, Path] = "models/ctgan",
    ) -> List[str]:
        """Discover all fitted CTGAN checkpoint IDs, ordering V2 first and V1 second."""
        import re

        root = Path(directory)
        if not root.exists():
            return []

        safe_re = re.compile(r"^[a-zA-Z0-9_\-]+$")
        discovered: List[str] = []
        seen: set[str] = set()

        search_patterns = [
            root / "v2" / "*.pkl",
            root / "v1" / "*.pkl",
            root / "custom",
            root / "trained_models" / "*.pkl",
        ]

        pkl_files: List[Path] = []
        for pattern in search_patterns:
            if pattern.name == "*.pkl":
                if pattern.parent.exists():
                    pkl_files.extend(sorted(pattern.parent.glob("*.pkl")))
            elif pattern.exists() and pattern.is_dir():
                pkl_files.extend(sorted(pattern.rglob("*.pkl")))

        for p in pkl_files:
            if p.is_file() and safe_re.match(p.stem) and p.stem not in seen:
                seen.add(p.stem)
                discovered.append(p.stem)

        ordered: List[str] = []
        for preferred in ("ctgan_device_aware_v2", "ctgan_full_v1"):
            if preferred in discovered:
                ordered.append(preferred)
                discovered.remove(preferred)
        return ordered + discovered

    def save(
        self,
        directory: Union[str, Path] = "models/ctgan",
        model_name: str = "ctgan_model",
        overwrite: bool = False,
    ) -> Dict[str, Path]:
        """Save model configuration, metadata, and weights cleanly into versioned/custom dirs."""
        config_path, meta_path, model_path = self.resolve_artifact_paths(
            directory=directory, model_name=model_name, for_write=True
        )
        for p in (config_path, meta_path, model_path):
            p.parent.mkdir(parents=True, exist_ok=True)

        # Overwrite guard
        if model_path.exists() and not overwrite:
            raise FileExistsError(
                f"Model artifact already exists at '{model_path}'. "
                "Set overwrite=True to replace the existing artifact."
            )

        # 1. Save config JSON
        config_data = self.config.to_dict()
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)

        # 2. Save metadata JSON
        full_metadata = {
            "model_name": model_name,
            "model_version": self.MODEL_VERSION,
            "is_fitted": self.is_fitted,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "training_metadata": self.training_metadata,
            "feature_columns": self.feature_columns,
            "discrete_columns": self.discrete_columns,
            "config": config_data,
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(full_metadata, f, indent=2)

        # 3. Save synthesizer weights via cloudpickle
        with open(model_path, "wb") as f:
            cloudpickle.dump(self.synthesizer, f)

        logger.info(f"Model artifacts successfully saved to: {model_path.parent}")
        return {
            "config_path": config_path,
            "metadata_path": meta_path,
            "model_path": model_path,
        }

    @classmethod
    def load(
        cls,
        directory: Union[str, Path] = "models/ctgan",
        model_name: str = "ctgan_model",
    ) -> "CTGANModel":
        """Load a saved CTGANModel instance from disk."""
        config_path, meta_path, model_path = cls.resolve_artifact_paths(
            directory=directory, model_name=model_name, for_write=False
        )

        for p, label in [(config_path, "Config"), (meta_path, "Metadata"), (model_path, "Model weights")]:
            if not p.exists():
                raise FileNotFoundError(f"{label} file not found at: {p}")

        # 1. Load config
        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = json.load(f)
        config = CTGANConfig.from_dict(config_dict)

        # 2. Load metadata
        with open(meta_path, "r", encoding="utf-8") as f:
            full_meta = json.load(f)

        # 3. Load synthesizer weights
        with open(model_path, "rb") as f:
            synthesizer = cloudpickle.load(f)

        # Construct restored instance
        model = cls(config=config)
        model.synthesizer = synthesizer
        model.is_fitted = full_meta.get("is_fitted", False)
        model.training_metadata = full_meta.get("training_metadata", {})
        model.feature_columns = full_meta.get("feature_columns", [])
        model.discrete_columns = full_meta.get("discrete_columns", [])
        if synthesizer is not None and hasattr(synthesizer, "metadata"):
            model.sdv_metadata = synthesizer.metadata

        logger.info(f"CTGANModel '{model_name}' successfully loaded from: {model_path.parent}")
        return model
