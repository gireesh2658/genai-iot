"""
IoTSynth AI - Synthetic Data Evaluation Package
"""

from synthetic_engine.evaluation.data_loader import (
    load_evaluation_datasets,
    LoadedEvaluationDatasets,
    compute_file_sha256,
    compute_df_sha256,
)
from synthetic_engine.evaluation.validity import (
    SyntheticDataValidityEvaluator,
    AUTHORITATIVE_LABEL_MAP,
    AUTHORITATIVE_IS_ATTACK_MAP,
)
from synthetic_engine.evaluation.statistical import StatisticalDistributionEvaluator
from synthetic_engine.evaluation.correlation import FeatureCorrelationEvaluator
from synthetic_engine.evaluation.classes import ClassDistributionEvaluator
from synthetic_engine.evaluation.diversity import DiversityAndMemorizationEvaluator
from synthetic_engine.evaluation.orchestrator import EvaluationPipelineOrchestrator

__all__ = [
    "load_evaluation_datasets",
    "LoadedEvaluationDatasets",
    "compute_file_sha256",
    "compute_df_sha256",
    "SyntheticDataValidityEvaluator",
    "AUTHORITATIVE_LABEL_MAP",
    "AUTHORITATIVE_IS_ATTACK_MAP",
    "StatisticalDistributionEvaluator",
    "FeatureCorrelationEvaluator",
    "ClassDistributionEvaluator",
    "DiversityAndMemorizationEvaluator",
    "EvaluationPipelineOrchestrator",
]
