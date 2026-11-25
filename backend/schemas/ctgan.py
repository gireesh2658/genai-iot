"""
IoTSynth AI - CTGAN Generative Synthesis & Training Schemas
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CTGANModelSummary(BaseModel):
    model_id: str
    model_type: str = "CTGAN"
    role: str = "custom"
    is_primary: bool = False
    is_fitted: bool
    is_loaded: bool
    is_custom: bool = False
    epochs: int
    batch_size: int
    training_rows: Optional[int] = None
    feature_columns_count: Optional[int] = None
    discrete_columns_count: Optional[int] = None
    cond_vector_dim: Optional[int] = None
    training_duration_sec: Optional[float] = None
    artifact_availability: Dict[str, bool]
    device: str = "cpu"
    trained_device: Optional[str] = None
    serving_device: str = "cpu"
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CTGANModelListResponse(BaseModel):
    total_models: int
    models: List[CTGANModelSummary] = Field(default_factory=list)


class CTGANModelDetailResponse(BaseModel):
    model_id: str
    model_type: str = "CTGAN"
    is_fitted: bool
    is_loaded: bool
    feature_columns_count: int
    feature_columns: List[str] = Field(default_factory=list)
    discrete_columns_count: int
    discrete_columns: List[str] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)
    training_metadata: Dict[str, Any] = Field(default_factory=dict)
    artifact_availability: Dict[str, bool] = Field(default_factory=dict)


class IoTDeviceProfileItem(BaseModel):
    profile_name: str
    device_category: str
    default_protocols: List[str]
    packet_size_min: int
    packet_size_max: int
    communication_interval: float
    traffic_rate_min: float
    traffic_rate_max: float
    behavior_type: str
    description: str


class AttackProfileSummaryItem(BaseModel):
    attack_id: str
    label_raw: str
    label_category: str
    protocol_name: str
    protocol_type: int
    packet_size_min: int
    packet_size_max: int
    rate_min: float
    rate_max: float


class V2DeviceItem(BaseModel):
    device_id: str
    device_name: str
    device_category: str
    testbed_role: str
    train_row_count: int = 0
    supported_label_categories: List[str] = Field(default_factory=list)


class V2DeviceCatalogResponse(BaseModel):
    total_devices: int
    device_categories: List[str] = Field(default_factory=list)
    traffic_categories: List[str] = Field(default_factory=list)
    devices: List[V2DeviceItem] = Field(default_factory=list)


class CTGANGenerateRequest(BaseModel):
    model_id: str = Field("ctgan_device_aware_v2", description="CTGAN model checkpoint ID (primary default: ctgan_device_aware_v2)")
    num_records: int = Field(500, ge=1, le=10000, description="Total rows to sample when category_counts is omitted")
    conditions: Optional[Dict[str, Any]] = None
    category_counts: Optional[Dict[str, int]] = Field(
        None,
        description="Per-category synthetic sampling quotas for balanced or rare-attack oversampling",
    )
    device_profiles: Optional[List[str]] = Field(
        None,
        description="Target IoT device profiles (e.g. smart_camera, smart_thermostat, motion_sensor) for V1 post-hoc calibration",
    )
    apply_device_calibration: bool = Field(
        True,
        description="Attach IoT device_id/device_category and calibrate benign sensor flow envelopes for V1 non-device models (skipped automatically for native V2 models)",
    )
    apply_domain_correction: bool = Field(
        True,
        description="Apply deterministic label hierarchy, IANA protocol mapping, and Std=sqrt(Variance) repair",
    )
    max_records_to_return: int = Field(100, ge=0, le=1000)
    export_dataset: bool = Field(True, description="Save generated synthetic dataset to datasets/generated")
    export_format: str = Field("both", description="Export format: 'parquet', 'csv', or 'both'")
    export_filename_prefix: Optional[str] = Field("iot_synthetic_v2", description="Custom filename prefix")


class CTGANGenerateResponse(BaseModel):
    status: str = "success"
    model_id: str
    total_generated: int
    returned_records_count: int
    generation_time_sec: float
    features_count: int
    features: List[str] = Field(default_factory=list)
    conditions_applied: Optional[Dict[str, Any]] = None
    domain_correction_applied: bool = False
    domain_correction_summary: Optional[Dict[str, Any]] = None
    device_calibration_applied: bool = False
    device_distribution: Dict[str, int] = Field(default_factory=dict)
    category_distribution: Dict[str, int] = Field(default_factory=dict)
    records: List[Dict[str, Any]] = Field(default_factory=list)
    dataset_id: Optional[str] = None
    exported_files: Optional[Dict[str, str]] = None


class CTGANTrainRequest(BaseModel):
    model_id: str = Field(..., min_length=3, max_length=40, description="Name for new custom CTGAN checkpoint")
    epochs: int = Field(10, ge=1, le=150, description="Training epochs on CPU (e.g. 5-30 for quick fit, up to 150)")
    sample_size: int = Field(2000, ge=500, le=38466, description="Stratified real training rows to fit on")
    batch_size: int = Field(250, ge=50, le=500, description="Batch size (must be divisible by pac=10)")
    random_seed: int = 42


class CTGANTrainResponse(BaseModel):
    status: str = "completed"
    model_id: str
    epochs: int
    batch_size: int
    training_rows: int
    elapsed_seconds: float
    initial_generator_loss: Optional[float] = None
    final_generator_loss: Optional[float] = None
    initial_discriminator_loss: Optional[float] = None
    final_discriminator_loss: Optional[float] = None
