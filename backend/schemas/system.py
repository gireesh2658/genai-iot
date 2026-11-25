"""
IoTSynth AI - System Diagnostics Schemas
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class CTGANModelStatusItem(BaseModel):
    model_id: str
    is_loaded: bool
    on_disk: bool
    file_size_bytes: Optional[int] = None


class AnomalyModelStatusItem(BaseModel):
    model_id: str
    classifier_name: str
    experiment_type: str
    augmentation_percentage: Optional[int] = None
    is_loaded: bool
    on_disk: bool


class SystemStatusResponse(BaseModel):
    status: str = "online"
    app_name: str
    app_version: str
    python_version: str
    dependencies: Dict[str, str]
    storage_status: Dict[str, bool]


class SystemModelsStatusResponse(BaseModel):
    ctgan_models_count: int
    ctgan_loaded_count: int
    ctgan_models: List[CTGANModelStatusItem]
    anomaly_models_count: int
    anomaly_loaded_count: int
    anomaly_experiment_types: List[str]
    anomaly_classifiers: List[str]
    anomaly_models: List[AnomalyModelStatusItem]
