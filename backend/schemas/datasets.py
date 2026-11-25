"""
IoTSynth AI - Dataset Repository Schemas
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DatasetSummaryItem(BaseModel):
    dataset_id: str
    filename: str
    format: str
    available_formats: List[str] = Field(default_factory=list)
    size_bytes: int
    created_at: str
    has_metadata: bool = False
    is_protected: bool = False
    num_records: Optional[int] = None
    num_columns: Optional[int] = None


class DatasetListResponse(BaseModel):
    total_datasets: int
    datasets: List[DatasetSummaryItem] = Field(default_factory=list)


class DatasetDetailResponse(BaseModel):
    dataset_id: str
    primary_filename: str
    available_formats: List[str]
    num_records: Optional[int] = None
    num_columns: Optional[int] = None
    columns: List[str] = Field(default_factory=list)
    files: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = None
    preview_records: List[Dict[str, Any]] = Field(default_factory=list)
