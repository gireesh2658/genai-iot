"""
IoTSynth AI - Evaluation Data Loader (Phase 6)
Loads and verifies real training, real validation, and synthetic datasets
ensuring strict provenance, column alignment, and data integrity.
"""

import os
import hashlib
from dataclasses import dataclass
from typing import Dict, Any, Tuple

import pandas as pd
import numpy as np

from simulator.traffic_schema import CANONICAL_SCHEMA_COLUMNS
from synthetic_engine.ctgan_data_pipeline import CTGANDataPipeline, CTGANDataPipelineConfig


def compute_file_sha256(path: str) -> str:
    """Compute the SHA-256 hash of a file on disk."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def compute_df_sha256(df: pd.DataFrame) -> str:
    """Compute deterministic SHA-256 hash of a DataFrame serialized to CSV bytes."""
    return hashlib.sha256(df.to_csv(index=False).encode("utf-8")).hexdigest()


@dataclass
class LoadedEvaluationDatasets:
    """Container holding verified real and synthetic datasets for evaluation."""
    train_df: pd.DataFrame
    val_df: pd.DataFrame
    synth_df: pd.DataFrame
    metadata: Dict[str, Any]


def load_evaluation_datasets(
    reference_path: str = "datasets/processed/ciciot2023_preprocessed_sample.parquet",
    synthetic_path: str = "datasets/generated/ctgan_initial_sample_v1.parquet",
    random_seed: int = 42,
) -> LoadedEvaluationDatasets:
    """Load reference training/validation splits and synthetic dataset with integrity verification.

    Args:
        reference_path: Path to the prepared reference Parquet dataset.
        synthetic_path: Path to the generated synthetic Parquet dataset.
        random_seed: Random seed used for the deterministic 80/20 train/val split.

    Returns:
        LoadedEvaluationDatasets container with train, val, synthetic DataFrames and metadata.

    Raises:
        FileNotFoundError: If required datasets are missing.
        ValueError: If schema or dimensions fail verification.
    """
    if not os.path.exists(reference_path):
        raise FileNotFoundError(f"Prepared reference dataset not found at: {reference_path}")
    if not os.path.exists(synthetic_path):
        raise FileNotFoundError(f"Synthetic dataset not found at: {synthetic_path}")

    # 1. Verify file hashes
    ref_sha256 = compute_file_sha256(reference_path)
    synth_sha256 = compute_file_sha256(synthetic_path)

    # 2. Load and adapt reference data
    raw_ref = pd.read_parquet(reference_path)
    if "Label" in raw_ref.columns:
        raw_ref = raw_ref.drop(columns=["Label"])
    if "device_id" not in raw_ref.columns:
        raw_ref["device_id"] = "ciciot2023_node"
    if "device_category" not in raw_ref.columns:
        raw_ref["device_category"] = "testbed_device"
    df_canon = raw_ref[CANONICAL_SCHEMA_COLUMNS]

    # Deterministic split via pipeline
    pipeline_cfg = CTGANDataPipelineConfig(
        sample_size=None,
        stratify_by="label_raw",
        train_ratio=0.80,
        random_seed=random_seed,
        exclude_metadata_cols=True,
    )
    pipeline = CTGANDataPipeline(config=pipeline_cfg)
    prep = pipeline.prepare_training_data(df_canon)

    train_df = prep["train_df"]
    val_df = prep["val_df"]

    # 3. Load synthetic data (.parquet or .csv) and project 44-col simulator outputs cleanly to 42 columns
    if synthetic_path.lower().endswith(".csv"):
        synth_df = pd.read_csv(synthetic_path)
    else:
        synth_df = pd.read_parquet(synthetic_path)

    schema_projected = False
    if "device_id" in synth_df.columns or "device_category" in synth_df.columns:
        synth_df = synth_df.drop(columns=["device_id", "device_category"], errors="ignore")
        schema_projected = True
    if set(train_df.columns).issubset(set(synth_df.columns)) and list(synth_df.columns) != list(train_df.columns):
        synth_df = synth_df[list(train_df.columns)].copy()

    # 4. Integrity assertions
    assert len(train_df.columns) == 42, f"Expected 42 train columns, got {len(train_df.columns)}"
    assert len(val_df.columns) == 42, f"Expected 42 val columns, got {len(val_df.columns)}"
    assert len(synth_df.columns) == 42, f"Expected 42 synth columns, got {len(synth_df.columns)}"
    assert list(train_df.columns) == list(synth_df.columns), "Column alignment mismatch between train and synthetic!"
    assert list(train_df.columns) == list(val_df.columns), "Column alignment mismatch between train and val!"

    train_sha256 = compute_df_sha256(train_df)
    val_sha256 = compute_df_sha256(val_df)
    synth_df_sha256 = compute_df_sha256(synth_df)

    metadata = {
        "reference_path": reference_path,
        "reference_sha256": ref_sha256,
        "reference_total_rows": len(raw_ref),
        "synthetic_path": synthetic_path,
        "synthetic_sha256": synth_sha256,
        "train_rows": len(train_df),
        "val_rows": len(val_df),
        "synthetic_rows": len(synth_df),
        "columns_count": len(train_df.columns),
        "columns": list(train_df.columns),
        "train_sha256": train_sha256,
        "val_sha256": val_sha256,
        "synthetic_df_sha256": synth_df_sha256,
        "discrete_columns": prep["discrete_columns"],
    }

    return LoadedEvaluationDatasets(
        train_df=train_df,
        val_df=val_df,
        synth_df=synth_df,
        metadata=metadata,
    )
