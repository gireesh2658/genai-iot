"""
Acquire real CICIoT2023 PCAPNG captures (or block-aligned prefix slices) and write
complete provenance + Dataset Selection Decision Matrix reports.
"""

from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict

import httpx

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from synthetic_engine.ciciot2023_capture_catalog import CAPTURE_SPECS, HF_BASE_URL
from synthetic_engine.pcap_device_extractor import (
    CaptureSpec,
    sha256_file,
    trim_to_pcapng_block_boundary,
)


PCAP_DIR = ROOT / "datasets" / "external" / "device_labelled_iot_data" / "pcaps"
REPORT_DIR = ROOT / "reports" / "ctgan_v2"


def download_capture(spec: CaptureSpec) -> Dict[str, Any]:
    dest = PCAP_DIR / spec.local_rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"{HF_BASE_URL}/{spec.rel_url_path}"

    # Skip re-download if valid cached file matches expected minimum bound
    if dest.exists() and dest.stat().st_size > 100_000:
        size = dest.stat().st_size
        if spec.max_download_bytes is None or size >= int(spec.max_download_bytes * 0.9):
            return {
                "capture_id": spec.capture_id,
                "url": url,
                "local_path": str(dest.relative_to(ROOT)),
                "label_raw": spec.label_raw,
                "label_category": spec.label_category,
                "requested_bytes": spec.max_download_bytes,
                "block_aligned_bytes": size,
                "is_complete_file": spec.max_download_bytes is None,
                "sha256": sha256_file(dest),
                "status": "cached",
            }

    headers = {"User-Agent": "IoTSynthAI-DataAcquisition/2.0"}
    if spec.max_download_bytes is not None:
        headers["Range"] = f"bytes=0-{spec.max_download_bytes - 1}"

    last_err = None
    for attempt in range(4):
        try:
            with httpx.Client(follow_redirects=True, timeout=180.0) as client:
                resp = client.get(url, headers=headers)
                resp.raise_for_status()
                raw = resp.content
                aligned = trim_to_pcapng_block_boundary(raw)
                dest.write_bytes(aligned)
                return {
                    "capture_id": spec.capture_id,
                    "url": url,
                    "local_path": str(dest.relative_to(ROOT)),
                    "label_raw": spec.label_raw,
                    "label_category": spec.label_category,
                    "requested_bytes": spec.max_download_bytes,
                    "raw_downloaded_bytes": len(raw),
                    "block_aligned_bytes": len(aligned),
                    "is_complete_file": spec.max_download_bytes is None,
                    "sha256": sha256_file(dest),
                    "status": "downloaded",
                }
        except Exception as exc:
            last_err = exc
            time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"Failed acquiring {url}: {last_err}")


def main() -> None:
    PCAP_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {pool.submit(download_capture, spec): spec for spec in CAPTURE_SPECS}
        for fut in as_completed(futs):
            res = fut.result()
            results.append(res)
            print(
                f"[{res['status']:10s}] {res['capture_id']:18s} | {res['label_raw']:26s} | "
                f"{res['block_aligned_bytes']/1e6:6.2f} MB | complete={res['is_complete_file']}"
            )

    results.sort(key=lambda r: r["capture_id"])
    total_mb = sum(r["block_aligned_bytes"] for r in results) / 1e6

    provenance_report = {
        "selected_primary_dataset": "CICIoT2023 PCAPNG Captures (somnath0100/CICIoT2023Small) + Official PMC10346235 Table 1 MAC Registry",
        "acquisition_elapsed_s": round(time.perf_counter() - t0, 2),
        "total_captures": len(results),
        "total_bytes": sum(r["block_aligned_bytes"] for r in results),
        "total_mb": round(total_mb, 2),
        "dataset_selection_decision_matrix": [
            {
                "candidate": "Existing ciciot2023_preprocessed_sample.parquet",
                "verdict": "Retained for v1 baseline only (cannot support v2 device-aware learning)",
                "real_device_ids": False,
                "real_attack_labels": True,
                "attack_categories": 8,
                "schema_compatibility": "43 columns (38 canonical features + 5 label/protocol cols; zero MAC/IP/timestamp fields)",
                "reason": "Anonymized aggregated CSV lacks timestamps, MACs, IPs, and device identifiers; cannot back-map to PCAPs or hardware devices.",
            },
            {
                "candidate": "CICIoT2023 PCAPNGs (somnath0100/CICIoT2023Small) + PMC10346235 Table 1 MACs",
                "verdict": "SELECTED PRIMARY FOR CTGAN V2",
                "real_device_ids": True,
                "real_attack_labels": True,
                "attack_categories": 8,
                "schema_compatibility": "Exact 44 canonical columns reconstructed natively from L2/L3/L4 headers + orig_len + PCAPNG timestamps",
                "reason": (
                    "Preserves true Ethernet source/destination MACs mapping to 70 verified physical devices across 7 hardware categories "
                    "(Audio, Camera, Home Automation, Hub, Lighting, Power Outlet, NextGen) covering Benign + 32 real attack types. "
                    "Verified DHCP IP reassignment confirms Ethernet L2 MAC is required instead of IP."
                ),
            },
            {
                "candidate": "UNSW-IoTraffic (16-09-23 packet CSV + Dryad flows)",
                "verdict": "REJECTED AS PRIMARY (Benign-only reference)",
                "real_device_ids": True,
                "real_attack_labels": False,
                "attack_categories": 1,
                "schema_compatibility": "10 packet columns only (Packet ID, TIME, Size, eth.src, eth.dst, IP.src, IP.dst, IP.proto, port.src, port.dst); 802,581 rows checked",
                "reason": "Zero cyberattack traffic or anomaly labels; cannot train attack-conditioned CTGAN or evaluate TSTR anomaly detection.",
            },
            {
                "candidate": "IoT-23 (Zenodo 4743746)",
                "verdict": "NOT SELECTED",
                "real_device_ids": False,
                "real_attack_labels": True,
                "attack_categories": 1,
                "schema_compatibility": "20.5 GB monolithic tarball of Zeek conn.log flows; mainly Linux malware sandboxes + 3 real IoT devices",
                "reason": "Poor IoT hardware diversity (only 3 consumer devices) and incompatible Zeek schema compared with CICIoT2023 44-col schema.",
            },
        ],
        "ground_truth_and_attribution_methodology": {
            "mac_source": "Neto et al. (2023), Sensors 23(13):5941 (PMC10346235 Table 1 & Section 3)",
            "pseudonymization": "Every raw MAC mapped 1-to-1 to stable device_001..device_070; ZERO raw MAC or IP strings emitted to processed or synthetic tables.",
            "excluded_macs": ["3c:18:a0:41:c3:a0 (gateway router)", "56:4f:8a:e1:f3:2d (local testbed bridge/LAA)", "broadcast/multicast"],
            "disjoint_packet_ownership": "Each Ethernet frame is assigned to at most one verified device (preferring victim IoT hardware over attacking RPi when both appear on local L2) so no packet spans train and test splits.",
            "ground_truth_caveat": "CICIoT2023 attack labels are capture-session level ground truth (ambient background IoT traffic may coexist inside attack capture sessions; attacker vs victim role provenance is tracked separately).",
        },
        "captures": results,
    }

    out = REPORT_DIR / "dataset_provenance_report.json"
    out.write_text(json.dumps(provenance_report, indent=2), encoding="utf-8")
    print(f"\nCompleted {len(results)} captures ({total_mb:.2f} MB) -> {out}")


if __name__ == "__main__":
    main()
