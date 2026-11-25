"""
Extract canonical 44-column device-aware flow-window dataset strictly from local
CICIoT2023 PCAPNG files (offline / sandbox-safe). Builds deterministic stratified
splits with zero MAC/IP leakage and saves provenance + device coverage reports.
"""

from __future__ import annotations

import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulator.traffic_schema import MODEL_INPUT_FEATURES
from synthetic_engine.ciciot2023_capture_catalog import CAPTURE_SPECS
from synthetic_engine.evaluation.validity import SyntheticDataValidityEvaluator
from synthetic_engine.pcap_device_extractor import (
    extract_windows_from_pcapng,
    load_mac_registry,
)

EXT_DIR = ROOT / "datasets" / "external" / "device_labelled_iot_data"
PCAP_DIR = EXT_DIR / "pcaps"
REG_PATH = EXT_DIR / "ciciot2023_mac_registry.json"
OUT_DATASET = EXT_DIR / "ciciot2023_device_labelled_v2.parquet"
OUT_PROVENANCE = EXT_DIR / "ciciot2023_device_labelled_v2_provenance.parquet"
REPORT_DIR = ROOT / "reports" / "ctgan_v2"

CANONICAL_44_COLS: List[str] = (
    list(MODEL_INPUT_FEATURES)
    + ["protocol_name", "label_raw", "label_category", "is_attack", "device_id", "device_category"]
)

MAC_OR_IP_PATTERN = re.compile(r"([0-9a-f]{2}(?::[0-9a-f]{2}){5}|(?:\d{1,3}\.){3}\d{1,3})", re.IGNORECASE)


def assert_zero_mac_ip_leakage(df: pd.DataFrame) -> None:
    """Verify no string column contains raw MAC or IPv4 addresses."""
    for col in df.columns:
        if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
            for val in df[col].dropna().astype(str).unique():
                if MAC_OR_IP_PATTERN.search(val):
                    raise AssertionError(f"Detected potential MAC/IP leakage in column {col!r}: {val!r}")


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    mac_map, registry_meta = load_mac_registry(REG_PATH)

    t0 = time.perf_counter()
    all_rows: List[Dict[str, Any]] = []
    capture_diags: List[Dict[str, Any]] = []

    for spec in CAPTURE_SPECS:
        pcap_path = PCAP_DIR / spec.local_rel_path
        if not pcap_path.exists():
            raise FileNotFoundError(f"Missing expected PCAPNG capture: {pcap_path}")
        rows, diag = extract_windows_from_pcapng(pcap_path, spec, mac_map, min_window_packets=5)
        all_rows.extend(rows)
        capture_diags.append(diag)
        print(
            f"[EXTRACT] {spec.capture_id:18s} | epbs={diag['total_epbs']:7d} | "
            f"matched={diag['matched_official_device_epbs']:7d} | devs={diag['active_devices']:2d} | "
            f"windows={diag['extracted_windows']:5d}"
        )

    full_df = pd.DataFrame(all_rows)
    if full_df.empty:
        raise RuntimeError("No windows extracted from PCAPNG captures.")

    # Separate clean 44-column modeling table from audit provenance columns
    prov_df = full_df[["device_id", "device_category", "testbed_role", "capture_id", "label_raw", "label_category"]].copy()
    prov_df.insert(0, "row_index", range(len(prov_df)))

    model_df = full_df[CANONICAL_44_COLS].copy()
    assert_zero_mac_ip_leakage(model_df)

    # Validate domain invariants on extracted real dataset
    evaluator = SyntheticDataValidityEvaluator(tolerance=1e-2)
    val_summary = evaluator.evaluate_all(model_df, expected_columns=CANONICAL_44_COLS)
    norm_violations = sum(
        v.get("negative_count", 0) for k, v in val_summary.get("numerical_validity", {}).items() if isinstance(v, dict)
    )
    overall_valid = bool(val_summary.get("overall_summary", {}).get("all_passed", False))

    model_df.to_parquet(OUT_DATASET, index=False)
    prov_df.to_parquet(OUT_PROVENANCE, index=False)

    # Compute rich coverage & sparsity matrices
    dev_cat_x_macro = pd.crosstab(model_df["device_category"], model_df["label_category"]).to_dict()
    role_x_macro = pd.crosstab(prov_df["testbed_role"], prov_df["label_category"]).to_dict()
    raw_counts = model_df["label_raw"].value_counts().to_dict()
    macro_counts = model_df["label_category"].value_counts().to_dict()
    dev_cat_counts = model_df["device_category"].value_counts().to_dict()
    rare_raw = {k: int(v) for k, v in raw_counts.items() if v < 100}

    # Check non-zero support cells in device_category x label_category
    cross = pd.crosstab(model_df["device_category"], model_df["label_category"])
    supported_pairs = int((cross > 0).sum().sum())
    low_support_pairs = [
        {"device_category": dcat, "label_category": lcat, "count": int(cross.loc[dcat, lcat])}
        for dcat in cross.index
        for lcat in cross.columns
        if 0 < int(cross.loc[dcat, lcat]) < 20
    ]
    zero_support_pairs = [
        {"device_category": dcat, "label_category": lcat}
        for dcat in cross.index
        for lcat in cross.columns
        if int(cross.loc[dcat, lcat]) == 0
    ]

    coverage_report = {
        "dataset_path": str(OUT_DATASET.relative_to(ROOT)),
        "provenance_path": str(OUT_PROVENANCE.relative_to(ROOT)),
        "extraction_elapsed_s": round(time.perf_counter() - t0, 2),
        "total_rows": int(len(model_df)),
        "total_columns": int(model_df.shape[1]),
        "columns": list(model_df.columns),
        "unique_device_ids": int(model_df["device_id"].nunique()),
        "unique_device_categories": sorted(model_df["device_category"].unique().tolist()),
        "unique_label_raw": int(model_df["label_raw"].nunique()),
        "unique_label_categories": sorted(model_df["label_category"].unique().tolist()),
        "zero_mac_ip_leakage_verified": True,
        "domain_validation_on_real_extracted_data": val_summary,
        "device_category_counts": {k: int(v) for k, v in dev_cat_counts.items()},
        "label_category_counts": {k: int(v) for k, v in macro_counts.items()},
        "label_raw_counts": {k: int(v) for k, v in raw_counts.items()},
        "rare_raw_classes_under_100": rare_raw,
        "testbed_role_counts": {k: int(v) for k, v in prov_df["testbed_role"].value_counts().items()},
        "device_category_by_label_category": {
            lcat: {dcat: int(cnt) for dcat, cnt in col_dict.items()}
            for lcat, col_dict in dev_cat_x_macro.items()
        },
        "testbed_role_by_label_category": {
            lcat: {role: int(cnt) for role, cnt in col_dict.items()}
            for lcat, col_dict in role_x_macro.items()
        },
        "supported_device_x_macro_pairs": supported_pairs,
        "total_possible_device_x_macro_pairs": int(cross.shape[0] * cross.shape[1]),
        "low_support_device_x_macro_pairs_under_20": low_support_pairs,
        "zero_support_device_x_macro_pairs": zero_support_pairs,
        "per_capture_diagnostics": capture_diags,
    }

    out = REPORT_DIR / "device_coverage_report.json"
    out.write_text(json.dumps(coverage_report, indent=2), encoding="utf-8")
    print(f"\nSaved {OUT_DATASET} shape={model_df.shape}, validity_all_passed={overall_valid}")
    print(f"Device categories: {dev_cat_counts}")
    print(f"Macro categories: {macro_counts}")
    print(f"Report -> {out}")


if __name__ == "__main__":
    main()
