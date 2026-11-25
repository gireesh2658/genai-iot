"""
IoTSynth AI - CTGAN Generative Service
Handles dynamic model discovery, custom CPU CTGAN fitting, conditional rare-attack
generation, device-diverse IoT telemetry calibration, domain integrity repair, and export.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import threading
import time
from typing import Any, Dict, List, Optional, Set
import numpy as np
import pandas as pd

from backend.config import Settings, get_settings
from backend.exceptions import BadRequestError, ResourceNotFoundError
from backend.schemas.ctgan import (
    AttackProfileSummaryItem,
    CTGANGenerateRequest,
    CTGANGenerateResponse,
    CTGANModelDetailResponse,
    CTGANModelListResponse,
    CTGANModelSummary,
    CTGANTrainRequest,
    CTGANTrainResponse,
    IoTDeviceProfileItem,
    V2DeviceCatalogResponse,
    V2DeviceItem,
)
from simulator.attack_profiles import ATTACK_PROFILES, list_attack_profiles
from simulator.device_profiles import PREDEFINED_PROFILES
from simulator.traffic_constraints import KNOWN_PROTOCOL_MAP
from simulator.traffic_schema import CANONICAL_SCHEMA_COLUMNS
from synthetic_engine.ctgan_config import CTGANConfig
from synthetic_engine.ctgan_data_pipeline import CTGANDataPipeline, CTGANDataPipelineConfig
from synthetic_engine.ctgan_model import CTGANModel
from synthetic_engine.evaluation.validity import (
    AUTHORITATIVE_IS_ATTACK_MAP,
    AUTHORITATIVE_LABEL_MAP,
)

SAFE_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")
CORE_PROTECTED_MODELS: Set[str] = {"ctgan_full_v1", "ctgan_device_aware_v2"}
VALID_CATEGORIES: Set[str] = {
    "DDoS",
    "DoS",
    "Mirai",
    "Benign",
    "Reconnaissance",
    "Spoofing",
    "Web-based",
    "Brute Force",
}


class CTGANService:
    """Service layer managing CTGAN checkpoints, live neural training, device calibration, and generation."""

    CATEGORY_DEFAULT_RAW: Dict[str, str] = {
        "Benign": "BENIGN",
        "Brute Force": "DICTIONARYBRUTEFORCE",
        "DDoS": "DDOS-ICMP_FLOOD",
        "DoS": "DOS-UDP_FLOOD",
        "Mirai": "MIRAI-GREETH_FLOOD",
        "Reconnaissance": "VULNERABILITYSCAN",
        "Spoofing": "MITM-ARPSPOOFING",
        "Web-based": "COMMANDINJECTION",
    }

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._model_cache: Dict[str, CTGANModel] = {}
        self._v2_catalog_cache: Optional[Dict[str, Any]] = None
        self._lock = threading.Lock()

    def _discover_model_ids(self) -> List[str]:
        """Discover all fitted CTGAN models cleanly across v2/, v1/, custom/, and legacy dirs."""
        return [
            mid
            for mid in CTGANModel.discover_model_ids(self.settings.CTGAN_MODELS_DIR)
            if SAFE_ID_REGEX.match(mid)
        ]

    def _get_v2_registry_data(self) -> Dict[str, Any]:
        """Load pseudonymized V2 device catalog and empirical class support (zero MAC/IP exposure)."""
        if self._v2_catalog_cache is not None:
            return self._v2_catalog_cache

        with self._lock:
            if self._v2_catalog_cache is not None:
                return self._v2_catalog_cache

            static_catalog_path = (
                self.settings.CTGAN_MODELS_DIR / "v2" / "ctgan_device_aware_v2_device_catalog.json"
            )
            if static_catalog_path.exists():
                try:
                    raw_cat = json.loads(static_catalog_path.read_text(encoding="utf-8"))
                    devices_by_id: Dict[str, Dict[str, Any]] = {}
                    category_set: Set[str] = {
                        str(c) for c in raw_cat.get("device_categories", []) if str(c).strip()
                    }
                    for entry in raw_cat.get("devices", []):
                        dev_id = str(entry.get("device_id", "")).strip()
                        dev_cat = str(entry.get("device_category", "")).strip()
                        if not dev_id or not dev_cat:
                            continue
                        category_set.add(dev_cat)
                        devices_by_id[dev_id] = {
                            "device_id": dev_id,
                            "device_name": str(entry.get("device_name", dev_id)),
                            "device_category": dev_cat,
                            "testbed_role": str(entry.get("testbed_role", "victim")),
                            "train_row_count": int(entry.get("train_row_count", 0)),
                            "supported_label_categories": [
                                str(c) for c in entry.get("supported_label_categories", [])
                            ],
                        }

                    pair_support: Dict[tuple[str, str], int] = {}
                    for k, v in raw_cat.get("pair_support", {}).items():
                        if "|" in str(k):
                            dev_k, cat_k = str(k).split("|", 1)
                            pair_support[(dev_k, cat_k)] = int(v)

                    cat_pair_support: Dict[tuple[str, str], int] = {}
                    for k, v in raw_cat.get("cat_pair_support", {}).items():
                        if "|" in str(k):
                            dcat_k, lcat_k = str(k).split("|", 1)
                            cat_pair_support[(dcat_k, lcat_k)] = int(v)

                    self._v2_catalog_cache = {
                        "device_categories": sorted(category_set),
                        "traffic_categories": sorted(VALID_CATEGORIES),
                        "devices_by_id": devices_by_id,
                        "pair_support": pair_support,
                        "cat_pair_support": cat_pair_support,
                    }
                    return self._v2_catalog_cache
                except Exception:
                    pass

            ext_dir = self.settings.DATASETS_DIR / "external" / "device_labelled_iot_data"
            reg_path = ext_dir / "ciciot2023_mac_registry.json"
            train_path = ext_dir / "splits" / "train.parquet"

            devices_by_id = {}
            category_set = set()

            if reg_path.exists():
                try:
                    raw_reg = json.loads(reg_path.read_text(encoding="utf-8"))
                    for entry in raw_reg.get("devices", []):
                        dev_id = str(entry.get("device_id", "")).strip()
                        dev_cat = str(entry.get("official_category", "")).strip()
                        if not dev_id or not dev_cat:
                            continue
                        category_set.add(dev_cat)
                        devices_by_id[dev_id] = {
                            "device_id": dev_id,
                            "device_name": str(entry.get("device_name", dev_id)),
                            "device_category": dev_cat,
                            "testbed_role": str(entry.get("testbed_role", "victim")),
                            "train_row_count": 0,
                            "supported_label_categories": [],
                        }
                except Exception:
                    pass

            pair_support = {}
            cat_pair_support = {}

            if train_path.exists():
                try:
                    tdf = pd.read_parquet(
                        train_path,
                        columns=["device_id", "device_category", "label_category"],
                    )
                    dev_totals = tdf["device_id"].astype(str).value_counts().to_dict()
                    dev_lcat = pd.crosstab(tdf["device_id"].astype(str), tdf["label_category"].astype(str))
                    dcat_lcat = pd.crosstab(tdf["device_category"].astype(str), tdf["label_category"].astype(str))

                    for d_cat in dcat_lcat.index:
                        category_set.add(str(d_cat))
                        for l_cat in dcat_lcat.columns:
                            cat_pair_support[(str(d_cat), str(l_cat))] = int(dcat_lcat.loc[d_cat, l_cat])

                    for d_id in dev_lcat.index:
                        supported_lcats = sorted(
                            str(l_cat)
                            for l_cat in dev_lcat.columns
                            if int(dev_lcat.loc[d_id, l_cat]) > 0
                        )
                        for l_cat in supported_lcats:
                            pair_support[(str(d_id), l_cat)] = int(dev_lcat.loc[d_id, l_cat])
                        if d_id in devices_by_id:
                            devices_by_id[d_id]["train_row_count"] = int(dev_totals.get(d_id, 0))
                            devices_by_id[d_id]["supported_label_categories"] = supported_lcats
                except Exception:
                    pass

            self._v2_catalog_cache = {
                "device_categories": sorted(category_set),
                "traffic_categories": sorted(VALID_CATEGORIES),
                "devices_by_id": devices_by_id,
                "pair_support": pair_support,
                "cat_pair_support": cat_pair_support,
            }
            return self._v2_catalog_cache

    def list_v2_devices(self) -> V2DeviceCatalogResponse:
        """Return pseudonymized V2 device categories and 70 device IDs without raw MAC/IP fields."""
        data = self._get_v2_registry_data()
        items = [
            V2DeviceItem(**data["devices_by_id"][dev_id])
            for dev_id in sorted(data["devices_by_id"].keys())
        ]
        return V2DeviceCatalogResponse(
            total_devices=len(items),
            device_categories=list(data["device_categories"]),
            traffic_categories=list(data["traffic_categories"]),
            devices=items,
        )

    def list_device_profiles(self) -> List[IoTDeviceProfileItem]:
        """Return all 6 empirical IoT device profiles."""
        return [
            IoTDeviceProfileItem(
                profile_name=p.profile_name,
                device_category=p.device_category,
                default_protocols=list(p.default_protocols),
                packet_size_min=p.packet_size_min,
                packet_size_max=p.packet_size_max,
                communication_interval=p.communication_interval,
                traffic_rate_min=p.traffic_rate_min,
                traffic_rate_max=p.traffic_rate_max,
                behavior_type=p.behavior_type,
                description=p.description,
            )
            for p in PREDEFINED_PROFILES.values()
        ]

    def list_attack_profiles(self) -> List[AttackProfileSummaryItem]:
        """Return the catalog of 33 IoT cyberattack signatures across 7 attack families."""
        return [
            AttackProfileSummaryItem(
                attack_id=p.attack_id,
                label_raw=p.label_raw,
                label_category=p.label_category,
                protocol_name=p.protocol_name,
                protocol_type=p.protocol_type,
                packet_size_min=p.packet_size_min,
                packet_size_max=p.packet_size_max,
                rate_min=p.rate_min,
                rate_max=p.rate_max,
            )
            for p in list_attack_profiles()
        ]

    def list_models(self) -> CTGANModelListResponse:
        root_dir = self.settings.CTGAN_MODELS_DIR
        summaries: List[CTGANModelSummary] = []

        for model_id in self._discover_model_ids():
            config_path, meta_path, weights_path = CTGANModel.resolve_artifact_paths(
                root_dir, model_id, for_write=False
            )

            epochs, batch_size, device = 0, 500, "cpu"
            is_fitted, training_rows, elapsed_sec, created_at = False, None, None, None
            feat_count, disc_count, cond_dim = None, None, None
            trained_device = None

            if config_path.exists():
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    epochs = cfg.get("epochs", 0)
                    batch_size = cfg.get("batch_size", 500)
                    device = "cuda" if cfg.get("cuda", False) else "cpu"
                except Exception:
                    pass

            if meta_path.exists():
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    is_fitted = meta.get("is_fitted", False)
                    created_at = meta.get("saved_at")
                    feat_cols = meta.get("feature_columns", [])
                    disc_cols = meta.get("discrete_columns", [])
                    feat_count = len(feat_cols) if feat_cols else None
                    disc_count = len(disc_cols) if disc_cols else None
                    train_meta = meta.get("training_metadata", {})
                    training_rows = train_meta.get("num_rows") or train_meta.get("train_rows")
                    elapsed_sec = train_meta.get("elapsed_seconds")
                    cond_dim = train_meta.get("actual_dim_cond_vec")
                    if cond_dim is None and model_id == "ctgan_full_v1":
                        cond_dim = 992
                    trained_device = train_meta.get("trained_device") or ("CPU" if device == "cpu" else "CUDA")
                except Exception:
                    pass

            serving_device = "cpu"
            if model_id in self._model_cache:
                cached = self._model_cache[model_id]
                raw_dev = getattr(getattr(cached.synthesizer, "_model", None), "_device", None)
                if raw_dev is not None and "cuda" in str(raw_dev).lower():
                    serving_device = "cuda"

            role = "primary" if model_id == "ctgan_device_aware_v2" else ("baseline" if model_id == "ctgan_full_v1" else "custom")
            summaries.append(
                CTGANModelSummary(
                    model_id=model_id,
                    model_type="CTGAN",
                    role=role,
                    is_primary=(model_id == "ctgan_device_aware_v2"),
                    is_fitted=is_fitted,
                    is_loaded=model_id in self._model_cache,
                    is_custom=model_id not in CORE_PROTECTED_MODELS,
                    epochs=epochs,
                    batch_size=batch_size,
                    training_rows=training_rows,
                    feature_columns_count=feat_count,
                    discrete_columns_count=disc_count,
                    cond_vector_dim=cond_dim,
                    training_duration_sec=elapsed_sec,
                    artifact_availability={
                        "config": config_path.exists(),
                        "metadata": meta_path.exists(),
                        "weights": weights_path.exists(),
                    },
                    device=device,
                    trained_device=trained_device,
                    serving_device=serving_device,
                    created_at=created_at,
                )
            )

        return CTGANModelListResponse(total_models=len(summaries), models=summaries)

    def get_model_detail(self, model_id: str) -> CTGANModelDetailResponse:
        if not SAFE_ID_REGEX.match(model_id) or model_id not in self._discover_model_ids():
            raise ResourceNotFoundError("CTGAN model", model_id)

        root_dir = self.settings.CTGAN_MODELS_DIR
        config_path, meta_path, weights_path = CTGANModel.resolve_artifact_paths(
            root_dir, model_id, for_write=False
        )

        config_data: Dict[str, Any] = {}
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)

        meta_data: Dict[str, Any] = {}
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                meta_data = json.load(f)

        feature_columns = meta_data.get("feature_columns", [])
        discrete_columns = meta_data.get("discrete_columns", [])

        return CTGANModelDetailResponse(
            model_id=model_id,
            model_type="CTGAN",
            is_fitted=meta_data.get("is_fitted", False),
            is_loaded=model_id in self._model_cache,
            feature_columns_count=len(feature_columns),
            feature_columns=feature_columns,
            discrete_columns_count=len(discrete_columns),
            discrete_columns=discrete_columns,
            config=config_data,
            training_metadata=meta_data.get("training_metadata", {}),
            artifact_availability={
                "config": config_path.exists(),
                "metadata": meta_path.exists(),
                "weights": weights_path.exists(),
            },
        )

    def get_or_load_model(self, model_id: str) -> CTGANModel:
        if not SAFE_ID_REGEX.match(model_id) or model_id not in self._discover_model_ids():
            raise ResourceNotFoundError("CTGAN model", model_id)

        if model_id in self._model_cache:
            return self._model_cache[model_id]

        with self._lock:
            if model_id in self._model_cache:
                return self._model_cache[model_id]
            try:
                loaded_model = CTGANModel.load(
                    directory=self.settings.CTGAN_MODELS_DIR,
                    model_name=model_id,
                )
            except Exception as e:
                raise BadRequestError(f"Failed to load CTGAN model '{model_id}': {str(e)}")
            self._model_cache[model_id] = loaded_model
            return loaded_model

    def train_model(self, request: CTGANTrainRequest) -> CTGANTrainResponse:
        """Fit a new CTGAN synthesizer on stratified real CICIoT2023 flows."""
        clean_id = request.model_id.strip()
        if not SAFE_ID_REGEX.match(clean_id):
            raise BadRequestError("model_id may only contain alphanumeric characters, underscores, and hyphens.")
        if clean_id in self._discover_model_ids():
            raise BadRequestError(f"CTGAN model '{clean_id}' already exists. Choose a different name.")
        if request.batch_size % 10 != 0:
            raise BadRequestError("batch_size must be divisible by pac=10 (e.g., 100, 200, 250, 500).")
        if request.sample_size < request.batch_size:
            raise BadRequestError("sample_size must be >= batch_size.")

        ref_parquet = self.settings.DATASETS_PROCESSED_DIR / "ciciot2023_preprocessed_sample.parquet"
        if not ref_parquet.exists():
            raise ResourceNotFoundError("Reference dataset", str(ref_parquet.name))

        raw_df = pd.read_parquet(ref_parquet)
        if "Label" in raw_df.columns:
            raw_df = raw_df.drop(columns=["Label"])
        if "device_id" not in raw_df.columns:
            raw_df["device_id"] = "ciciot2023_node"
        if "device_category" not in raw_df.columns:
            raw_df["device_category"] = "testbed_device"
        df_canon = raw_df[CANONICAL_SCHEMA_COLUMNS]

        prep_cfg = CTGANDataPipelineConfig(
            sample_size=request.sample_size,
            stratify_by="label_raw",
            train_ratio=0.80,
            val_ratio=0.20,
            random_seed=request.random_seed,
            exclude_metadata_cols=True,
        )
        prep = CTGANDataPipeline(config=prep_cfg).prepare_training_data(df_canon)
        train_df = prep["train_df"]
        discrete_columns = prep["discrete_columns"]

        # Adjust batch_size if 80% split produced fewer rows than batch_size
        eff_batch = min(request.batch_size, (len(train_df) // 10) * 10)
        eff_batch = max(10, eff_batch)

        cfg = CTGANConfig(
            epochs=request.epochs,
            batch_size=eff_batch,
            pac=10,
            generator_dim=(128, 128),
            discriminator_dim=(128, 128),
            cuda=False,
            random_seed=request.random_seed,
            verbose=False,
        )
        model = CTGANModel(config=cfg)
        t0 = time.perf_counter()
        model.fit(
            train_df=train_df,
            discrete_columns=discrete_columns,
            dataset_name="ciciot2023_preprocessed_sample",
            table_name="traffic",
        )
        elapsed = round(time.perf_counter() - t0, 2)
        model.training_metadata["wall_clock_elapsed_seconds"] = elapsed
        model.save(directory=self.settings.CTGAN_MODELS_DIR, model_name=clean_id, overwrite=False)

        with self._lock:
            self._model_cache[clean_id] = model

        loss_df = model.get_loss_history()
        init_g = final_g = init_d = final_d = None
        if loss_df is not None and not loss_df.empty:
            init_g = round(float(loss_df.iloc[0]["Generator Loss"]), 4)
            final_g = round(float(loss_df.iloc[-1]["Generator Loss"]), 4)
            init_d = round(float(loss_df.iloc[0]["Discriminator Loss"]), 4)
            final_d = round(float(loss_df.iloc[-1]["Discriminator Loss"]), 4)

        return CTGANTrainResponse(
            status="completed",
            model_id=clean_id,
            epochs=request.epochs,
            batch_size=eff_batch,
            training_rows=len(train_df),
            elapsed_seconds=elapsed,
            initial_generator_loss=init_g,
            final_generator_loss=final_g,
            initial_discriminator_loss=init_d,
            final_discriminator_loss=final_d,
        )

    def delete_model(self, model_id: str) -> Dict[str, str]:
        if model_id in CORE_PROTECTED_MODELS:
            raise BadRequestError(f"Primary pretrained checkpoint '{model_id}' is protected and cannot be deleted.")
        if not SAFE_ID_REGEX.match(model_id) or model_id not in self._discover_model_ids():
            raise ResourceNotFoundError("CTGAN model", model_id)
        with self._lock:
            self._model_cache.pop(model_id, None)
        root = self.settings.CTGAN_MODELS_DIR
        cfg_p, meta_p, pkl_p = CTGANModel.resolve_artifact_paths(root, model_id, for_write=False)
        for fp in (pkl_p, cfg_p, meta_p):
            if fp.exists():
                fp.unlink()
        if pkl_p.parent.parent.name == "custom" and pkl_p.parent.exists() and not any(pkl_p.parent.iterdir()):
            pkl_p.parent.rmdir()
        return {"status": "deleted", "model_id": model_id}

    @classmethod
    def _apply_domain_correction(
        cls,
        df: pd.DataFrame,
        target_category: Optional[str] = None,
    ) -> tuple[pd.DataFrame, Dict[str, int]]:
        """Reconcile label hierarchy, IANA protocol names, and Std = sqrt(Variance)."""
        corrected = df.copy()
        stats = {
            "category_mismatches_fixed": 0,
            "is_attack_violations_fixed": 0,
            "protocol_mismatches_fixed": 0,
            "dispersion_violations_fixed": 0,
        }

        if target_category is not None and target_category in cls.CATEGORY_DEFAULT_RAW:
            expected_is_atk = 0 if target_category == "Benign" else 1
            if "label_raw" in corrected.columns:
                mapped_cat = corrected["label_raw"].map(AUTHORITATIVE_LABEL_MAP)
                bad_raw_mask = mapped_cat != target_category
                stats["category_mismatches_fixed"] = int(bad_raw_mask.sum())
                corrected.loc[bad_raw_mask, "label_raw"] = cls.CATEGORY_DEFAULT_RAW[target_category]
            if "label_category" in corrected.columns:
                corrected["label_category"] = target_category
            if "is_attack" in corrected.columns:
                orig_atk = corrected["is_attack"].astype(int)
                diff_atk = orig_atk != expected_is_atk
                stats["is_attack_violations_fixed"] = int(diff_atk.sum())
                corrected["is_attack"] = expected_is_atk
        elif "label_raw" in corrected.columns:
            mapped_cat = corrected["label_raw"].map(AUTHORITATIVE_LABEL_MAP)
            if "label_category" in corrected.columns:
                valid_cat_mask = mapped_cat.notna()
                diff_cat = valid_cat_mask & (corrected["label_category"].astype(str) != mapped_cat.astype(str))
                stats["category_mismatches_fixed"] = int(diff_cat.sum())
                corrected.loc[valid_cat_mask, "label_category"] = mapped_cat.loc[valid_cat_mask]

            mapped_atk = corrected["label_raw"].map(AUTHORITATIVE_IS_ATTACK_MAP)
            if "is_attack" in corrected.columns:
                valid_atk_mask = mapped_atk.notna()
                diff_atk = valid_atk_mask & (corrected["is_attack"].astype(int) != mapped_atk.loc[valid_atk_mask].astype(int))
                stats["is_attack_violations_fixed"] = int(diff_atk.sum())
                corrected.loc[valid_atk_mask, "is_attack"] = mapped_atk.loc[valid_atk_mask].astype(int)

        if "Protocol Type" in corrected.columns and "protocol_name" in corrected.columns:
            proto_ints = pd.to_numeric(corrected["Protocol Type"], errors="coerce")
            mapped_proto = proto_ints.map(KNOWN_PROTOCOL_MAP)
            valid_proto_mask = mapped_proto.notna()
            diff_proto = valid_proto_mask & (corrected["protocol_name"].astype(str) != mapped_proto.astype(str))
            stats["protocol_mismatches_fixed"] = int(diff_proto.sum())
            corrected.loc[valid_proto_mask, "protocol_name"] = mapped_proto.loc[valid_proto_mask]

        if "Variance" in corrected.columns and "Std" in corrected.columns:
            expected_std = np.sqrt(np.maximum(pd.to_numeric(corrected["Variance"], errors="coerce").fillna(0.0), 0.0))
            orig_std = pd.to_numeric(corrected["Std"], errors="coerce").fillna(0.0)
            diff_std = np.abs(orig_std - expected_std) > 1e-4
            stats["dispersion_violations_fixed"] = int(diff_std.sum())
            corrected["Std"] = expected_std

        return corrected, stats

    @staticmethod
    def _apply_device_calibration(
        df: pd.DataFrame,
        profile_names: List[str],
        seed: int = 42,
    ) -> pd.DataFrame:
        """Attach target IoT device identities and calibrate benign sensor flow envelopes cleanly."""
        calibrated = df.reset_index(drop=True).copy()
        for col in ("Rate", "IAT", "Min", "Max", "AVG", "Std", "Variance", "Tot sum"):
            if col in calibrated.columns:
                calibrated[col] = pd.to_numeric(calibrated[col], errors="coerce").fillna(0.0).astype("float64")

        rng = np.random.default_rng(seed)
        profiles = [PREDEFINED_PROFILES[p] for p in profile_names]
        n = len(calibrated)

        assigned_profiles = [profiles[i % len(profiles)] for i in range(n)]
        rng.shuffle(assigned_profiles)

        device_ids = [f"{p.profile_name}_{1 + (idx % 3):02d}" for idx, p in enumerate(assigned_profiles)]
        device_cats = [p.device_category for p in assigned_profiles]

        # Calibrate benign flows smoothly to the selected IoT hardware profiles
        # while preserving attack dynamics for malicious flows.
        is_benign = (calibrated["is_attack"] == 0).to_numpy()
        for idx, prof in enumerate(assigned_profiles):
            if not is_benign[idx]:
                continue
            r_min, r_max = max(0.05, prof.traffic_rate_min), max(prof.traffic_rate_min + 0.1, prof.traffic_rate_max)
            raw_rate = float(calibrated.at[idx, "Rate"])
            if raw_rate < r_min or raw_rate > r_max:
                cal_rate = float(rng.uniform(r_min, r_max))
                calibrated.at[idx, "Rate"] = round(cal_rate, 4)
                calibrated.at[idx, "IAT"] = round(1.0 / max(cal_rate, 0.1), 6)

            p_min, p_max = float(prof.packet_size_min), float(prof.packet_size_max)
            cur_min = float(calibrated.at[idx, "Min"])
            cur_max = float(calibrated.at[idx, "Max"])
            cur_avg = float(calibrated.at[idx, "AVG"])
            clipped_bounds = cur_max > p_max or cur_min < p_min
            scaled_min = float(np.clip(cur_min, p_min, p_max))
            scaled_max = float(np.clip(cur_max, scaled_min, p_max))
            scaled_avg = float(np.clip(cur_avg, scaled_min, scaled_max))
            if clipped_bounds:
                num_pkts = max(1.0, float(calibrated.at[idx, "Number"]))
                calibrated.at[idx, "Min"] = round(scaled_min, 2)
                calibrated.at[idx, "Max"] = round(scaled_max, 2)
                calibrated.at[idx, "AVG"] = round(scaled_avg, 2)
                calibrated.at[idx, "Tot sum"] = round(scaled_avg * num_pkts, 2)

            if "Variance" in calibrated.columns and "Std" in calibrated.columns:
                max_pop_var = ((scaled_max - scaled_min) / 2.0) ** 2
                cur_var = max(0.0, float(calibrated.at[idx, "Variance"]))
                if clipped_bounds or cur_var > max_pop_var:
                    bounded_var = round(min(cur_var, max_pop_var), 4)
                    calibrated.at[idx, "Variance"] = bounded_var
                    calibrated.at[idx, "Std"] = round(float(np.sqrt(max(bounded_var, 0.0))), 6)

        # Ensure metadata columns appear cleanly in canonical schema positions
        if "device_id" not in calibrated.columns:
            calibrated.insert(0, "device_id", device_ids)
        else:
            calibrated["device_id"] = device_ids
        if "device_category" not in calibrated.columns:
            calibrated.insert(1, "device_category", device_cats)
        else:
            calibrated["device_category"] = device_cats

        ordered_cols = [c for c in CANONICAL_SCHEMA_COLUMNS if c in calibrated.columns]
        extra_cols = [c for c in calibrated.columns if c not in ordered_cols]
        return calibrated[ordered_cols + extra_cols]

    @classmethod
    def _sample_clean_category(
        cls,
        model: CTGANModel,
        category_str: str,
        qty: int,
        extra_conditions: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """Draw conditional CTGAN samples and prefer rows whose native label_raw aligns cleanly."""
        cond = dict(extra_conditions or {})
        cond["label_category"] = category_str
        # Omit redundant is_attack when pairing additional conditions (like device_category/device_id)
        # so SDV conditional sampling avoids extra rejection overhead; _apply_domain_correction fixes it.
        if extra_conditions:
            cond.pop("is_attack", None)
        else:
            cond["is_attack"] = 0 if category_str == "Benign" else 1
        oversample_n = min(qty * 2, qty + 150) if qty > 0 else 0
        cand_df = model.sample(num_rows=oversample_n, conditions=cond)
        if cand_df.empty or "label_raw" not in cand_df.columns:
            return cand_df.head(qty).reset_index(drop=True)
        mapped_cat = cand_df["label_raw"].map(AUTHORITATIVE_LABEL_MAP)
        native_mask = mapped_cat == category_str
        native_df = cand_df.loc[native_mask]
        if len(native_df) >= qty:
            return native_df.head(qty).reset_index(drop=True)
        fallback_df = cand_df.loc[~native_mask]
        return pd.concat([native_df, fallback_df], ignore_index=True).head(qty).reset_index(drop=True)

    def generate_synthetic_traffic(
        self, request: CTGANGenerateRequest
    ) -> CTGANGenerateResponse:
        """Sample CTGAN traffic with optional conditional quotas, domain repair, and IoT device calibration."""
        model = self.get_or_load_model(request.model_id)

        has_native_device_model = (
            "device_id" in model.discrete_columns
            and "device_category" in model.discrete_columns
        )

        selected_device_profiles: List[str] = []
        if not has_native_device_model:
            if request.device_profiles:
                for prof in request.device_profiles:
                    clean_p = prof.strip().lower()
                    if clean_p not in PREDEFINED_PROFILES:
                        raise BadRequestError(
                            f"Unknown IoT device profile '{prof}'. Available: {sorted(list(PREDEFINED_PROFILES.keys()))}"
                        )
                    if clean_p not in selected_device_profiles:
                        selected_device_profiles.append(clean_p)
            elif request.apply_device_calibration:
                selected_device_profiles = list(PREDEFINED_PROFILES.keys())

        if request.category_counts:
            total_quota = sum(int(v) for v in request.category_counts.values())
            if total_quota < 1 or total_quota > 10000:
                raise BadRequestError(f"Total records requested via category_counts must be 1–10,000, got {total_quota}.")
            for cat, count in request.category_counts.items():
                if str(cat) not in VALID_CATEGORIES:
                    raise BadRequestError(f"Invalid category '{cat}'. Supported: {sorted(list(VALID_CATEGORIES))}")
                if int(count) < 0:
                    raise BadRequestError(f"Quota for '{cat}' must be non-negative.")

        effective_conditions: Optional[Dict[str, Any]] = dict(request.conditions) if request.conditions else None
        if effective_conditions:
            for col, val in effective_conditions.items():
                if col not in model.feature_columns and col not in model.discrete_columns:
                    raise BadRequestError(f"Unknown condition feature '{col}' for model '{request.model_id}'.")

            if has_native_device_model:
                v2_reg = self._get_v2_registry_data()
                devices_by_id = v2_reg["devices_by_id"]
                valid_dcats = set(v2_reg["device_categories"])

                if "device_id" in effective_conditions:
                    req_dev_id = str(effective_conditions["device_id"]).strip()
                    if req_dev_id not in devices_by_id:
                        raise BadRequestError(
                            f"Unknown V2 physical device_id '{req_dev_id}'. Must be one of device_001..device_070."
                        )
                    expected_dcat = devices_by_id[req_dev_id]["device_category"]
                    if "device_category" in effective_conditions:
                        req_dcat = str(effective_conditions["device_category"]).strip()
                        if req_dcat != expected_dcat:
                            raise BadRequestError(
                                f"Device '{req_dev_id}' belongs to category '{expected_dcat}', not '{req_dcat}'."
                            )
                    else:
                        # Auto-pair verified hardware category to eliminate passive single-key drift
                        effective_conditions["device_category"] = expected_dcat

                if "device_category" in effective_conditions and valid_dcats:
                    req_dcat = str(effective_conditions["device_category"]).strip()
                    if req_dcat not in valid_dcats:
                        raise BadRequestError(
                            f"Unsupported device_category '{req_dcat}' for '{request.model_id}'. Supported: {sorted(valid_dcats)}"
                        )

                if "label_category" in effective_conditions:
                    req_lcat = str(effective_conditions["label_category"]).strip()
                    if req_lcat not in VALID_CATEGORIES:
                        raise BadRequestError(
                            f"Unsupported traffic category '{req_lcat}'. Supported: {sorted(VALID_CATEGORIES)}"
                        )
                    if "device_id" in effective_conditions:
                        supp = v2_reg["pair_support"].get((str(effective_conditions["device_id"]), req_lcat), 0)
                        if supp == 0:
                            dcat_name = effective_conditions.get("device_category", "its category")
                            raise BadRequestError(
                                f"Zero training examples for {effective_conditions['device_id']} × {req_lcat}. "
                                f"Select device_category='{dcat_name}' or pick a traffic category supported by {effective_conditions['device_id']}."
                            )

        if has_native_device_model and request.category_counts and effective_conditions and "device_id" in effective_conditions:
            v2_reg = self._get_v2_registry_data()
            dev_id = str(effective_conditions["device_id"])
            low_cats = [
                f"{cat} ({v2_reg['pair_support'].get((dev_id, str(cat)), 0)} rows)"
                for cat, cnt in request.category_counts.items()
                if int(cnt) > 0 and v2_reg["pair_support"].get((dev_id, str(cat)), 0) < 10
            ]
            if low_cats:
                dcat_name = effective_conditions.get("device_category", "the parent category")
                raise BadRequestError(
                    f"Single-device multi-class quotas for '{dev_id}' include sparse/unseen classes ({', '.join(low_cats)}). "
                    f"Use device category '{dcat_name}' (all 8 classes supported) or switch to General Prior / Normal / single Attack mode."
                )

        # Optimize multi-condition SDV rejection sampling when label_category + device condition are both specified
        sampling_conditions: Optional[Dict[str, Any]] = dict(effective_conditions) if effective_conditions else None
        if (
            sampling_conditions
            and request.apply_domain_correction
            and "label_category" in sampling_conditions
            and ("device_category" in sampling_conditions or "device_id" in sampling_conditions)
        ):
            sampling_conditions.pop("is_attack", None)

        start_time = time.time()
        correction_summary: Optional[Dict[str, Any]] = None
        try:
            if request.category_counts:
                chunks: List[pd.DataFrame] = []
                agg_stats = {
                    "category_mismatches_fixed": 0,
                    "is_attack_violations_fixed": 0,
                    "protocol_mismatches_fixed": 0,
                    "dispersion_violations_fixed": 0,
                }
                for cat, cnt in request.category_counts.items():
                    qty = int(cnt)
                    if qty <= 0:
                        continue
                    cat_str = str(cat)
                    chunk_df = self._sample_clean_category(model, cat_str, qty, sampling_conditions)
                    if request.apply_domain_correction:
                        chunk_df, c_stats = self._apply_domain_correction(chunk_df, target_category=cat_str)
                        for k, v in c_stats.items():
                            agg_stats[k] += v
                    chunks.append(chunk_df)
                if not chunks:
                    raise BadRequestError("At least one category must have a positive sample count.")
                df = pd.concat(chunks, ignore_index=True).sample(frac=1.0, random_state=42).reset_index(drop=True)
                if request.apply_domain_correction:
                    correction_summary = agg_stats
            else:
                df = model.sample(num_rows=request.num_records, conditions=sampling_conditions)
                if request.apply_domain_correction and not df.empty:
                    target_cat = (
                        str(effective_conditions["label_category"])
                        if (effective_conditions and "label_category" in effective_conditions)
                        else None
                    )
                    df, correction_summary = self._apply_domain_correction(df, target_category=target_cat)
        except BadRequestError:
            raise
        except Exception as e:
            raise BadRequestError(f"CTGAN sampling failed: {str(e)}")

        if df.empty:
            raise BadRequestError("CTGAN sampling produced zero records.")

        has_native_device_conditioning = (
            has_native_device_model
            and "device_id" in df.columns
            and "device_category" in df.columns
        )
        device_calibrated = False
        if (
            not has_native_device_conditioning
            and request.apply_device_calibration
            and selected_device_profiles
        ):
            df = self._apply_device_calibration(df, selected_device_profiles)
            device_calibrated = True

        elapsed_sec = round(time.time() - start_time, 3)

        category_distribution: Dict[str, int] = {}
        if "label_category" in df.columns:
            category_distribution = {str(k): int(v) for k, v in df["label_category"].value_counts().to_dict().items()}

        device_distribution: Dict[str, int] = {}
        if "device_category" in df.columns:
            device_distribution = {str(k): int(v) for k, v in df["device_category"].value_counts().to_dict().items()}

        exported_files_map: Optional[Dict[str, str]] = None
        dataset_id_out: Optional[str] = None

        if request.export_dataset:
            now_utc = datetime.now(timezone.utc)
            timestamp_str = now_utc.strftime("%Y%m%d_%H%M%S")
            default_prefix = "iot_synthetic_v2" if request.model_id == "ctgan_device_aware_v2" else f"ctgan_{request.model_id}"
            prefix = (request.export_filename_prefix or default_prefix).strip()
            if not SAFE_ID_REGEX.match(prefix):
                raise BadRequestError(f"Invalid export_filename_prefix '{prefix}'.")

            fmt = request.export_format.strip().lower()
            if fmt not in ("parquet", "csv", "both"):
                raise BadRequestError(f"Unsupported export_format '{fmt}'. Allowed: 'parquet', 'csv', 'both'.")

            target_dir = self.settings.DATASETS_GENERATED_DIR
            target_dir.mkdir(parents=True, exist_ok=True)
            dataset_id_out = f"{prefix}_{timestamp_str}"
            if (target_dir / f"{dataset_id_out}.parquet").exists() or (target_dir / f"{dataset_id_out}.csv").exists():
                dataset_id_out = f"{prefix}_{timestamp_str}_{int(now_utc.microsecond // 1000):03d}"

            exported_files_map = {}

            if fmt in ("parquet", "both"):
                pq_name = f"{dataset_id_out}.parquet"
                df.to_parquet(target_dir / pq_name, index=False, engine="pyarrow")
                exported_files_map["parquet"] = pq_name

            if fmt in ("csv", "both"):
                csv_name = f"{dataset_id_out}.csv"
                df.to_csv(target_dir / csv_name, index=False)
                exported_files_map["csv"] = csv_name

            applied_conditions_meta = dict(effective_conditions or {})
            if request.category_counts:
                applied_conditions_meta["category_counts"] = request.category_counts

            raw_model_dev = getattr(getattr(model.synthesizer, "_model", None), "_device", "cpu")
            serving_dev = "cuda" if "cuda" in str(raw_model_dev).lower() else "cpu"

            meta_path = target_dir / f"{dataset_id_out}_metadata.json"
            with open(meta_path, "w", encoding="utf-8") as mf:
                json.dump(
                    {
                        "dataset_id": dataset_id_out,
                        "model_id": request.model_id,
                        "source": "ctgan_generator",
                        "native_device_conditioning": has_native_device_conditioning,
                        "serving_device": serving_dev,
                        "conditions_applied": applied_conditions_meta or None,
                        "num_records": len(df),
                        "columns_count": len(df.columns),
                        "domain_correction_applied": request.apply_domain_correction,
                        "domain_correction_summary": correction_summary,
                        "device_calibration_applied": device_calibrated,
                        "selected_device_profiles": selected_device_profiles,
                        "device_distribution": device_distribution,
                        "category_distribution": category_distribution,
                        "created_at": now_utc.isoformat(),
                    },
                    mf,
                    indent=2,
                )

        bounded_records = df.head(request.max_records_to_return).to_dict(orient="records")

        merged_conditions: Optional[Dict[str, Any]] = None
        if effective_conditions or request.category_counts:
            merged_conditions = dict(effective_conditions or {})
            if request.category_counts:
                merged_conditions["category_counts"] = request.category_counts

        return CTGANGenerateResponse(
            status="success",
            model_id=request.model_id,
            total_generated=len(df),
            returned_records_count=len(bounded_records),
            generation_time_sec=elapsed_sec,
            features_count=len(df.columns),
            features=list(df.columns),
            conditions_applied=merged_conditions,
            domain_correction_applied=request.apply_domain_correction,
            domain_correction_summary=correction_summary,
            device_calibration_applied=device_calibrated,
            device_distribution=device_distribution,
            category_distribution=category_distribution,
            records=bounded_records,
            dataset_id=dataset_id_out,
            exported_files=exported_files_map,
        )
