"""
IoTSynth AI - Backend Schemas for Anomaly Detection API (Phase 8.2.4)
Pydantic schemas for model discovery, single/batch inference, and experiment comparison.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AnomalyModelSummary(BaseModel):
    """Summary information for an approved anomaly detection model."""

    model_id: str = Field(..., description="Approved model identifier")
    classifier_name: str = Field(
        ...,
        description="Classifier family: extra_trees, hist_gradient_boosting, logistic_regression, random_forest",
    )
    experiment_type: str = Field(..., description="Experiment paradigm: TRTR, TSTR, or TSTR+R")
    augmentation_percentage: Optional[int] = Field(
        None, description="Synthetic augmentation percentage (25, 50, 100 for TSTR+R)"
    )
    is_loaded: bool = Field(..., description="Whether the model weights are currently resident in memory")
    is_custom: bool = Field(False, description="Whether this is a user-trained custom model")
    synthetic_source: Optional[str] = Field(None, description="Synthetic dataset identifier used if custom-trained")
    train_records: Optional[int] = Field(None, description="Number of training records")
    supported_capabilities: List[str] = Field(..., description="Supported methods, e.g. ['predict', 'predict_proba']")
    macro_f1: Optional[float] = Field(None, description="Macro F1 score on validation set from Phase 7 benchmarks")
    balanced_accuracy: Optional[float] = Field(None, description="Balanced accuracy score on validation set")


class AnomalyModelListResponse(BaseModel):
    """Response containing list of all approved anomaly detection models."""

    total_models: int = Field(..., description="Total approved models count (expected 20)")
    loaded_models_count: int = Field(..., description="Number of models currently cached in memory")
    models: List[AnomalyModelSummary] = Field(..., description="List of model summaries")


class AnomalyModelDetailResponse(BaseModel):
    """Detailed metadata and metrics for a specific approved model."""

    model_id: str = Field(..., description="Approved model identifier")
    classifier_name: str = Field(..., description="Classifier family name")
    experiment_type: str = Field(..., description="Experiment paradigm: TRTR, TSTR, or TSTR+R")
    augmentation_percentage: Optional[int] = Field(None, description="Synthetic augmentation level")
    is_loaded: bool = Field(..., description="Whether model weights are resident in memory")
    features_count: int = Field(38, description="Expected input features count (38)")
    target_column: str = Field("label_category", description="Model classification target")
    classes: List[str] = Field(..., description="Output threat category labels (8 classes)")
    pipeline_steps: List[str] = Field(..., description="Scikit-learn pipeline step names")
    train_records: Optional[int] = Field(None, description="Number of training records")
    val_records: Optional[int] = Field(None, description="Number of validation records")
    model_file_sha256: Optional[str] = Field(None, description="SHA-256 checksum of saved model artifact")
    overall_metrics: Optional[Dict[str, Any]] = Field(None, description="Overall validation metrics")
    per_class_metrics: Optional[Dict[str, Any]] = Field(None, description="Per-class validation precision, recall, F1")
    confusion_matrix: Optional[Dict[str, Any]] = Field(None, description="8x8 validation confusion matrix counts")
    hyperparameters: Optional[Dict[str, Any]] = Field(None, description="Classifier hyperparameters")
    provenance_info: Optional[Dict[str, Any]] = Field(None, description="Training data provenance and synthetic source info")
    is_custom: bool = Field(False, description="Whether this is a user-trained custom model")


class AnomalyTrainRequest(BaseModel):
    """Request payload for training and benchmarking a custom anomaly detection classifier."""

    classifier_name: str = Field(
        "random_forest",
        description="Classifier family: random_forest, extra_trees, hist_gradient_boosting, or logistic_regression",
    )
    experiment_type: str = Field(
        "TSTR+R",
        description="Training paradigm: TRTR (real only), TSTR (synthetic only), or TSTR+R (real + synthetic)",
    )
    synthetic_dataset_id: Optional[str] = Field(
        "ctgan_initial_sample_v1_domain_corrected",
        description="Generated synthetic or simulator dataset stem in datasets/generated/ (used for TSTR and TSTR+R)",
    )
    augmentation_fraction: float = Field(
        1.0,
        ge=0.05,
        le=1.0,
        description="Fraction of the synthetic pool to mix into training (0.05 to 1.0)",
    )
    balance_minority_classes: bool = Field(
        True,
        description="Prioritize underrepresented rare attack categories when augmenting real training data (TSTR+R)",
    )
    model_tag: Optional[str] = Field(
        None,
        description="Optional custom alphanumeric identifier suffix for the trained model",
    )
    random_seed: int = Field(42, description="Deterministic seed for sampling and estimator initialization")


class AnomalyTrainResponse(BaseModel):
    """Benchmark report returned after training an anomaly detector against the held-out real validation split."""

    status: str = Field("completed", description="Execution status")
    model_id: str = Field(..., description="Registered custom model identifier")
    classifier_name: str = Field(..., description="Classifier family")
    experiment_type: str = Field(..., description="Experiment paradigm executed")
    synthetic_dataset_id: Optional[str] = Field(None, description="Synthetic dataset used, if applicable")
    train_records: int = Field(..., description="Total training records used")
    synthetic_records_used: int = Field(..., description="Number of synthetic records included in training")
    val_records: int = Field(..., description="Held-out real validation records evaluated (9,616)")
    fit_duration_seconds: float = Field(..., description="Model fit runtime in seconds")
    overall_metrics: Dict[str, Any] = Field(..., description="Validation metrics (macro F1, balanced accuracy, ROC-AUC)")
    per_class_metrics: Dict[str, Any] = Field(..., description="Per-class validation precision, recall, F1, support")
    trtr_baseline_macro_f1: Optional[float] = Field(None, description="Reference TRTR baseline Macro F1 for comparison")
    macro_f1_delta_vs_trtr: Optional[float] = Field(None, description="Macro F1 delta against TRTR baseline")
    balanced_accuracy_delta_vs_trtr: Optional[float] = Field(None, description="Balanced Accuracy delta vs TRTR baseline")
    per_class_f1_deltas_vs_trtr: Dict[str, float] = Field(default_factory=dict, description="Per-class F1 gain/loss vs TRTR")
    confusion_matrix: Dict[str, Any] = Field(default_factory=dict, description="8x8 validation confusion matrix")
    quality_warnings: List[str] = Field(default_factory=list, description="Synthetic data provenance & caveats")


class PredictSingleRequest(BaseModel):
    """Inference request for a single network flow record."""

    model_id: str = Field(..., description="Approved anomaly detection model identifier")
    features: Dict[str, Any] = Field(
        ...,
        description="Feature dictionary containing exactly the 38 canonical features",
    )


class PredictSingleResponse(BaseModel):
    """Inference result for a single network flow record."""

    model_id: str = Field(..., description="Model identifier used for inference")
    predicted_category: str = Field(..., description="Predicted macro threat category (e.g. 'Benign', 'DDoS')")
    is_attack: int = Field(..., description="Binary anomaly indicator (0 for Benign, 1 for Attack)")
    confidence: float = Field(..., description="Confidence score (highest class probability)")
    probabilities: Dict[str, float] = Field(..., description="Predicted probabilities for each of the 8 classes")
    latency_ms: float = Field(..., description="Inference latency in milliseconds")


class PredictionItem(BaseModel):
    """Individual prediction within a batch inference response."""

    index: int = Field(..., description="0-based record index in input batch")
    predicted_category: str = Field(..., description="Predicted macro threat category")
    is_attack: int = Field(..., description="Binary anomaly indicator (0 for Benign, 1 for Attack)")
    confidence: float = Field(..., description="Confidence score (highest class probability)")
    probabilities: Dict[str, float] = Field(..., description="Predicted probabilities across all classes")


class PredictBatchRequest(BaseModel):
    """Batch inference request for multiple network flow records."""

    model_id: str = Field(..., description="Approved anomaly detection model identifier")
    records: List[Dict[str, Any]] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="List of feature dictionaries (bounded: 1 to 1000 records)",
    )


class PredictBatchResponse(BaseModel):
    """Batch inference response."""

    model_id: str = Field(..., description="Model identifier used for inference")
    total_records: int = Field(..., description="Number of records evaluated")
    attack_count: int = Field(..., description="Number of records classified as attacks")
    benign_count: int = Field(..., description="Number of records classified as benign")
    predictions: List[PredictionItem] = Field(..., description="Prediction results for each input record")
    latency_ms: float = Field(..., description="Total batch inference latency in milliseconds")


class ExperimentListResponse(BaseModel):
    """List of available experiment benchmarking results."""

    experiments: List[str] = Field(..., description="Available experimental paradigms: TRTR, TSTR, TSTR+R")
    available_classifiers: List[str] = Field(..., description="Available classifier families")
    augmentation_levels: List[str] = Field(..., description="Available synthetic augmentation levels")
    total_models: int = Field(..., description="Total models benchmarked across all experiments (20)")
    quality_warnings: List[str] = Field(..., description="Empirical synthetic data quality caveats")


class ExperimentComparisonResponse(BaseModel):
    """Comparison table and metrics across TRTR, TSTR, and TSTR+R experiments."""

    total_comparisons: int = Field(..., description="Number of comparative entries returned")
    comparisons: List[Dict[str, Any]] = Field(..., description="Comparison records across models and experiments")
    trtr_vs_tstr_summary: Optional[List[Dict[str, Any]]] = Field(
        None, description="TRTR vs TSTR comparative baseline summary"
    )
    quality_warnings: List[str] = Field(..., description="Empirical synthetic data quality caveats")
