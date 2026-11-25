"""
IoTSynth AI - Generated Dataset Repository Routes
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from backend.dependencies import get_dataset_service
from backend.schemas.datasets import DatasetDetailResponse, DatasetListResponse
from backend.services.dataset_service import DatasetService

router = APIRouter(tags=["Generated Datasets"])


@router.get("", response_model=DatasetListResponse)
@router.get("/", response_model=DatasetListResponse, include_in_schema=False)
def list_datasets(
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetListResponse:
    return service.list_datasets()


@router.get("/{dataset_id}", response_model=DatasetDetailResponse)
def get_dataset(
    dataset_id: str,
    preview_limit: int = Query(40, ge=0, le=200),
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetDetailResponse:
    return service.get_dataset_detail(dataset_id, preview_limit=preview_limit)


@router.get("/{dataset_id}/download")
def download_dataset(
    dataset_id: str,
    format: str = Query("csv", description="'csv' or 'parquet'"),
    service: DatasetService = Depends(get_dataset_service),
) -> FileResponse:
    file_path = service.get_dataset_file_path(dataset_id=dataset_id, file_format=format)
    media_type = "text/csv" if format.lower() == "csv" else "application/octet-stream"
    return FileResponse(path=str(file_path), media_type=media_type, filename=file_path.name)


@router.delete("/{dataset_id}")
def delete_dataset(
    dataset_id: str,
    service: DatasetService = Depends(get_dataset_service),
) -> dict:
    return service.delete_dataset(dataset_id)
