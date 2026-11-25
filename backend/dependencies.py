"""
IoTSynth AI - Backend Dependency Providers
"""

from typing import Optional
from fastapi import Depends

from backend.config import Settings, get_settings
from backend.services.anomaly_service import AnomalyService
from backend.services.ctgan_service import CTGANService
from backend.services.dataset_service import DatasetService
from backend.services.evaluation_service import EvaluationService

_dataset_service_instance: Optional[DatasetService] = None
_ctgan_service_instance: Optional[CTGANService] = None
_evaluation_service_instance: Optional[EvaluationService] = None
_anomaly_service_instance: Optional[AnomalyService] = None


def get_app_settings() -> Settings:
    return get_settings()


def get_ctgan_service(settings: Settings = Depends(get_app_settings)) -> CTGANService:
    global _ctgan_service_instance
    if _ctgan_service_instance is None:
        real_settings = settings if isinstance(settings, Settings) else get_app_settings()
        _ctgan_service_instance = CTGANService(settings=real_settings)
    return _ctgan_service_instance


def get_dataset_service(settings: Settings = Depends(get_app_settings)) -> DatasetService:
    global _dataset_service_instance
    if _dataset_service_instance is None:
        real_settings = settings if isinstance(settings, Settings) else get_app_settings()
        _dataset_service_instance = DatasetService(settings=real_settings)
    return _dataset_service_instance


def get_evaluation_service(settings: Settings = Depends(get_app_settings)) -> EvaluationService:
    global _evaluation_service_instance
    if _evaluation_service_instance is None:
        real_settings = settings if isinstance(settings, Settings) else get_app_settings()
        _evaluation_service_instance = EvaluationService(settings=real_settings)
    return _evaluation_service_instance


def get_anomaly_service(settings: Settings = Depends(get_app_settings)) -> AnomalyService:
    global _anomaly_service_instance
    if _anomaly_service_instance is None:
        real_settings = settings if isinstance(settings, Settings) else get_app_settings()
        _anomaly_service_instance = AnomalyService(settings=real_settings)
    return _anomaly_service_instance
