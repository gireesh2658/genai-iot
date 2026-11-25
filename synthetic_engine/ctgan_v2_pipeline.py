"""
CTGAN v2 Feature Encoding, Leakage-Free Splitting, Conditional Auditing,
and Hardware-Aware Post-Processing Registry.

Refines v1 encoding by converting all 15 protocol proportions (HTTP..LLC) and
5 packet/flag counts (Number, ack_count, syn_count, fin_count, rst_count) from
bloated categoricals to true numerical variables, shrinking the conditional vector
from 992 dimensions (25 discrete cols, without device IDs) to ~100-140 dimensions
while adding genuine physical device_id and device_category conditioning.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import torch
from sdv.metadata import Metadata
from sdv.sampling import Condition
from sdv.single_table import CTGANSynthesizer
from sklearn.model_selection import train_test_split

from simulator.traffic_schema import (
    BINARY_INDICATOR_FEATURES,
    CONTINUOUS_NUMERICAL_FEATURES,
    MODEL_INPUT_FEATURES,
)


# Features misclassified as discrete in CTGAN v1 (must remain numerical in v2)
V1_MISTAKEN_PROTOCOL_PROPORTIONS: List[str] = [
    c for c in BINARY_INDICATOR_FEATURES if c != "is_attack"
]  # 15 protocol fractions in [0.0, 1.0]

V1_MISTAKEN_NUMERIC_COUNTS: List[str] = [
    "Number",
    "ack_count",
    "syn_count",
    "fin_count",
    "rst_count",
]

# Complete 37 numerical features in CTGAN v2
CTGAN_V2_NUMERICAL_COLUMNS: List[str] = (
    list(CONTINUOUS_NUMERICAL_FEATURES)
    + V1_MISTAKEN_PROTOCOL_PROPORTIONS
    + V1_MISTAKEN_NUMERIC_COUNTS
)

# Genuine discrete / categorical features in CTGAN v2 (7 columns)
CTGAN_V2_DISCRETE_COLUMNS: List[str] = [
    "device_id",
    "device_category",
    "protocol_name",
    "Protocol Type",
    "label_raw",
    "label_category",
    "is_attack",
]

CTGAN_V2_ALL_COLUMNS: List[str] = list(MODEL_INPUT_FEATURES) + [
    "protocol_name",
    "label_raw",
    "label_category",
    "is_attack",
    "device_id",
    "device_category",
]


@dataclass
class CTGANv2Config:
    """Hyperparameters and hardware flags for GPU-accelerated CTGAN v2."""

    model_version: str = "ctgan_device_aware_v2"
    epochs: int = 200
    batch_size: int = 500
    pac: int = 10
    embedding_dim: int = 128
    generator_dim: Tuple[int, ...] = (256, 256)
    discriminator_dim: Tuple[int, ...] = (256, 256)
    generator_lr: float = 2e-4
    discriminator_lr: float = 2e-4
    generator_decay: float = 1e-6
    discriminator_decay: float = 1e-6
    discriminator_steps: int = 1
    log_frequency: bool = True
    enable_gpu: bool = True
    random_seed: int = 42
    verbose: bool = True
    enforce_min_max_values: bool = True
    enforce_rounding: bool = True

    def validate(self) -> None:
        if self.batch_size <= 0 or self.pac <= 0 or (self.batch_size % self.pac != 0):
            raise ValueError(
                f"batch_size ({self.batch_size}) must be positive and divisible by pac ({self.pac})."
            )
        if self.epochs <= 0:
            raise ValueError("epochs must be positive.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_version": self.model_version,
            "epochs": self.epochs,
            "batch_size": self.batch_size,
            "pac": self.pac,
            "embedding_dim": self.embedding_dim,
            "generator_dim": list(self.generator_dim),
            "discriminator_dim": list(self.discriminator_dim),
            "generator_lr": self.generator_lr,
            "discriminator_lr": self.discriminator_lr,
            "generator_decay": self.generator_decay,
            "discriminator_decay": self.discriminator_decay,
            "discriminator_steps": self.discriminator_steps,
            "log_frequency": self.log_frequency,
            "enable_gpu": self.enable_gpu,
            "random_seed": self.random_seed,
            "verbose": self.verbose,
            "enforce_min_max_values": self.enforce_min_max_values,
            "enforce_rounding": self.enforce_rounding,
        }


def compute_encoding_comparison(
    v1_train_df: pd.DataFrame,
    v1_discrete_cols: Sequence[str],
    v2_train_df: pd.DataFrame,
    v2_discrete_cols: Sequence[str] = CTGAN_V2_DISCRETE_COLUMNS,
) -> Dict[str, Any]:
    """Quantify conditional vector dimensionality and column classification differences (v1 vs v2)."""
    v1_card = {c: int(v1_train_df[c].nunique(dropna=True)) for c in v1_discrete_cols if c in v1_train_df.columns}
    v2_card = {c: int(v2_train_df[c].nunique(dropna=True)) for c in v2_discrete_cols if c in v2_train_df.columns}
    v1_cond_sum = int(sum(v1_card.values()))
    v2_cond_sum = int(sum(v2_card.values()))
    return {
        "v1_discrete_column_count": len(v1_card),
        "v1_nominal_categorical_level_sum": v1_cond_sum,
        "v1_has_device_conditioning": ("device_id" in v1_card or "device_category" in v1_card),
        "v1_discrete_cardinalities": v1_card,
        "v2_discrete_column_count": len(v2_card),
        "v2_nominal_categorical_level_sum": v2_cond_sum,
        "v2_has_device_conditioning": ("device_id" in v2_card and "device_category" in v2_card),
        "v2_discrete_cardinalities": v2_card,
        "reclassified_as_numerical_proportions": list(V1_MISTAKEN_PROTOCOL_PROPORTIONS),
        "reclassified_as_numerical_counts": list(V1_MISTAKEN_NUMERIC_COUNTS),
        "cond_level_reduction_ratio": round(v1_cond_sum / max(1, v2_cond_sum), 3),
    }


def make_leakage_free_splits(
    df: pd.DataFrame,
    train_frac: float = 0.70,
    val_frac: float = 0.15,
    test_frac: float = 0.15,
    seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Deterministically partition real device-labelled data into disjoint
    train / validation / held-out test splits, stratified by (device_category, label_category).
    Rare strata with < 4 rows fall back to label_category so every class populates test/train cleanly.
    """
    if not np.isclose(train_frac + val_frac + test_frac, 1.0):
        raise ValueError("Split fractions must sum to 1.0.")

    work = df.reset_index(drop=True).copy()
    strata = work["device_category"].astype(str) + "__" + work["label_category"].astype(str)
    counts = strata.value_counts()
    rare_mask = strata.isin(counts[counts < 4].index)
    strata = strata.where(~rare_mask, work["label_category"].astype(str))
    counts2 = strata.value_counts()
    if (counts2 < 3).any():
        strata = strata.where(~strata.isin(counts2[counts2 < 3].index), work["is_attack"].astype(str))

    idx_all = np.arange(len(work))
    holdout_frac = val_frac + test_frac
    idx_train, idx_hold, _, strata_hold = train_test_split(
        idx_all, strata, test_size=holdout_frac, stratify=strata, random_state=seed
    )

    rel_test = test_frac / holdout_frac
    hold_counts = pd.Series(strata_hold).value_counts()
    strata_hold_safe = pd.Series(strata_hold).where(
        ~pd.Series(strata_hold).isin(hold_counts[hold_counts < 2].index), "RARE_SINGLETON"
    )
    if (strata_hold_safe.value_counts() < 2).any():
        strata_hold_safe = None

    idx_val, idx_test = train_test_split(
        idx_hold,
        test_size=rel_test,
        stratify=strata_hold_safe,
        random_state=seed + 1,
    )

    assert len(set(idx_train) & set(idx_val)) == 0
    assert len(set(idx_train) & set(idx_test)) == 0
    assert len(set(idx_val) & set(idx_test)) == 0
    assert len(idx_train) + len(idx_val) + len(idx_test) == len(work)

    train_df = work.iloc[idx_train].reset_index(drop=True)
    val_df = work.iloc[idx_val].reset_index(drop=True)
    test_df = work.iloc[idx_test].reset_index(drop=True)

    summary = {
        "total_rows": int(len(work)),
        "train_rows": int(len(train_df)),
        "val_rows": int(len(val_df)),
        "test_rows": int(len(test_df)),
        "seed": seed,
        "train_label_category_counts": {k: int(v) for k, v in train_df["label_category"].value_counts().items()},
        "val_label_category_counts": {k: int(v) for k, v in val_df["label_category"].value_counts().items()},
        "test_label_category_counts": {k: int(v) for k, v in test_df["label_category"].value_counts().items()},
        "train_device_category_counts": {k: int(v) for k, v in train_df["device_category"].value_counts().items()},
        "val_device_category_counts": {k: int(v) for k, v in val_df["device_category"].value_counts().items()},
        "test_device_category_counts": {k: int(v) for k, v in test_df["device_category"].value_counts().items()},
    }
    return train_df, val_df, test_df, summary


