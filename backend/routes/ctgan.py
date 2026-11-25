"""
IoTSynth AI - CTGAN Generative Routes
"""

from typing import List
from fastapi import APIRouter, Depends, status

from backend.dependencies import get_ctgan_service
from backend.schemas.ctgan import (
    AttackProfileSummaryItem,
    CTGANGenerateRequest,
    CTGANGenerateResponse,
    CTGANModelDetailResponse,
    CTGANModelListResponse,
    CTGANTrainRequest,
    CTGANTrainResponse,
    IoTDeviceProfileItem,
    V2DeviceCatalogResponse,
)
from backend.services.ctgan_service import CTGANService

router = APIRouter(tags=["CTGAN Synthesizer"])


@router.get("/device-profiles", response_model=List[IoTDeviceProfileItem])
def list_device_profiles(
    service: CTGANService = Depends(get_ctgan_service),
) -> List[IoTDeviceProfileItem]:
    return service.list_device_profiles()


@router.get("/v2-devices", response_model=V2DeviceCatalogResponse)
def list_v2_devices(
    service: CTGANService = Depends(get_ctgan_service),
) -> V2DeviceCatalogResponse:
    return service.list_v2_devices()


@router.get("/attack-profiles", response_model=List[AttackProfileSummaryItem])
def list_attack_profiles(
    service: CTGANService = Depends(get_ctgan_service),
) -> List[AttackProfileSummaryItem]:
    return service.list_attack_profiles()


@router.get("/models", response_model=CTGANModelListResponse)
def list_ctgan_models(
    service: CTGANService = Depends(get_ctgan_service),
) -> CTGANModelListResponse:
    return service.list_models()


@router.get("/models/{model_id}", response_model=CTGANModelDetailResponse)
def get_ctgan_model(
    model_id: str,
    service: CTGANService = Depends(get_ctgan_service),
) -> CTGANModelDetailResponse:
    return service.get_model_detail(model_id)


@router.post("/generate", response_model=CTGANGenerateResponse, status_code=status.HTTP_200_OK)
def generate_ctgan_traffic(
    request: CTGANGenerateRequest,
    service: CTGANService = Depends(get_ctgan_service),
) -> CTGANGenerateResponse:
    return service.generate_synthetic_traffic(request)


@router.post("/train", response_model=CTGANTrainResponse, status_code=status.HTTP_201_CREATED)
def train_ctgan_model(
    request: CTGANTrainRequest,
    service: CTGANService = Depends(get_ctgan_service),
) -> CTGANTrainResponse:
    return service.train_model(request)


@router.delete("/models/{model_id}")
def delete_ctgan_model(
    model_id: str,
    service: CTGANService = Depends(get_ctgan_service),
) -> dict:
    return service.delete_model(model_id)
