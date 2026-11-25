"""
IoTSynth AI - Backend Routes for Anomaly Detection API (Phase 8.2.4)
FastAPI endpoints for model discovery, lazy-loaded inference, and experiment comparison.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status

from backend.dependencies import get_anomaly_service
from backend.schemas.anomaly import (
    AnomalyModelDetailResponse,
    AnomalyModelListResponse,
    AnomalyTrainRequest,
    AnomalyTrainResponse,
    ExperimentComparisonResponse,
    ExperimentListResponse,
    PredictBatchRequest,
    PredictBatchResponse,
    PredictSingleRequest,
    PredictSingleResponse,
)
from backend.services.anomaly_service import AnomalyService

router = APIRouter(tags=["Anomaly Detection & Inference"])


@router.get(
    "/models",
    response_model=AnomalyModelListResponse,
    summary="List Approved Anomaly Detection Models",
    description=(
        "Lists all 20 approved models across TRTR, TSTR, and TSTR+R experimental paradigms. "
        "Zero model weights are loaded during application startup."
    ),
)
def list_models(
    service: AnomalyService = Depends(get_anomaly_service),
) -> AnomalyModelListResponse:
    """Retrieve catalog of all 20 approved models with in-memory status and validation F1."""
    return service.list_models()


@router.get(
    "/models/{model_id}",
    response_model=AnomalyModelDetailResponse,
    summary="Get Model Details and Validation Metrics",
    description="Returns detailed metadata, hyperparameters, and validation performance for one approved model.",
)
def get_model_detail(
    model_id: str,
    service: AnomalyService = Depends(get_anomaly_service),
) -> AnomalyModelDetailResponse:
    """Retrieve metadata and per-class metrics for an approved model."""
    return service.get_model_detail(model_id=model_id)


@router.post(
    "/train",
    response_model=AnomalyTrainResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Train and Benchmark Custom Anomaly Detection Classifier",
    description=(
        "Trains a Scikit-learn anomaly detection pipeline (TRTR, TSTR, or TSTR+R) using any generated "
        "synthetic or simulator dataset and benchmarks against the disjoint 9,616-row held-out real validation split."
    ),
)
def train_model(
    request: AnomalyTrainRequest,
    service: AnomalyService = Depends(get_anomaly_service),
) -> AnomalyTrainResponse:
    """Train a custom classifier and compare against the TRTR baseline."""
    return service.train_model(request)


@router.delete(
    "/models/{model_id}",
    summary="Delete Custom Trained Anomaly Model",
    description="Deletes a user-trained custom anomaly model (Phase 7 baseline models are protected).",
)
def delete_custom_model(
    model_id: str,
    service: AnomalyService = Depends(get_anomaly_service),
) -> dict:
    """Remove a custom trained anomaly model and its metrics artifacts."""
    return service.delete_custom_model(model_id=model_id)


@router.post(
    "/predict",
    response_model=PredictSingleResponse,
    status_code=status.HTTP_200_OK,
    summary="Single-Flow Anomaly Detection Inference",
    description=(
        "Evaluates a single network flow record against an approved anomaly detection model. "
        "Strictly requires the 38 canonical features in order, rejecting missing/extra/leakage features."
    ),
)
def predict_single(
    request: PredictSingleRequest,
    service: AnomalyService = Depends(get_anomaly_service),
) -> PredictSingleResponse:
    """Execute single-flow prediction and class probabilities."""
    return service.predict_single(request)


@router.post(
    "/predict/batch",
    response_model=PredictBatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch Flow Anomaly Detection Inference",
    description=(
        "Evaluates multiple network flow records (up to 1,000) against an approved model. "
        "Validates every record against the 38 canonical features without feature leakage."
    ),
)
def predict_batch(
    request: PredictBatchRequest,
    service: AnomalyService = Depends(get_anomaly_service),
) -> PredictBatchResponse:
    """Execute batch inference across up to 1,000 flow records."""
    return service.predict_batch(request)


@router.get(
    "/experiments",
    response_model=ExperimentListResponse,
    summary="List Anomaly Detection Experimental Paradigms",
    description="Returns supported experimental paradigms (TRTR, TSTR, TSTR+R) and empirical synthetic caveats.",
)
def list_experiments(
    service: AnomalyService = Depends(get_anomaly_service),
) -> ExperimentListResponse:
    """List experimental paradigms and synthetic data quality warnings."""
    return service.list_experiments()


@router.get(
    "/experiments/compare",
    response_model=ExperimentComparisonResponse,
    summary="Compare Benchmarking Results Across Experiments",
    description=(
        "Retrieves comparative performance metrics across TRTR, TSTR, and TSTR+R (25%, 50%, 100%) "
        "from audited Phase 7 benchmarks. Supports optional filtering by experiment type, classifier, and augmentation."
    ),
)
def compare_experiments(
    experiment_type: Optional[str] = Query(None, description="Filter by experiment type (e.g. TRTR, TSTR, TSTR+R)"),
    classifier: Optional[str] = Query(None, description="Filter by classifier name (e.g. random_forest, extra_trees)"),
    augmentation_level: Optional[str] = Query(None, description="Filter by augmentation level (e.g. 0%, 25%, 50%, 100%)"),
    service: AnomalyService = Depends(get_anomaly_service),
) -> ExperimentComparisonResponse:
    """Compare performance metrics across experimental paradigms and augmentation tiers."""
    # Sanitize Query defaults if called directly without FastAPI DI
    exp_filter = experiment_type if isinstance(experiment_type, str) else None
    clf_filter = classifier if isinstance(classifier, str) else None
    aug_filter = augmentation_level if isinstance(augmentation_level, str) else None

    return service.compare_experiments(
        experiment_type=exp_filter,
        classifier=clf_filter,
        augmentation_level=aug_filter,
    )