def build_v2_sdv_metadata(df: pd.DataFrame, table_name: str = "ciciot_device_v2") -> Metadata:
    """
    Construct explicit SDV Metadata enforcing exact discrete vs numerical assignments.
    Prevents SDV auto-detection from casting low-cardinality numeric counts/proportions
    (e.g., Telnet, SMTP, IRC, IGMP) into categorical types.
    """
    meta = Metadata.detect_from_dataframes(data={table_name: df})
    for col in df.columns:
        if col in CTGAN_V2_DISCRETE_COLUMNS:
            meta.update_column(column_name=col, sdtype="categorical", table_name=table_name)
        else:
            meta.update_column(column_name=col, sdtype="numerical", table_name=table_name)
    meta.validate()
    return meta


def create_v2_synthesizer(
    train_df: pd.DataFrame,
    config: CTGANv2Config,
    table_name: str = "ciciot_device_v2",
) -> Tuple[CTGANSynthesizer, Metadata]:
    """Instantiate SDV CTGANSynthesizer for v2 with strict GPU guard when enable_gpu=True."""
    config.validate()
    if config.enable_gpu and not torch.cuda.is_available():
        raise RuntimeError(
            "CTGANv2Config(enable_gpu=True) requires CUDA, but torch.cuda.is_available() is False. "
            "Refusing silent CPU fallback."
        )

    metadata = build_v2_sdv_metadata(train_df, table_name=table_name)
    synth = CTGANSynthesizer(
        metadata=metadata,
        enforce_min_max_values=config.enforce_min_max_values,
        enforce_rounding=config.enforce_rounding,
        embedding_dim=config.embedding_dim,
        generator_dim=config.generator_dim,
        discriminator_dim=config.discriminator_dim,
        generator_lr=config.generator_lr,
        discriminator_lr=config.discriminator_lr,
        generator_decay=config.generator_decay,
        discriminator_decay=config.discriminator_decay,
        batch_size=config.batch_size,
        discriminator_steps=config.discriminator_steps,
        log_frequency=config.log_frequency,
        verbose=config.verbose,
        epochs=config.epochs,
        pac=config.pac,
        enable_gpu=config.enable_gpu,
    )
    return synth, metadata


