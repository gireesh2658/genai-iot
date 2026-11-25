"""
IoTSynth AI - Generated Dataset Repository Service
Handles listing, inspecting, previewing, deleting, and downloading CTGAN datasets.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set
import pandas as pd

from backend.config import Settings
from backend.exceptions import BadRequestError, ResourceNotFoundError
from backend.schemas.datasets import (
    DatasetDetailResponse,
    DatasetListResponse,
    DatasetSummaryItem,
)

SAFE_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")
PROTECTED_DATASETS: Set[str] = {
    "ctgan_initial_sample_v1",
    "ctgan_initial_sample_v1_domain_corrected",
}


class DatasetService:
    """Service layer managing generated synthetic IoT datasets under datasets/generated/."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.settings.DATASETS_GENERATED_DIR.mkdir(parents=True, exist_ok=True)

    def _is_contained_path(self, candidate: Path) -> bool:
        try:
            resolved_candidate = candidate.resolve()
            for base_dir in self.settings.iter_generated_search_dirs():
                resolved_base = base_dir.resolve()
                if resolved_candidate != resolved_base and resolved_candidate.is_relative_to(resolved_base):
                    return True
            return False
        except Exception:
            return False

    def _read_sidecar_meta(self, dataset_id: str, gen_dir: Optional[Path] = None) -> Optional[Dict[str, Any]]:
        search_dirs = [gen_dir] if gen_dir is not None else self.settings.iter_generated_search_dirs()
        for d in search_dirs:
            meta_path = d / f"{dataset_id}_metadata.json"
            if meta_path.exists():
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    return None
        return None

    def list_datasets(self) -> DatasetListResponse:
        grouped: Dict[str, Dict[str, Any]] = {}
        # Scan bundled baseline directory first, then active generated dir so writable overrides take precedence.
        for gen_dir in reversed(self.settings.iter_generated_search_dirs()):
            if not gen_dir.exists():
                continue
            for fp in sorted(gen_dir.glob("*")):
                if not fp.is_file() or fp.suffix.lower() not in (".parquet", ".csv"):
                    continue
                stem = fp.stem
                if not SAFE_ID_REGEX.match(stem):
                    continue
                fmt = fp.suffix.lower().lstrip(".")
                mtime = fp.stat().st_mtime
                entry = grouped.setdefault(
                    stem,
                    {
                        "formats": [],
                        "primary": fp,
                        "dir": gen_dir,
                        "size_bytes": 0,
                        "mtime": mtime,
                    },
                )
                if fmt not in entry["formats"]:
                    entry["formats"].append(fmt)
                if fmt == "parquet" or entry["primary"].suffix.lower() != ".parquet":
                    entry["primary"] = fp
                    entry["dir"] = gen_dir
                    entry["size_bytes"] = fp.stat().st_size
                entry["mtime"] = max(entry["mtime"], mtime)

        if not grouped:
            return DatasetListResponse(total_datasets=0, datasets=[])

        items: List[DatasetSummaryItem] = []
        for stem, info in sorted(grouped.items(), key=lambda kv: kv[1]["mtime"], reverse=True):
            meta = self._read_sidecar_meta(stem, info["dir"])
            num_rows = meta.get("num_records") or meta.get("sample_size") if meta else None
            num_cols = meta.get("columns_count") or meta.get("num_columns") if meta else None
            if (num_rows is None or num_cols is None) and info["primary"].suffix.lower() == ".parquet":
                try:
                    import pyarrow.parquet as pq
                    pq_meta = pq.read_metadata(info["primary"])
                    num_rows = pq_meta.num_rows
                    num_cols = pq_meta.num_columns
                except Exception:
                    pass

            items.append(
                DatasetSummaryItem(
                    dataset_id=stem,
                    filename=info["primary"].name,
                    format=info["primary"].suffix.lower().lstrip("."),
                    available_formats=sorted(info["formats"]),
                    size_bytes=info["size_bytes"],
                    created_at=datetime.fromtimestamp(info["mtime"], tz=timezone.utc).isoformat(),
                    has_metadata=meta is not None,
                    is_protected=stem in PROTECTED_DATASETS,
                    num_records=num_rows,
                    num_columns=num_cols,
                )
            )

        return DatasetListResponse(total_datasets=len(items), datasets=items)

    def get_dataset_detail(self, dataset_id: str, preview_limit: int = 40) -> DatasetDetailResponse:
        clean_id = dataset_id.strip()
        if not SAFE_ID_REGEX.match(clean_id):
            raise BadRequestError(f"Invalid dataset_id '{dataset_id}'.")

        pq_file: Optional[Path] = None
        csv_file: Optional[Path] = None
        matched_dir: Optional[Path] = None
        for gen_dir in self.settings.iter_generated_search_dirs():
            cand_pq = gen_dir / f"{clean_id}.parquet"
            cand_csv = gen_dir / f"{clean_id}.csv"
            if cand_pq.exists() or cand_csv.exists():
                pq_file = cand_pq
                csv_file = cand_csv
                matched_dir = gen_dir
                break

        if matched_dir is None or pq_file is None or csv_file is None:
            raise ResourceNotFoundError("Generated dataset", clean_id)

        available_formats: List[str] = []
        files_info: Dict[str, Dict[str, Any]] = {}
        primary_filename = ""
        columns: List[str] = []
        num_records: Optional[int] = None
        preview_records: List[Dict[str, Any]] = []

        if pq_file.exists():
            available_formats.append("parquet")
            primary_filename = pq_file.name
            files_info["parquet"] = {"filename": pq_file.name, "size_bytes": pq_file.stat().st_size}
            df = pd.read_parquet(pq_file)
            num_records = len(df)
            columns = list(df.columns)
            preview_records = df.head(preview_limit).to_dict(orient="records")

        if csv_file.exists():
            available_formats.append("csv")
            if not primary_filename:
                primary_filename = csv_file.name
            files_info["csv"] = {"filename": csv_file.name, "size_bytes": csv_file.stat().st_size}
            if num_records is None:
                df = pd.read_csv(csv_file)
                num_records = len(df)
                columns = list(df.columns)
                preview_records = df.head(preview_limit).to_dict(orient="records")

        return DatasetDetailResponse(
            dataset_id=clean_id,
            primary_filename=primary_filename,
            available_formats=available_formats,
            num_records=num_records,
            num_columns=len(columns) if columns else None,
            columns=columns,
            files=files_info,
            metadata=self._read_sidecar_meta(clean_id),
            preview_records=preview_records,
        )

    def get_dataset_file_path(self, dataset_id: str, file_format: str) -> Path:
        clean_id = dataset_id.strip()
        if not SAFE_ID_REGEX.match(clean_id):
            raise BadRequestError(f"Invalid dataset_id '{dataset_id}'.")

        clean_fmt = file_format.strip().lower()
        if clean_fmt not in ("csv", "parquet"):
            raise BadRequestError(f"Unsupported format '{file_format}'. Use 'csv' or 'parquet'.")

        target_file = (self.settings.DATASETS_GENERATED_DIR.resolve() / f"{clean_id}.{clean_fmt}").resolve()
        if target_file.exists() and target_file.is_file() and self._is_contained_path(target_file):
            return target_file

        for search_dir in self.settings.iter_generated_search_dirs():
            candidate = (search_dir.resolve() / f"{clean_id}.{clean_fmt}").resolve()
            if self._is_contained_path(candidate) and candidate.exists() and candidate.is_file():
                return candidate

        # Convert transparently between Parquet and CSV into writable DATASETS_GENERATED_DIR if sibling exists
        sibling_ext = "parquet" if clean_fmt == "csv" else "csv"
        for search_dir in self.settings.iter_generated_search_dirs():
            sibling_file = (search_dir.resolve() / f"{clean_id}.{sibling_ext}").resolve()
            if sibling_file.exists() and sibling_file.is_file() and self._is_contained_path(sibling_file):
                self.settings.DATASETS_GENERATED_DIR.mkdir(parents=True, exist_ok=True)
                target_file = (self.settings.DATASETS_GENERATED_DIR.resolve() / f"{clean_id}.{clean_fmt}").resolve()
                if not self._is_contained_path(target_file):
                    raise BadRequestError("Invalid dataset file path.")
                df = pd.read_parquet(sibling_file) if sibling_ext == "parquet" else pd.read_csv(sibling_file)
                if clean_fmt == "csv":
                    df.to_csv(target_file, index=False)
                else:
                    df.to_parquet(target_file, index=False, engine="pyarrow")
                return target_file

        raise ResourceNotFoundError("Dataset file", f"{clean_id}.{clean_fmt}")

    def delete_dataset(self, dataset_id: str) -> Dict[str, str]:
        clean_id = dataset_id.strip()
        if not SAFE_ID_REGEX.match(clean_id):
            raise BadRequestError(f"Invalid dataset_id '{dataset_id}'.")
        if clean_id in PROTECTED_DATASETS:
            raise BadRequestError(f"Baseline dataset '{clean_id}' is protected and cannot be deleted.")

        gen_dir = self.settings.DATASETS_GENERATED_DIR
        candidates = [
            gen_dir / f"{clean_id}.parquet",
            gen_dir / f"{clean_id}.csv",
            gen_dir / f"{clean_id}_metadata.json",
        ]
        found = False
        for fp in candidates:
            if fp.exists() and fp.is_file():
                fp.unlink()
                found = True
        if not found:
            raise ResourceNotFoundError("Generated dataset", clean_id)
        return {"status": "deleted", "dataset_id": clean_id}
