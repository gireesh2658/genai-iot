"""
IoTSynth AI - Statistical Distribution Evaluator (Phase 6)
Compares marginal univariate distributions between real (train/val) and synthetic traffic
using parametric moments, non-parametric distance metrics (KS test, Wasserstein distance),
and information-theoretic divergence (Jensen-Shannon divergence).
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from scipy import stats
from scipy.spatial.distance import jensenshannon

from simulator.traffic_schema import (
    CONTINUOUS_NUMERICAL_FEATURES,
    DISCRETE_COUNT_FEATURES,
    BINARY_INDICATOR_FEATURES,
    CATEGORICAL_STRING_FEATURES,
)


class StatisticalDistributionEvaluator:
    """Evaluates statistical similarity and distribution distances between real and synthetic data."""

    def __init__(self, continuous_features: Optional[List[str]] = None):
        self.continuous_features = continuous_features or CONTINUOUS_NUMERICAL_FEATURES

    def compute_continuous_feature_stats(self, series: pd.Series) -> Dict[str, float]:
        """Compute parametric and non-parametric summary moments for a numeric feature."""
        vals = series.dropna().to_numpy()
        if len(vals) == 0:
            return {
                "mean": 0.0, "std": 0.0, "median": 0.0,
                "min": 0.0, "max": 0.0, "q25": 0.0, "q75": 0.0,
            }
        return {
            "mean": float(np.mean(vals)),
            "std": float(np.std(vals)),
            "median": float(np.median(vals)),
            "min": float(np.min(vals)),
            "max": float(np.max(vals)),
            "q25": float(np.percentile(vals, 25)),
            "q75": float(np.percentile(vals, 75)),
        }

    def compare_continuous_feature(
        self,
        real_series: pd.Series,
        synth_series: pd.Series,
    ) -> Dict[str, Any]:
        """Compare a single continuous feature between real and synthetic data."""
        r_vals = real_series.dropna().to_numpy()
        s_vals = synth_series.dropna().to_numpy()

        r_stats = self.compute_continuous_feature_stats(real_series)
        s_stats = self.compute_continuous_feature_stats(synth_series)

        # Kolmogorov-Smirnov 2-sample test
        ks_res = stats.ks_2samp(r_vals, s_vals)
        ks_stat = float(ks_res.statistic)
        ks_pvalue = float(ks_res.pvalue)

        # Wasserstein distance (raw & real-std standardized Earth Mover's Distance)
        w_dist = float(stats.wasserstein_distance(r_vals, s_vals))
        r_std = float(r_stats["std"])
        norm_w_dist = (
            float(stats.wasserstein_distance(r_vals / r_std, s_vals / r_std))
            if r_std > 1e-12
            else 0.0
        )

        # Relative mean and std differences
        mean_abs_err = abs(r_stats["mean"] - s_stats["mean"])
        std_abs_err = abs(r_stats["std"] - s_stats["std"])

        return {
            "real_stats": r_stats,
            "synth_stats": s_stats,
            "ks_statistic": round(ks_stat, 4),
            "ks_pvalue": ks_pvalue,
            "wasserstein_distance": round(w_dist, 4),
            "normalized_wasserstein_distance": round(norm_w_dist, 4),
            "mean_absolute_difference": round(mean_abs_err, 4),
            "std_absolute_difference": round(std_abs_err, 4),
        }

    def compare_categorical_feature(
        self,
        real_series: pd.Series,
        synth_series: pd.Series,
    ) -> Dict[str, Any]:
        """Compare a discrete/categorical feature using frequency distributions and Jensen-Shannon divergence."""
        r_counts = real_series.value_counts(normalize=True)
        s_counts = synth_series.value_counts(normalize=True)

        all_categories = sorted(list(set(r_counts.index).union(set(s_counts.index))))
        p = np.array([r_counts.get(c, 0.0) for c in all_categories], dtype=np.float64)
        q = np.array([s_counts.get(c, 0.0) for c in all_categories], dtype=np.float64)

        # Jensen-Shannon distance (square root of JS divergence, bounded in [0, 1])
        js_dist = float(jensenshannon(p, q, base=2))

        cat_comparison = {}
        for c in all_categories:
            cat_comparison[str(c)] = {
                "real_pct": round(float(r_counts.get(c, 0.0)) * 100, 3),
                "synth_pct": round(float(s_counts.get(c, 0.0)) * 100, 3),
                "abs_diff_pct": round(abs(float(r_counts.get(c, 0.0)) - float(s_counts.get(c, 0.0))) * 100, 3),
            }

        return {
            "jensen_shannon_distance": round(js_dist, 4),
            "categories_count": len(all_categories),
            "category_frequencies": cat_comparison,
        }

    def evaluate_distributions(
        self,
        real_train: pd.DataFrame,
        real_val: pd.DataFrame,
        synth_df: pd.DataFrame,
        discrete_columns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Run statistical distribution comparison of synthetic data against both real train and real val."""
        discrete_cols = set(discrete_columns or (DISCRETE_COUNT_FEATURES + BINARY_INDICATOR_FEATURES + CATEGORICAL_STRING_FEATURES))
        cont_cols = [c for c in self.continuous_features if c in synth_df.columns]

        train_continuous = {}
        val_continuous = {}
        for col in cont_cols:
            if col in real_train.columns and col in synth_df.columns:
                train_continuous[col] = self.compare_continuous_feature(real_train[col], synth_df[col])
            if col in real_val.columns and col in synth_df.columns:
                val_continuous[col] = self.compare_continuous_feature(real_val[col], synth_df[col])

        # Categorical comparisons
        target_cat_cols = ["label_raw", "label_category", "is_attack", "protocol_name", "Protocol Type", "TCP", "UDP", "HTTP"]
        target_cat_cols = [c for c in target_cat_cols if c in synth_df.columns and c in real_train.columns]

        train_categorical = {}
        val_categorical = {}
        for col in target_cat_cols:
            train_categorical[col] = self.compare_categorical_feature(real_train[col], synth_df[col])
            if col in real_val.columns:
                val_categorical[col] = self.compare_categorical_feature(real_val[col], synth_df[col])

        # Summary aggregates
        avg_ks_train = float(np.mean([m["ks_statistic"] for m in train_continuous.values()])) if train_continuous else 0.0
        avg_w_dist_train = float(np.mean([m["wasserstein_distance"] for m in train_continuous.values()])) if train_continuous else 0.0
        avg_norm_w_dist_train = (
            float(np.mean([m["normalized_wasserstein_distance"] for m in train_continuous.values()]))
            if train_continuous
            else 0.0
        )
        avg_js_dist_train = float(np.mean([m["jensen_shannon_distance"] for m in train_categorical.values()])) if train_categorical else 0.0

        return {
            "continuous_feature_comparisons_vs_train": train_continuous,
            "continuous_feature_comparisons_vs_val": val_continuous,
            "categorical_feature_comparisons_vs_train": train_categorical,
            "categorical_feature_comparisons_vs_val": val_categorical,
            "summary_metrics": {
                "average_ks_statistic_vs_train": round(avg_ks_train, 4),
                "average_wasserstein_distance_vs_train": round(avg_w_dist_train, 4),
                "average_normalized_wasserstein_distance_vs_train": round(avg_norm_w_dist_train, 4),
                "average_jensen_shannon_distance_vs_train": round(avg_js_dist_train, 4),
            },
        }
