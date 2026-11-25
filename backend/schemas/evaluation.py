"""
IoTSynth AI - Backend Schemas for Evaluation API (Phase 8.2.4)
Pydantic schemas for synthetic data quality evaluation, dataset validation, and report inspection.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvaluationStatusResponse(BaseModel):
    """Status and availability of the synthetic data evaluation engine."""

    engine_available: bool = Field(True, description="Whether the Phase 6 evaluation engine is available")
    engine_class: str = Field(..., description="Evaluation orchestrator class name")
    available_reference_datasets: List[str] = Field(..., description="Whitelisted reference dataset identifiers")
    available_synthetic_datasets: List[str] = Field(..., description="Whitelisted synthetic dataset identifiers")
    capabilities: List[str] = Field(..., description="Supported evaluation dimensions")


class EvaluationRunRequest(BaseModel):
    """Parameters for running a synthetic data quality evaluation."""

    reference_dataset_id: str = Field(
        "ciciot2023_preprocessed_sample",
        description="Logical identifier of the reference dataset (must be whitelisted)",
    )
    synthetic_dataset_id: str = Field(
        "ctgan_initial_sample_v1_domain_corrected",
        description="Logical identifier of the synthetic dataset (must be whitelisted)",
    )
    generate_plots: bool = Field(
        False,
        description="Whether to generate visual plots (PNG) in the isolated run directory",
    )
    generate_corrected_dataset: bool = Field(
        False,
        description="Whether to run the candidate corrector (always False for read-only evaluation API)",
    )
    test_conditional_sampling: bool = Field(
        False,
        description="Whether to test conditional generation with CTGAN model",
    )


class EvaluationRunResponse(BaseModel):
    """Structured results from executing an evaluation workflow."""

    evaluation_id: str = Field(..., description="Unique execution identifier")
    status: str = Field("completed", description="Evaluation execution status")
    timestamp: str = Field(..., description="Timestamp of evaluation completion")
    reference_dataset_id: str = Field(..., description="Reference dataset evaluated")
    synthetic_dataset_id: str = Field(..., description="Synthetic dataset evaluated")
    summary_metrics: Dict[str, Any] = Field(..., description="Key summary metrics (validity, KS, JS, MACE, etc.)")
    reports: Dict[str, Any] = Field(..., description="Individual dimension report summaries")
    isolated_reports_dir: str = Field(..., description="Isolated execution reports directory")


class EvaluationResultSummary(BaseModel):
    """Summary of an available evaluation report collection."""

    evaluation_id: str = Field(..., description="Evaluation identifier")
    title: str = Field(..., description="Human-readable title")
    source: str = Field(..., description="Source origin: 'phase6_approved' or 'isolated_run'")
    created_at: Optional[str] = Field(None, description="Report timestamp or generation date")
    available_reports: List[str] = Field(..., description="List of report file types available")


class EvaluationResultsListResponse(BaseModel):
    """Response containing list of available evaluation results."""

    total_results: int = Field(..., description="Total available evaluation results")
    results: List[EvaluationResultSummary] = Field(..., description="List of evaluation results")


class EvaluationDetailResponse(BaseModel):
    """Comprehensive detail for a specific evaluation result."""

    evaluation_id: str = Field(..., description="Evaluation identifier")
    source: str = Field(..., description="Origin of the report")
    data_validity: Optional[Dict[str, Any]] = Field(None, description="Schema and domain validity report")
    statistical_similarity: Optional[Dict[str, Any]] = Field(None, description="KS, JS, and Wasserstein distances")
    feature_correlation: Optional[Dict[str, Any]] = Field(None, description="Correlation preservation and MACE")
    class_distribution: Optional[Dict[str, Any]] = Field(None, description="Class distributions and conditional fidelity")
    diversity_and_memorization: Optional[Dict[str, Any]] = Field(None, description="Diversity and distance to training data")
    three_candidate_comparison: Optional[Dict[str, Any]] = Field(None, description="Comparative metrics across candidate datasets")
