"""
IoTSynth AI - Backend Application Configuration
Centralized paths, API metadata, and path-boundary enforcement.
"""

import os
from pathlib import Path
from typing import List, Optional, Set

try:
    from dotenv import load_dotenv

    _env_file = Path(__file__).resolve().parent.parent / ".env"
    if _env_file.exists():
        load_dotenv(_env_file)
    else:
        load_dotenv()
except ImportError:
    pass


class Settings:
    """Application configuration and directory management."""

    APP_NAME: str = "IoTSynth AI API"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = (
        "Synthetic IoT Device Traffic Generator (CTGAN) for Anomaly-Detection Model Training"
    )
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    CORS_ORIGIN_REGEX: Optional[str] = None
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = ["Accept", "Authorization", "Content-Type"]

    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

    DATASETS_DIR: Path = PROJECT_ROOT / "datasets"
    DATASETS_PROCESSED_DIR: Path = DATASETS_DIR / "processed"
    BUNDLED_DATASETS_GENERATED_DIR: Path = DATASETS_DIR / "generated"
    DATASETS_GENERATED_DIR: Path = BUNDLED_DATASETS_GENERATED_DIR

    MODELS_DIR: Path = PROJECT_ROOT / "models"
    CTGAN_MODELS_DIR: Path = MODELS_DIR / "ctgan"
    DEFAULT_CTGAN_MODEL: str = "ctgan_device_aware_v2"

    ANOMALY_MODELS_DIR: Path = PROJECT_ROOT / "anomaly_detection" / "models"
    CUSTOM_ANOMALY_MODELS_DIR: Path = ANOMALY_MODELS_DIR / "custom"
    ANOMALY_RESULTS_DIR: Path = PROJECT_ROOT / "anomaly_detection" / "results"
    CUSTOM_ANOMALY_RESULTS_DIR: Path = ANOMALY_RESULTS_DIR / "custom"

    PHASE6_REPORTS_DIR: Path = PROJECT_ROOT / "reports" / "phase6"
    EVALUATION_RUNS_DIR: Path = PROJECT_ROOT / "reports" / "evaluations" / "runs"

    APPROVED_ROOT_DIRS: Set[Path] = {
        PROJECT_ROOT / "datasets",
        PROJECT_ROOT / "models",
        PROJECT_ROOT / "anomaly_detection",
        PROJECT_ROOT / "reports",
        PROJECT_ROOT / "simulator",
        PROJECT_ROOT / "synthetic_engine",
    }

    def __init__(self) -> None:
        self.DEBUG = os.getenv("IOTSYNTH_DEBUG", "false").lower() in ("true", "1", "t")
        self.DEFAULT_CTGAN_MODEL = (
            os.getenv("IOTSYNTH_DEFAULT_CTGAN_MODEL", "ctgan_device_aware_v2").strip()
            or "ctgan_device_aware_v2"
        )

        raw_cors = (os.getenv("CORS_ORIGINS") or os.getenv("IOTSYNTH_CORS_ORIGINS") or "").strip()
        if raw_cors:
            parsed_origins = [
                origin.strip().rstrip("/")
                for origin in raw_cors.split(",")
                if origin.strip()
            ]
            if parsed_origins:
                self.CORS_ORIGINS = parsed_origins
                if "*" in self.CORS_ORIGINS:
                    self.CORS_ALLOW_CREDENTIALS = False
        else:
            self.CORS_ORIGINS = list(Settings.CORS_ORIGINS)

        cors_regex = (
            os.getenv("CORS_ORIGIN_REGEX") or os.getenv("IOTSYNTH_CORS_ORIGIN_REGEX") or ""
        ).strip()
        self.CORS_ORIGIN_REGEX = cors_regex or None

        env_gen_dir = (os.getenv("IOTSYNTH_GENERATED_DIR") or "").strip()
        if env_gen_dir:
            self.DATASETS_GENERATED_DIR = Path(env_gen_dir).expanduser().resolve()
        else:
            self.DATASETS_GENERATED_DIR = self.BUNDLED_DATASETS_GENERATED_DIR

        self.APPROVED_ROOT_DIRS = set(Settings.APPROVED_ROOT_DIRS) | {
            self.DATASETS_GENERATED_DIR.resolve(),
            self.BUNDLED_DATASETS_GENERATED_DIR.resolve(),
        }
        self.validate_directories()

    def iter_generated_search_dirs(self) -> List[Path]:
        """Return writable runtime generated dir first, plus bundled baseline dir if distinct."""
        active = self.DATASETS_GENERATED_DIR.resolve()
        bundled = self.BUNDLED_DATASETS_GENERATED_DIR.resolve()
        if active == bundled:
            return [self.DATASETS_GENERATED_DIR]
        return [self.DATASETS_GENERATED_DIR, self.BUNDLED_DATASETS_GENERATED_DIR]

    def validate_directories(self) -> None:
        """Ensure all canonical project paths remain strictly within PROJECT_ROOT."""
        resolved_root = self.PROJECT_ROOT.resolve()
        for path in [
            self.DATASETS_DIR,
            self.MODELS_DIR,
            self.ANOMALY_MODELS_DIR,
            self.ANOMALY_RESULTS_DIR,
            self.PHASE6_REPORTS_DIR,
            self.EVALUATION_RUNS_DIR,
        ]:
            resolved = path.resolve()
            if not resolved.is_relative_to(resolved_root):
                raise ValueError(
                    f"Configured directory '{resolved}' escapes PROJECT_ROOT '{self.PROJECT_ROOT}'"
                )

    def is_safe_path(self, target_path: Path) -> bool:
        """Verify that a target path resolves strictly inside approved project roots."""
        try:
            resolved_target = target_path.resolve()
            return any(
                resolved_target.is_relative_to(approved_dir.resolve())
                for approved_dir in self.APPROVED_ROOT_DIRS
            )
        except Exception:
            return False


_settings_instance: Settings | None = None


def get_settings() -> Settings:
    """Retrieve or instantiate singleton application settings."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