def ensure_cpu_portable_and_save(
    synthesizer: CTGANSynthesizer,
    save_path: Path,
) -> None:
    """
    Move underlying PyTorch generator device cleanly to CPU prior to cloudpickle
    serialization so CPU-only FastAPI environments can unpickle and run inference
    while preserving GPU training telemetry separately in metadata/reports.
    """
    save_path.parent.mkdir(parents=True, exist_ok=True)
    if getattr(synthesizer, "_model", None) is not None:
        synthesizer._model.set_device(torch.device("cpu"))
        synthesizer._model._enable_gpu = False
    synthesizer.save(str(save_path))


def load_v2_synthesizer(model_path: Path, prefer_gpu: bool = False) -> CTGANSynthesizer:
    """Load a saved v2 CTGANSynthesizer and move it to GPU only if requested & available."""
    synth = CTGANSynthesizer.load(str(model_path))
    model = getattr(synth, "_model", None)
    if model is not None:
        if prefer_gpu:
            if not torch.cuda.is_available():
                raise RuntimeError("prefer_gpu=True requested, but CUDA is unavailable.")
            model._enable_gpu = True
            model.set_device(torch.device("cuda"))
        else:
            model._enable_gpu = False
            model.set_device(torch.device("cpu"))
    return synth


def conditional_sample_with_support_check(
    synthesizer: CTGANSynthesizer,
    train_df: pd.DataFrame,
    conditions_spec: Dict[str, Any],
    num_rows: int,
    table_name: str = "ciciot_device_v2",
    min_support_threshold: int = 20,
    max_tries_per_batch: int = 200,
) -> Tuple[Optional[pd.DataFrame], Dict[str, Any]]:
    """
    Validate empirical support in training corpus before conditional generation.
    Rejects unsupported zero-support combinations honestly instead of hallucinating.
    """
    mask = pd.Series(True, index=train_df.index)
    for k, v in conditions_spec.items():
        if k not in train_df.columns:
            return None, {"supported": False, "empirical_support": 0, "reason": f"Unknown column {k}"}
        mask &= train_df[k].astype(str) == str(v)

    support = int(mask.sum())
    if support == 0:
        return None, {
            "supported": False,
            "empirical_support": 0,
            "support_tier": "unsupported",
            "reason": f"Zero empirical training rows for combination {conditions_spec}.",
        }

    tier = "under_supported" if support < min_support_threshold else "well_supported"
    cond = Condition(column_values=conditions_spec, num_rows=num_rows, table_name=table_name)
    out = synthesizer.sample_from_conditions(conditions=[cond], max_tries_per_batch=max_tries_per_batch)
    df = out[table_name] if isinstance(out, dict) else out

    exact_matches = pd.Series(True, index=df.index)
    for k, v in conditions_spec.items():
        exact_matches &= df[k].astype(str) == str(v)

    audit = {
        "supported": True,
        "support_tier": tier,
        "empirical_support": support,
        "requested_rows": int(num_rows),
        "generated_rows": int(len(df)),
        "exact_condition_matches": int(exact_matches.sum()),
        "compliance_rate": round(float(exact_matches.mean()), 4) if len(df) > 0 else 0.0,
    }
    return df, audit
