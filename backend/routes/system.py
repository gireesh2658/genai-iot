"""
IoTSynth AI - System Diagnostics Routes
"""

import sys
from fastapi import APIRouter, Depends

from backend.config import Settings
from backend.dependencies import (
    get_anomaly_service,
    get_app_settings,
    get_ctgan_service,
)
from backend.schemas.system import (
    AnomalyModelStatusItem,
    CTGANModelStatusItem,
    SystemModelsStatusResponse,
    SystemStatusResponse,
)
from backend.services.anomaly_service import AnomalyService
from backend.services.ctgan_service import CTGANService
from synthetic_engine.ctgan_model import CTGANModel

router = APIRouter(tags=["System"])


@router.get("/status", response_model=SystemStatusResponse)
def get_system_status(
    settings: Settings = Depends(get_app_settings),
) -> SystemStatusResponse:
    def _pkg_version(module_name: str) -> str:
        try:
            mod = __import__(module_name)
            return getattr(mod, "__version__", "installed")
        except Exception:
            return "not installed"

    return SystemStatusResponse(
        status="online",
        app_name=settings.APP_NAME,
        app_version=settings.APP_VERSION,
        python_version=sys.version.split()[0],
        dependencies={
            "fastapi": _pkg_version("fastapi"),
            "pydantic": _pkg_version("pydantic"),
            "scikit-learn": _pkg_version("sklearn"),
            "torch": _pkg_version("torch"),
            "sdv": _pkg_version("sdv"),
            "ctgan": _pkg_version("ctgan"),
            "pandas": _pkg_version("pandas"),
            "numpy": _pkg_version("numpy"),
        },
        storage_status={
            "datasets_processed_ready": settings.DATASETS_PROCESSED_DIR.is_dir(),
            "datasets_generated_ready": settings.DATASETS_GENERATED_DIR.is_dir(),
            "ctgan_models_ready": settings.CTGAN_MODELS_DIR.is_dir(),
            "anomaly_models_ready": settings.ANOMALY_MODELS_DIR.is_dir(),
            "reports_ready": settings.PHASE6_REPORTS_DIR.is_dir(),
        },
    )


@router.get("/models-status", response_model=SystemModelsStatusResponse)
def get_models_status(
    settings: Settings = Depends(get_app_settings),
    ctgan_service: CTGANService = Depends(get_ctgan_service),
    anomaly_service: AnomalyService = Depends(get_anomaly_service),
) -> SystemModelsStatusResponse:
    ctgan_list = ctgan_service.list_models()
    ctgan_items = []
    ctgan_loaded = 0
    for m in ctgan_list.models:
        if m.is_loaded:
            ctgan_loaded += 1
        _, _, weights_file = CTGANModel.resolve_artifact_paths(
            settings.CTGAN_MODELS_DIR, m.model_id, for_write=False
        )
        ctgan_items.append(
            CTGANModelStatusItem(
                model_id=m.model_id,
                is_loaded=m.is_loaded,
                on_disk=weights_file.is_file(),
                file_size_bytes=weights_file.stat().st_size if weights_file.is_file() else None,
            )
        )

    anomaly_list = anomaly_service.list_models()
    anomaly_items = []
    anomaly_loaded = 0
    for m in anomaly_list.models:
        if m.is_loaded:
            anomaly_loaded += 1
        anomaly_items.append(
            AnomalyModelStatusItem(
                model_id=m.model_id,
                classifier_name=m.classifier_name,
                experiment_type=m.experiment_type,
                augmentation_percentage=m.augmentation_percentage,
                is_loaded=m.is_loaded,
                on_disk=True,
            )
        )

    return SystemModelsStatusResponse(
        ctgan_models_count=len(ctgan_items),
        ctgan_loaded_count=ctgan_loaded,
        ctgan_models=ctgan_items,
        anomaly_models_count=len(anomaly_items),
        anomaly_loaded_count=anomaly_loaded,
        anomaly_experiment_types=["TRTR", "TSTR", "TSTR+R"],
        anomaly_classifiers=["extra_trees", "hist_gradient_boosting", "logistic_regression", "random_forest"],
        anomaly_models=anomaly_items,
    )
