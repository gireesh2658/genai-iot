"""
IoTSynth AI - Feature Correlation Evaluator (Phase 6)
Evaluates multivariate relationship preservation between real and synthetic network features
using Pearson linear correlation, Spearman rank correlation, and matrix divergence metrics.
"""

from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import pandas as pd

from simulator.traffic_schema import CONTINUOUS_NUMERICAL_FEATURES


class FeatureCorrelationEvaluator:
    """Evaluates multivariate feature correlation preservation in synthetic data."""

    def __init__(self, key_features: Optional[List[str]] = None):
        self.key_features = key_features or [
            "Rate", "IAT", "Number", "Min", "Max", "AVG", "Std", "Variance", "Tot sum",
            "Header_Length", "Time_To_Live", "syn_count", "ack_count"
        ]

    def compute_correlation_matrices(
        self,
        real_df: pd.DataFrame,
        synth_df: pd.DataFrame,
        features: Optional[List[str]] = None,
        method: str = "pearson",
    ) -> Dict[str, Any]:
        """Compute correlation matrices and difference metrics for real and synthetic data.

        Args:
            real_df: Real training DataFrame.
            synth_df: Synthetic generated DataFrame.
            features: List of continuous/discrete numeric features to analyze.
            method: 'pearson' or 'spearman'.

        Returns:
            Dictionary containing real_corr, synth_corr, diff_corr, and aggregate error metrics.
        """
        cols = [c for c in (features or self.key_features) if c in real_df.columns and c in synth_df.columns]

        r_corr = real_df[cols].corr(method=method).fillna(0.0)
        s_corr = synth_df[cols].corr(method=method).fillna(0.0)

        # Difference matrix
        diff = s_corr - r_corr
        abs_diff = np.abs(diff.values)

        # Off-diagonal elements only (diagonal is always 1.0, difference is 0)
        mask = ~np.eye(len(cols), dtype=bool)
        off_diag_diffs = abs_diff[mask]

        mace = float(np.mean(off_diag_diffs)) if len(off_diag_diffs) > 0 else 0.0
        max_err = float(np.max(off_diag_diffs)) if len(off_diag_diffs) > 0 else 0.0
        frobenius_norm = float(np.linalg.norm(diff.values, "fro"))

        # Identify top preserved and top distorted pairs
        pairs = []
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                f1, f2 = cols[i], cols[j]
                r_val = float(r_corr.iloc[i, j])
                s_val = float(s_corr.iloc[i, j])
                delta = float(s_val - r_val)
                pairs.append({
                    "feature_1": f1,
                    "feature_2": f2,
                    "real_corr": round(r_val, 4),
                    "synth_corr": round(s_val, 4),
                    "abs_diff": round(abs(delta), 4),
                    "diff": round(delta, 4),
                })

        # Sort pairs by absolute error
        top_distorted = sorted(pairs, key=lambda x: x["abs_diff"], reverse=True)[:10]
        top_preserved = sorted(pairs, key=lambda x: x["abs_diff"])[:10]

        return {
            "method": method,
            "features": cols,
            "mean_absolute_correlation_error": round(mace, 4),
            "max_correlation_error": round(max_err, 4),
            "frobenius_norm": round(frobenius_norm, 4),
            "top_preserved_relationships": top_preserved,
            "top_distorted_relationships": top_distorted,
            "real_correlation_matrix": r_corr.round(4).to_dict(),
            "synthetic_correlation_matrix": s_corr.round(4).to_dict(),
            "difference_matrix": diff.round(4).to_dict(),
        }

    def evaluate_all(
        self,
        real_df: pd.DataFrame,
        synth_df: pd.DataFrame,
        features: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Compute both Pearson linear and Spearman rank correlation comparisons."""
        pearson_res = self.compute_correlation_matrices(real_df, synth_df, features, method="pearson")
        spearman_res = self.compute_correlation_matrices(real_df, synth_df, features, method="spearman")

        return {
            "pearson": pearson_res,
            "spearman": spearman_res,
            "summary": {
                "pearson_mace": pearson_res["mean_absolute_correlation_error"],
                "spearman_mace": spearman_res["mean_absolute_correlation_error"],
                "pearson_frobenius": pearson_res["frobenius_norm"],
                "spearman_frobenius": spearman_res["frobenius_norm"],
            },
        }
