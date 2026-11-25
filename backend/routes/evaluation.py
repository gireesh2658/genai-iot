"""
IoTSynth AI - Backend Routes for Evaluation API (Phase 8.2.4)
FastAPI endpoints for synthetic data statistical quality audits and report retrieval.
"""

from typing import Optional
from fastapi import APIRouter, Depends, status

from backend.dependencies import get_evaluation_service
from backend.schemas.evaluation import (
    EvaluationDetailResponse,
    EvaluationResultsListResponse,
    EvaluationRunRequest,
    EvaluationRunResponse,
    EvaluationStatusResponse,
)
from backend.services.evaluation_service import EvaluationService

router = APIRouter(tags=["Synthetic Quality Evaluation"])


@router.get(
    "/status",
    response_model=EvaluationStatusResponse,
    summary="Get Evaluation Engine Readiness and Capabilities",
    description="Returns availability of the Phase 6 evaluation engine and whitelisted datasets.",
)
def get_evaluation_status(
    service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationStatusResponse:
    """Retrieve evaluation engine availability and capabilities."""
    return service.get_status()


@router.post(
    "/run",
    response_model=EvaluationRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Synthetic Quality Evaluation Workflow",
    description=(
        "Executes end-to-end statistical quality evaluation between an approved reference "
        "and synthetic dataset. Operates within an isolated run directory to prevent modifying approved reports."
    ),
)
def run_evaluation(
    request: EvaluationRunRequest,
    service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationRunResponse:
    """Run evaluation workflow using whitelisted dataset identifiers."""
    return service.run_evaluation(request)


@router.get(
    "/results",
    response_model=EvaluationResultsListResponse,
    summary="List Available Evaluation Results and Reports",
    description="Returns metadata for the approved Phase 6 evaluation report and any isolated execution runs.",
)
def list_evaluation_results(
    service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationResultsListResponse:
    """List available evaluation report summaries."""
    return service.list_results()


@router.get(
    "/results/{evaluation_id}",
    response_model=EvaluationDetailResponse,
    summary="Retrieve Detailed Evaluation Report",
    description=(
        "Retrieves detailed quality metrics (validity, KS/JS distances, correlation MACE, "
        "class distributions) for an approved or isolated run evaluation identifier."
    ),
)
def get_evaluation_result_detail(
    evaluation_id: str,
    service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationDetailResponse:
    """Retrieve comprehensive report metrics for a specific evaluation ID."""
    return service.get_result_detail(evaluation_id=evaluation_id)
