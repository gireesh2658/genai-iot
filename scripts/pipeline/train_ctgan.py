"""
IoTSynth AI - Phase 5.4 Full CTGAN Training and Initial Synthetic Generation
Executes end-to-end training of the primary CTGAN model (ctgan_full_v1)
and generates an initial synthetic sample of 5,000 records.
"""

import os
import sys
import time
import json
import hashlib
from datetime import datetime, timezone
import tracemalloc

import numpy as np
import pandas as pd

from simulator.traffic_schema import CANONICAL_SCHEMA_COLUMNS
from synthetic_engine.ctgan_config import CTGANConfig
from synthetic_engine.ctgan_data_pipeline import CTGANDataPipeline, CTGANDataPipelineConfig
from synthetic_engine.ctgan_model import CTGANModel


class TeeLogger:
    def __init__(self, log_path: str):
        self.terminal = sys.stdout
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        self.log_file = open(log_path, "w", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.terminal.flush()
        self.log_file.write(message)
        self.log_file.flush()

    def flush(self):
        self.terminal.flush()
        self.log_file.flush()


def compute_file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def compute_df_sha256(df: pd.DataFrame) -> str:
    return hashlib.sha256(df.to_csv(index=False).encode("utf-8")).hexdigest()


def main():
    sys.stdout = TeeLogger("models/ctgan/training_full.log")
    print("=" * 80)
    print("IoTSynth AI - Phase 5.4 Full CTGAN Training Pipeline")
    print("=" * 80)

    # ------------------------------------------------------------------
    # Step 1: Data Preparation & Provenance Verification
    # ------------------------------------------------------------------
    source_parquet = "datasets/processed/ciciot2023_preprocessed_sample.parquet"
    if not os.path.exists(source_parquet):
        raise FileNotFoundError(f"Source prepared dataset not found: {source_parquet}")

    source_hash = compute_file_sha256(source_parquet)
    print(f"\n[1] Source Dataset Verification:")
    print(f"  Path: {source_parquet}")
    print(f"  SHA-256: {source_hash}")

    raw_df = pd.read_parquet(source_parquet)
    print(f"  Raw dimensions: {raw_df.shape[0]} rows × {raw_df.shape[1]} columns")

    # Adapt to canonical schema
    df_work = raw_df.copy()
    if "Label" in df_work.columns:
        df_work = df_work.drop(columns=["Label"])
    if "device_id" not in df_work.columns:
        df_work["device_id"] = "ciciot2023_node"
    if "device_category" not in df_work.columns:
        df_work["device_category"] = "testbed_device"
    df_canon = df_work[CANONICAL_SCHEMA_COLUMNS]

    # Prepare training data via pipeline (stratified by label_raw, 80/20 split)
    data_cfg = CTGANDataPipelineConfig(
        sample_size=None,
        stratify_by="label_raw",
        train_ratio=0.80,
        random_seed=42,
        exclude_metadata_cols=True,
    )
    pipeline = CTGANDataPipeline(config=data_cfg)
    prep = pipeline.prepare_training_data(df_canon)

    train_df = prep["train_df"]
    val_df = prep["val_df"]
    discrete_columns = prep["discrete_columns"]

    train_hash = compute_df_sha256(train_df)
    val_hash = compute_df_sha256(val_df)

    print(f"\n[2] Training & Validation Split Summary:")
    print(f"  Train DataFrame: {train_df.shape[0]} rows × {train_df.shape[1]} columns | SHA-256: {train_hash}")
    print(f"  Val DataFrame:   {val_df.shape[0]} rows × {val_df.shape[1]} columns | SHA-256: {val_hash}")
    print(f"  Discrete features: {len(discrete_columns)} columns")
    print(f"  Unique raw labels in train: {train_df['label_raw'].nunique()} / {raw_df['label_raw'].nunique()}")
    print(f"  Unique raw labels in val:   {val_df['label_raw'].nunique()} / {raw_df['label_raw'].nunique()}")

    # ------------------------------------------------------------------
    # Step 2: Pre-Training Safety & Validation Checks
    # ------------------------------------------------------------------
    print("\n[3] Pre-Training Safety Checks:")
    # Check nulls
    null_count = train_df.isnull().sum().sum()
    if null_count > 0:
        raise ValueError(f"Training data contains {null_count} null values!")
    print("  ✓ Zero null / NaN values confirmed.")

    # Check non-finite numbers
    num_cols = train_df.select_dtypes(include=[np.number]).columns
    for c in num_cols:
        if not np.all(np.isfinite(train_df[c].to_numpy())):
            raise ValueError(f"Training column '{c}' contains infinite values!")
    print("  ✓ Zero infinite values confirmed.")

    # Verify model target files do not exist
    model_name = "ctgan_full_v1"
    target_config, target_meta, target_weights = CTGANModel.resolve_artifact_paths(
        directory="models/ctgan", model_name=model_name, for_write=True
    )
    target_weights = str(target_weights)
    target_config = str(target_config)
    target_meta = str(target_meta)

    for tp in [target_weights, target_config, target_meta]:
        if os.path.exists(tp):
            raise FileExistsError(f"Target model artifact already exists: {tp}. Halting to prevent overwrite.")
    print(f"  ✓ Target model '{model_name}' artifacts do not already exist (overwrite protection verified).")

    # ------------------------------------------------------------------
    # Step 3: Model Configuration
    # ------------------------------------------------------------------
    model_cfg = CTGANConfig(
        epochs=150,
        batch_size=500,
        pac=10,
        generator_dim=(128, 128),
        discriminator_dim=(128, 128),
        generator_lr=0.0002,
        discriminator_lr=0.0002,
        embedding_dim=128,
        generator_decay=1e-6,
        discriminator_decay=1e-6,
        discriminator_steps=1,
        cuda=False,
        random_seed=42,
        verbose=True,
    )
    assert model_cfg.batch_size % model_cfg.pac == 0, "Invariant violation: batch_size % pac != 0"
    print(f"\n[4] CTGAN Full Configuration:")
    print(f"  Epochs: {model_cfg.epochs}")
    print(f"  Batch size: {model_cfg.batch_size}")
    print(f"  PAC: {model_cfg.pac} (Invariant {model_cfg.batch_size} % {model_cfg.pac} == 0 satisfied)")
    print(f"  Network dimensions: Gen={model_cfg.generator_dim}, Disc={model_cfg.discriminator_dim}")
    print(f"  Learning rates: Gen={model_cfg.generator_lr}, Disc={model_cfg.discriminator_lr}")
    print(f"  Execution mode: CPU (cuda={model_cfg.cuda})")
    print(f"  Random seed: {model_cfg.random_seed}")

    # ------------------------------------------------------------------
    # Step 4: CTGAN Training Execution
    # ------------------------------------------------------------------
    model = CTGANModel(config=model_cfg)
    assert not model.is_fitted, "Pre-condition failed: model is already fitted before training."

    print(f"\n[5] Launching Full CTGAN Training ({model_cfg.epochs} epochs on {len(train_df)} rows)...")
    tracemalloc.start()
    t_start_wall = time.time()
    t_start_cpu = time.process_time()

    model.fit(
        train_df=train_df,
        discrete_columns=discrete_columns,
        dataset_name="ciciot2023_preprocessed_sample",
        table_name="traffic",
    )

    t_wall_elapsed = time.time() - t_start_wall
    t_cpu_elapsed = time.process_time() - t_start_cpu
    _, peak_mem_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mem_mb = peak_mem_bytes / (1024 * 1024)
    print(f"\n[6] Training Execution Result:")
    print(f"  Status: SUCCESSFUL (is_fitted={model.is_fitted})")
    print(f"  Total Wall-clock Time: {t_wall_elapsed:.2f} seconds ({t_wall_elapsed / 60:.2f} minutes / {t_wall_elapsed / 3600:.2f} hours)")
    print(f"  Process CPU Time:      {t_cpu_elapsed:.2f} seconds")
    print(f"  Average Epoch Time:    {t_wall_elapsed / model_cfg.epochs:.2f} seconds/epoch")
    print(f"  Peak Python Memory:    {peak_mem_mb:.2f} MB")

    loss_df = model.get_loss_history()
    if loss_df is not None:
        print(f"\n[7] Loss History Summary (Total {len(loss_df)} epochs recorded):")
        print(f"  Initial Epoch 0: Gen Loss = {loss_df.iloc[0]['Generator Loss']:.4f}, Disc Loss = {loss_df.iloc[0]['Discriminator Loss']:.4f}")
        print(f"  Midpoint Epoch {len(loss_df)//2}: Gen Loss = {loss_df.iloc[len(loss_df)//2]['Generator Loss']:.4f}, Disc Loss = {loss_df.iloc[len(loss_df)//2]['Discriminator Loss']:.4f}")
        print(f"  Final Epoch {len(loss_df)-1}: Gen Loss = {loss_df.iloc[-1]['Generator Loss']:.4f}, Disc Loss = {loss_df.iloc[-1]['Discriminator Loss']:.4f}")

    # ------------------------------------------------------------------
    # Step 5: Save Model Artifacts
    # ------------------------------------------------------------------
    print(f"\n[8] Saving Model Artifacts to models/ctgan/...")
    # Inject dataset provenance into training metadata before save
    model.training_metadata["source_dataset_path"] = source_parquet
    model.training_metadata["source_dataset_sha256"] = source_hash
    model.training_metadata["train_dataframe_sha256"] = train_hash
    model.training_metadata["val_dataframe_sha256"] = val_hash
    model.training_metadata["train_rows"] = len(train_df)
    model.training_metadata["val_rows"] = len(val_df)
    model.training_metadata["wall_clock_elapsed_seconds"] = round(t_wall_elapsed, 2)
    model.training_metadata["process_cpu_elapsed_seconds"] = round(t_cpu_elapsed, 2)
    model.training_metadata["peak_memory_mb"] = round(peak_mem_mb, 2)
    model.training_metadata["train_raw_label_counts"] = train_df["label_raw"].value_counts().to_dict()
    model.training_metadata["train_macro_category_counts"] = train_df["label_category"].value_counts().to_dict()

    saved_paths = model.save(
        directory="models/ctgan",
        model_name=model_name,
        overwrite=False,
    )
    for k, v in saved_paths.items():
        v_size = os.path.getsize(v)
        v_hash = compute_file_sha256(v)
        print(f"  Saved {k}: {v} ({v_size:,} bytes | SHA-256: {v_hash})")

    # ------------------------------------------------------------------
    # Step 6: Initial Synthetic Generation & Quality Verification
    # ------------------------------------------------------------------
    print(f"\n[9] Initial Synthetic Generation (5,000 records)...")
    t0_sample = time.time()
    synth_df = model.sample(num_rows=5000)
    sample_elapsed = time.time() - t0_sample
    print(f"  Generated {len(synth_df)} records in {sample_elapsed:.2f} seconds ({len(synth_df)/sample_elapsed:.1f} rows/s).")

    # Validation of generated records
    print("\n[10] Synthetic Dataset Quality & Precondition Checks:")
    print(f"  Dimensions: {synth_df.shape[0]} rows × {synth_df.shape[1]} columns")
    assert synth_df.shape[0] == 5000, f"Expected 5,000 rows, got {synth_df.shape[0]}"
    assert list(synth_df.columns) == list(train_df.columns), "Column alignment mismatch between train and synthetic!"
    print("  ✓ Column count and ordering matches training DataFrame exactly.")

    # Missing & infinite checks
    synth_nulls = synth_df.isnull().sum().sum()
    print(f"  Missing / NaN values: {synth_nulls}")
    synth_num_cols = synth_df.select_dtypes(include=[np.number]).columns
    synth_infs = 0
    for c in synth_num_cols:
        synth_infs += (~np.isfinite(synth_df[c].to_numpy())).sum()
    print(f"  Infinite values: {synth_infs}")

    # Check binary target validity
    is_attack_vals = set(synth_df["is_attack"].unique())
    print(f"  'is_attack' values in synthetic: {is_attack_vals}")
    is_attack_valid = is_attack_vals.issubset({0, 1})
    print(f"  ✓ Binary target validity: {'Valid' if is_attack_valid else 'Invalid'}")

    # Macro category distribution in synthetic
    print("\n  Synthetic Macro-Category Distribution:")
    synth_macro_counts = synth_df["label_category"].value_counts()
    for cat, cnt in synth_macro_counts.items():
        pct = (cnt / len(synth_df)) * 100
        print(f"    {cat:<18}: {cnt:>5} ({pct:.2f}%)")

    # Raw label count in synthetic
    print(f"\n  Unique raw labels generated: {synth_df['label_raw'].nunique()} / 33")

    # Test class-conditioned sampling
    print("\n[11] Testing Class-Conditioned Sampling (100 rows for 'DDoS')...")
    try:
        cond_sample = model.sample(num_rows=100, conditions={"label_category": "DDoS"})
        ddos_match = (cond_sample["label_category"] == "DDoS").all()
        print(f"  Conditioned sampling succeeded! All 100 rows have label_category='DDoS': {ddos_match}")
    except Exception as e:
        print(f"  Conditioned sampling failed: {e}")

    # Save initial synthetic sample
    os.makedirs("datasets/generated", exist_ok=True)
    out_parquet = "datasets/generated/ctgan_initial_sample_v1.parquet"
    out_meta_path = "datasets/generated/ctgan_initial_sample_v1_metadata.json"

    synth_df.to_parquet(out_parquet, index=False)
    synth_parquet_hash = compute_file_sha256(out_parquet)
    synth_parquet_size = os.path.getsize(out_parquet)

    sample_meta = {
        "model_name": model_name,
        "model_weights_path": target_weights,
        "sample_size": len(synth_df),
        "num_columns": len(synth_df.columns),
        "columns": list(synth_df.columns),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sampling_elapsed_seconds": round(sample_elapsed, 2),
        "output_parquet_path": out_parquet,
        "output_parquet_size_bytes": synth_parquet_size,
        "output_parquet_sha256": synth_parquet_hash,
        "null_count": int(synth_nulls),
        "infinite_count": int(synth_infs),
        "macro_category_counts": synth_macro_counts.to_dict(),
        "raw_label_counts": synth_df["label_raw"].value_counts().to_dict(),
        "is_attack_counts": synth_df["is_attack"].value_counts().to_dict(),
    }
    with open(out_meta_path, "w", encoding="utf-8") as f:
        json.dump(sample_meta, f, indent=2)

    print(f"\n  Saved synthetic dataset: {out_parquet} ({synth_parquet_size:,} bytes | SHA-256: {synth_parquet_hash})")
    print(f"  Saved generation metadata: {out_meta_path}")

    print("\n" + "=" * 80)
    print("Phase 5.4 Full CTGAN Training and Initial Generation Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
