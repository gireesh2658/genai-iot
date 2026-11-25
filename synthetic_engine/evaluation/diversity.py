"""
IoTSynth AI - Diversity & Memorization Evaluator (Phase 6)
Analyzes synthetic record uniqueness, internal duplication, training data memorization,
and nearest-neighbor continuous distance distributions.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors

from simulator.traffic_schema import CONTINUOUS_NUMERICAL_FEATURES


class DiversityAndMemorizationEvaluator:
    """Evaluates synthetic sample diversity and checks for training set memorization."""

    def __init__(self, continuous_features: Optional[List[str]] = None):
        self.continuous_features = continuous_features or CONTINUOUS_NUMERICAL_FEATURES

    def evaluate_internal_diversity(self, synth_df: pd.DataFrame) -> Dict[str, Any]:
        """Check for exact duplicate rows and compute uniqueness ratio in synthetic data."""
        n_rows = len(synth_df)
        dup_mask = synth_df.duplicated(keep=False)
        exact_duplicates = int(synth_df.duplicated().sum())
        rows_in_duplicate_groups = int(dup_mask.sum())
        unique_records = n_rows - exact_duplicates
        uniqueness_ratio = round(unique_records / n_rows, 4) if n_rows > 0 else 0.0

        return {
            "total_records": n_rows,
            "exact_duplicate_records": exact_duplicates,
            "rows_in_duplicate_groups": rows_in_duplicate_groups,
            "unique_records": unique_records,
            "uniqueness_ratio": uniqueness_ratio,
            "duplicate_percentage": round((exact_duplicates / n_rows) * 100, 2),
        }

    def evaluate_training_overlap(
        self,
        real_train: pd.DataFrame,
        synth_df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Check for exact full-row copies of training records inside the synthetic dataset."""
        common_cols = [c for c in real_train.columns if c in synth_df.columns]
        n_synth = len(synth_df)

        # Merge on all common columns to find identical rows
        # Drop duplicates in train to avoid multi-match inflation
        train_dedup = real_train[common_cols].drop_duplicates()
        merged = pd.merge(synth_df[common_cols], train_dedup, how="inner", on=common_cols)
        overlap_count = len(merged)

        return {
            "exact_overlap_count": overlap_count,
            "overlap_percentage": round((overlap_count / n_synth) * 100, 4) if n_synth > 0 else 0.0,
            "has_exact_training_memorization": overlap_count > 0,
        }

    def evaluate_nearest_neighbor_distances(
        self,
        real_train: pd.DataFrame,
        synth_df: pd.DataFrame,
        features: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Compute Euclidean distance from each synthetic record to its nearest training record in standardized feature space."""
        cols = [c for c in (features or self.continuous_features) if c in real_train.columns and c in synth_df.columns]

        scaler = StandardScaler()
        # Fit on real train, transform both
        train_scaled = scaler.fit_transform(real_train[cols].fillna(0.0))
        synth_scaled = scaler.transform(synth_df[cols].fillna(0.0))

        # 1-Nearest Neighbor search using Euclidean distance
        nn = NearestNeighbors(n_neighbors=1, metric="euclidean", n_jobs=-1)
        nn.fit(train_scaled)

        distances, _ = nn.kneighbors(synth_scaled)
        dists = distances.flatten()

        # Near-zero threshold for continuous numerical memorization
        zero_dist_count = int((dists < 1e-4).sum())
        p01 = float(np.percentile(dists, 1))
        p05 = float(np.percentile(dists, 5))
        p25 = float(np.percentile(dists, 25))
        p50 = float(np.percentile(dists, 50))
        p75 = float(np.percentile(dists, 75))
        p95 = float(np.percentile(dists, 95))

        return {
            "features_used": cols,
            "min_distance": round(float(np.min(dists)), 4),
            "p01_distance": round(p01, 4),
            "p05_distance": round(p05, 4),
            "median_distance": round(p50, 4),
            "mean_distance": round(float(np.mean(dists)), 4),
            "max_distance": round(float(np.max(dists)), 4),
            "p95_distance": round(p95, 4),
            "std_distance": round(float(np.std(dists)), 4),
            "near_zero_distance_count": zero_dist_count,
            "near_zero_distance_pct": round((zero_dist_count / len(dists)) * 100, 4),
            "raw_distances": dists,  # For plotting
        }

    def evaluate_all(
        self,
        real_train: pd.DataFrame,
        synth_df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Run all diversity and memorization checks."""
        internal_res = self.evaluate_internal_diversity(synth_df)
        overlap_res = self.evaluate_training_overlap(real_train, synth_df)
        nn_res = self.evaluate_nearest_neighbor_distances(real_train, synth_df)

        # Remove raw distances array from JSON serializable report
        nn_report = {k: v for k, v in nn_res.items() if k != "raw_distances"}

        return {
            "internal_diversity": internal_res,
            "training_overlap": overlap_res,
            "nearest_neighbor_distance": nn_report,
            "summary": {
                "uniqueness_ratio": internal_res["uniqueness_ratio"],
                "exact_training_overlaps": overlap_res["exact_overlap_count"],
                "median_nn_distance": nn_report["median_distance"],
                "memorization_risk": "Low" if overlap_res["exact_overlap_count"] == 0 and nn_report["near_zero_distance_count"] == 0 else "Moderate/High",
            },
        }
