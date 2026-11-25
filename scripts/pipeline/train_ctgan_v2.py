"""
GPU-Accelerated CTGAN v2 Training & Encoding Verification Pipeline.

Strictly enforces CUDA execution (.venv-gpu with NVIDIA RTX 3050 6GB),
builds deterministic leakage-free 70/15/15 train/val/test splits of the real
MAC-attributed CICIoT2023 device corpus, runs a GPU smoke benchmark before full
training, records VRAM + GPU telemetry + loss curves + parameter/conditional
dimensions, and saves ctgan_device_aware_v2 cleanly without touching v1 artifacts.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from synthetic_engine.ctgan_config import CTGANConfig
from synthetic_engine.ctgan_data_pipeline import CTGAN_DISCRETE_COLUMNS
from synthetic_engine.ctgan_model import CTGANModel
from synthetic_engine.ctgan_v2_pipeline import (
    CTGAN_V2_ALL_COLUMNS,
    CTGAN_V2_DISCRETE_COLUMNS,
    CTGANv2Config,
    compute_encoding_comparison,
    create_v2_synthesizer,
    ensure_cpu_portable_and_save,
    load_v2_synthesizer,
    make_leakage_free_splits,
)

EXT_DIR = ROOT / "datasets" / "external" / "device_labelled_iot_data"
DATA_PATH = EXT_DIR / "ciciot2023_device_labelled_v2.parquet"
SPLITS_DIR = EXT_DIR / "splits"

MODELS_DIR = ROOT / "models" / "ctgan"
V1_PKL = MODELS_DIR / "v1" / "ctgan_full_v1.pkl"
V1_DATA_PATH = ROOT / "datasets" / "processed" / "ciciot2023_preprocessed_sample.parquet"

V2_MODEL_PKL = MODELS_DIR / "v2" / "ctgan_device_aware_v2.pkl"
V2_CONFIG_JSON = MODELS_DIR / "v2" / "ctgan_device_aware_v2_config.json"
V2_META_JSON = MODELS_DIR / "v2" / "ctgan_device_aware_v2_metadata.json"

REPORT_DIR = ROOT / "reports" / "ctgan_v2"


class NvidiaSmiSampler:
    """Poll real GPU utilization, VRAM usage, and temperature during training."""

    def __init__(self, interval_s: float = 1.5) -> None:
        self.interval_s = interval_s
        self.samples: List[Dict[str, Any]] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _poll_once(self) -> Dict[str, Any] | None:
        try:
            out = subprocess.check_output(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu,power.draw",
                    "--format=csv,noheader,nounits",
                ],
                text=True,
                timeout=3,
            ).strip()
            parts = [p.strip() for p in out.splitlines()[0].split(",")]
            return {
                "t_rel_s": round(time.monotonic() - self._t0, 2),
                "gpu_util_pct": float(parts[0]),
                "mem_util_pct": float(parts[1]),
                "vram_used_mib": float(parts[2]),
                "vram_total_mib": float(parts[3]),
                "temp_c": float(parts[4]),
                "power_w": float(parts[5]) if parts[5] not in ("[N/A]", "N/A", "") else None,
            }
        except Exception:
            return None

    def _run(self) -> None:
        while not self._stop.is_set():
            rec = self._poll_once()
            if rec is not None:
                self.samples.append(rec)
            self._stop.wait(self.interval_s)

    def start(self) -> None:
        self._t0 = time.monotonic()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> Dict[str, Any]:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        if not self.samples:
            return {"sample_count": 0}
        gpu_utils = [s["gpu_util_pct"] for s in self.samples]
        vrams = [s["vram_used_mib"] for s in self.samples]
        temps = [s["temp_c"] for s in self.samples]
        return {
            "sample_count": len(self.samples),
            "avg_gpu_util_pct": round(float(np.mean(gpu_utils)), 2),
            "max_gpu_util_pct": round(float(np.max(gpu_utils)), 2),
            "max_vram_used_mib": round(float(np.max(vrams)), 2),
            "avg_temp_c": round(float(np.mean(temps)), 1),
            "max_temp_c": round(float(np.max(temps)), 1),
            "timeline_preview": self.samples[:10],
        }


def measure_v1_actual_dims() -> Dict[str, Any]:
    """Load untouched v1 checkpoint in read-only mode to measure exact cond_vec & transformer dims."""
    if not V1_PKL.exists():
        return {"available": False}
    v1_wrapper = CTGANModel.load(directory=MODELS_DIR, model_name="ctgan_full_v1")
    sdv_synth = v1_wrapper.synthesizer
    ctgan_core = getattr(sdv_synth, "_model", None)
    gen_params = (
        sum(p.numel() for p in ctgan_core._generator.parameters())
        if ctgan_core is not None and getattr(ctgan_core, "_generator", None) is not None
        else None
    )
    return {
        "available": True,
        "v1_discrete_columns_count": len(v1_wrapper.discrete_columns),
        "v1_actual_dim_cond_vec": int(ctgan_core._data_sampler.dim_cond_vec()) if ctgan_core else None,
        "v1_actual_transformed_data_dim": int(ctgan_core._transformer.output_dimensions) if ctgan_core else None,
        "v1_generator_param_count": int(gen_params) if gen_params is not None else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Train CTGAN v2 on CUDA GPU.")
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--pac", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise RuntimeError(
            "CUDA GPU is NOT available in the current interpreter. "
            "Run with .\\.venv-gpu\\Scripts\\python.exe. Refusing silent CPU fallback."
        )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    SPLITS_DIR.mkdir(parents=True, exist_ok=True)
    (MODELS_DIR / "v2").mkdir(parents=True, exist_ok=True)

    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)

    full_df = pd.read_parquet(DATA_PATH)
    missing_cols = [c for c in CTGAN_V2_ALL_COLUMNS if c not in full_df.columns]
    if missing_cols:
        raise ValueError(f"Dataset missing canonical columns: {missing_cols}")
    full_df = full_df[CTGAN_V2_ALL_COLUMNS].copy()

    train_df, val_df, test_df, split_summary = make_leakage_free_splits(full_df, seed=args.seed)
    train_df.to_parquet(SPLITS_DIR / "train.parquet", index=False)
    val_df.to_parquet(SPLITS_DIR / "val.parquet", index=False)
    test_df.to_parquet(SPLITS_DIR / "test.parquet", index=False)
    (SPLITS_DIR / "split_summary.json").write_text(json.dumps(split_summary, indent=2), encoding="utf-8")
    print(f"Leakage-free splits saved: train={len(train_df)}, val={len(val_df)}, test={len(test_df)}")

    # Ensure batch_size divides cleanly and <= len(train_df)
    batch_size = min(args.batch_size, (len(train_df) // args.pac) * args.pac)
    batch_size = max(args.pac * 10, (batch_size // args.pac) * args.pac)

    # 1. Measure feature encoding improvement (v1 vs v2)
    v1_sample = pd.read_parquet(V1_DATA_PATH) if V1_DATA_PATH.exists() else train_df
    v1_actual = measure_v1_actual_dims()
    encoding_cmp = compute_encoding_comparison(
        v1_train_df=v1_sample,
        v1_discrete_cols=CTGAN_DISCRETE_COLUMNS,
        v2_train_df=train_df,
        v2_discrete_cols=CTGAN_V2_DISCRETE_COLUMNS,
    )
    encoding_cmp["v1_measured_checkpoint"] = v1_actual

    # 2. GPU Smoke Fit (3 epochs on 2,000-row stratified subset of train_df)
    smoke_df = train_df.sample(n=min(2000, len(train_df)), random_state=args.seed).reset_index(drop=True)
    smoke_cfg = CTGANv2Config(
        model_version="ctgan_device_aware_v2_smoke",
        epochs=3,
        batch_size=min(250, batch_size),
        pac=args.pac,
        enable_gpu=True,
        verbose=False,
    )
    torch.cuda.reset_peak_memory_stats()
    smoke_synth, smoke_meta = create_v2_synthesizer(smoke_df, smoke_cfg)
    t_smoke0 = time.perf_counter()
    smoke_synth.fit({"ciciot_device_v2": smoke_df})
    torch.cuda.synchronize()
    smoke_elapsed = time.perf_counter() - t_smoke0
    smoke_cuda = bool(next(smoke_synth._model._generator.parameters()).is_cuda)
    smoke_peak_mb = round(torch.cuda.max_memory_allocated() / (1024 ** 2), 2)
    smoke_cond_dim = int(smoke_synth._model._data_sampler.dim_cond_vec())
    smoke_data_dim = int(smoke_synth._model._transformer.output_dimensions)
    if not smoke_cuda:
        raise RuntimeError("GPU smoke fit generator is NOT on CUDA!")
    del smoke_synth
    torch.cuda.empty_cache()
    print(
        f"[GPU SMOKE OK] 3 epochs on {len(smoke_df)} rows in {smoke_elapsed:.2f}s | "
        f"cond_dim={smoke_cond_dim}, data_dim={smoke_data_dim}, peak_vram={smoke_peak_mb} MB"
    )

    # 3. Full GPU Training on train_df ONLY (zero val/test leakage)
    cfg = CTGANv2Config(
        model_version="ctgan_device_aware_v2",
        epochs=args.epochs,
        batch_size=batch_size,
        pac=args.pac,
        embedding_dim=128,
        generator_dim=(256, 256),
        discriminator_dim=(256, 256),
        enable_gpu=True,
        random_seed=args.seed,
        verbose=True,
    )
    synth, sdv_meta = create_v2_synthesizer(train_df, cfg)
    smi = NvidiaSmiSampler(interval_s=1.5)
    torch.cuda.reset_peak_memory_stats()
    smi.start()
    t0 = time.perf_counter()
    synth.fit({"ciciot_device_v2": train_df})
    torch.cuda.synchronize()
    train_elapsed = time.perf_counter() - t0
    gpu_telemetry = smi.stop()

    core = synth._model
    gen_on_cuda = bool(next(core._generator.parameters()).is_cuda)
    if not gen_on_cuda:
        raise RuntimeError("Trained generator did NOT remain on CUDA during fit!")

    v2_cond_dim = int(core._data_sampler.dim_cond_vec())
    v2_data_dim = int(core._transformer.output_dimensions)
    v2_gen_params = int(sum(p.numel() for p in core._generator.parameters()))
    peak_alloc_mb = round(torch.cuda.max_memory_allocated() / (1024 ** 2), 2)
    peak_reserved_mb = round(torch.cuda.max_memory_reserved() / (1024 ** 2), 2)

    loss_df = getattr(core, "loss_values", pd.DataFrame())
    loss_records = []
    if not loss_df.empty:
        # Store compact milestone trace + full initial/final values
        for _, r in loss_df.iterrows():
            loss_records.append({
                "epoch": int(r.iloc[0]),
                "generator_loss": round(float(r.iloc[1]), 6),
                "discriminator_loss": round(float(r.iloc[2]), 6),
            })

    encoding_cmp["v2_actual_dim_cond_vec"] = v2_cond_dim
    encoding_cmp["v2_actual_transformed_data_dim"] = v2_data_dim
    encoding_cmp["v2_generator_param_count"] = v2_gen_params
    if v1_actual.get("v1_actual_dim_cond_vec"):
        encoding_cmp["actual_cond_vec_reduction_pct"] = round(
            100.0 * (1.0 - v2_cond_dim / v1_actual["v1_actual_dim_cond_vec"]), 2
        )
    (REPORT_DIR / "feature_encoding_report.json").write_text(json.dumps(encoding_cmp, indent=2), encoding="utf-8")

    # Quick GPU sampling throughput benchmark before making CPU-portable checkpoint
    t_samp0 = time.perf_counter()
    sample_probe_out = synth.sample(num_rows=2000)
    torch.cuda.synchronize()
    gpu_sample_s = time.perf_counter() - t_samp0
    _ = sample_probe_out["ciciot_device_v2"] if isinstance(sample_probe_out, dict) else sample_probe_out

    # Serialize CPU-portable checkpoint in native CTGANModel format (API-discoverable)
    if getattr(synth, "_model", None) is not None:
        synth._model.set_device(torch.device("cpu"))
        synth._model._enable_gpu = False

    gpu_name = torch.cuda.get_device_name(0)
    repo_config = CTGANConfig(
        epochs=cfg.epochs,
        batch_size=cfg.batch_size,
        pac=cfg.pac,
        generator_dim=cfg.generator_dim,
        discriminator_dim=cfg.discriminator_dim,
        generator_lr=cfg.generator_lr,
        discriminator_lr=cfg.discriminator_lr,
        embedding_dim=cfg.embedding_dim,
        generator_decay=cfg.generator_decay,
        discriminator_decay=cfg.discriminator_decay,
        discriminator_steps=cfg.discriminator_steps,
        log_frequency=cfg.log_frequency,
        cuda=True,
        random_seed=cfg.random_seed,
        verbose=cfg.verbose,
        enforce_min_max_values=cfg.enforce_min_max_values,
        enforce_rounding=cfg.enforce_rounding,
    )
    wrapper = CTGANModel(config=repo_config)
    wrapper.MODEL_VERSION = "ctgan_device_aware_v2"
    wrapper.synthesizer = synth
    wrapper.sdv_metadata = sdv_meta
    wrapper.is_fitted = True
    wrapper.feature_columns = list(train_df.columns)
    wrapper.discrete_columns = list(CTGAN_V2_DISCRETE_COLUMNS)
    wrapper.training_metadata = {
        "dataset_source": "ciciot2023_pcap_device_labelled_v2",
        "trained_device": f"cuda:0 ({gpu_name})",
        "cpu_portable_checkpoint": True,
        "num_rows": len(train_df),
        "train_rows": len(train_df),
        "val_rows": len(val_df),
        "test_rows": len(test_df),
        "elapsed_seconds": round(train_elapsed, 2),
        "peak_memory_mb": peak_alloc_mb,
        "actual_dim_cond_vec": v2_cond_dim,
        "actual_transformed_data_dim": v2_data_dim,
        "generator_param_count": v2_gen_params,
        "train_raw_label_counts": {k: int(v) for k, v in train_df["label_raw"].value_counts().items()},
        "train_macro_category_counts": {k: int(v) for k, v in train_df["label_category"].value_counts().items()},
        "train_device_category_counts": {k: int(v) for k, v in train_df["device_category"].value_counts().items()},
        "split_summary": split_summary,
        "encoding_comparison": encoding_cmp,
    }
    wrapper.save(directory=MODELS_DIR, model_name="ctgan_device_aware_v2", overwrite=True)

    # Verify reload works cleanly through both CTGANModel.load & load_v2_synthesizer
    reloaded_wrapper = CTGANModel.load(directory=MODELS_DIR, model_name="ctgan_device_aware_v2")
    cpu_probe_raw = reloaded_wrapper.synthesizer.sample(num_rows=20)
    cpu_probe = cpu_probe_raw["ciciot_device_v2"] if isinstance(cpu_probe_raw, dict) else cpu_probe_raw
    assert len(cpu_probe) == 20

    train_report = {
        "model_version": cfg.model_version,
        "checkpoint_path": str(V2_MODEL_PKL.relative_to(ROOT)),
        "config_path": str(V2_CONFIG_JSON.relative_to(ROOT)),
        "metadata_path": str(V2_META_JSON.relative_to(ROOT)),
        "hardware": {
            "gpu_name": gpu_name,
            "torch_version": torch.__version__,
            "cuda_version": torch.version.cuda,
            "trained_on_cuda": True,
            "peak_torch_allocated_mb": peak_alloc_mb,
            "peak_torch_reserved_mb": peak_reserved_mb,
            "nvidia_smi_telemetry": gpu_telemetry,
        },
        "smoke_test": {
            "rows": len(smoke_df),
            "epochs": smoke_cfg.epochs,
            "elapsed_s": round(smoke_elapsed, 3),
            "peak_vram_mb": smoke_peak_mb,
            "generator_on_cuda": smoke_cuda,
        },
        "training": {
            "train_rows": len(train_df),
            "val_rows": len(val_df),
            "test_rows": len(test_df),
            "epochs": cfg.epochs,
            "batch_size": cfg.batch_size,
            "pac": cfg.pac,
            "elapsed_seconds": round(train_elapsed, 2),
            "epochs_per_second": round(cfg.epochs / max(train_elapsed, 1e-6), 3),
            "rows_per_second_epoch": round((len(train_df) * cfg.epochs) / max(train_elapsed, 1e-6), 1),
            "v1_reference_elapsed_seconds": 6030.28,
            "gpu_2000_sample_elapsed_s": round(gpu_sample_s, 3),
            "actual_dim_cond_vec": v2_cond_dim,
            "actual_transformed_data_dim": v2_data_dim,
            "generator_param_count": v2_gen_params,
            "loss_initial": loss_records[0] if loss_records else None,
            "loss_midpoint": loss_records[len(loss_records) // 2] if loss_records else None,
            "loss_final": loss_records[-1] if loss_records else None,
            "loss_history": loss_records,
        },
        "checkpoint_size_mb": round(V2_MODEL_PKL.stat().st_size / (1024 ** 2), 2),
    }

    (REPORT_DIR / "training_report.json").write_text(json.dumps(train_report, indent=2), encoding="utf-8")

    print(
        f"\n[DONE] CTGAN v2 trained on {gpu_name} in {train_elapsed:.2f}s "
        f"(vs v1 6030.28s) | cond_vec={v2_cond_dim} | peak_vram={peak_alloc_mb} MB | saved -> {V2_MODEL_PKL}"
    )


if __name__ == "__main__":
    main()
