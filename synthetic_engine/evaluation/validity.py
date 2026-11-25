"""
IoTSynth AI - Synthetic Data Validity & Semantic Consistency Evaluator (Phase 6)
Audits schema structure, numerical ranges, physical statistical invariants,
protocol semantics, and label hierarchical consistency across synthetic records.
"""

from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd

from simulator.traffic_schema import (
    CONTINUOUS_NUMERICAL_FEATURES,
    DISCRETE_COUNT_FEATURES,
    BINARY_INDICATOR_FEATURES,
    CATEGORICAL_STRING_FEATURES,
)
from simulator.attack_profiles import ATTACK_PROFILES


# Authoritative mapping from label_raw to macro category and binary target
AUTHORITATIVE_LABEL_MAP: Dict[str, str] = {
    profile.label_raw: profile.label_category
    for profile in ATTACK_PROFILES.values()
}
AUTHORITATIVE_LABEL_MAP["BENIGN"] = "Benign"

AUTHORITATIVE_IS_ATTACK_MAP: Dict[str, int] = {
    lbl: 0 if lbl == "BENIGN" else 1
    for lbl in AUTHORITATIVE_LABEL_MAP.keys()
}


class SyntheticDataValidityEvaluator:
    """Evaluates syntactic, numerical, semantic, and domain-invariant validity."""

    def __init__(self, tolerance: float = 1e-2):
        self.tolerance = tolerance

    def evaluate_schema(self, df: pd.DataFrame, expected_columns: List[str]) -> Dict[str, Any]:
        """Check column presence, count, and ordering."""
        col_list = list(df.columns)
        has_correct_count = len(col_list) == len(expected_columns)
        has_correct_order = col_list == expected_columns
        missing = [c for c in expected_columns if c not in df.columns]
        unexpected = [c for c in df.columns if c not in expected_columns]

        return {
            "total_columns": len(col_list),
            "expected_columns": len(expected_columns),
            "has_correct_count": has_correct_count,
            "has_correct_order": has_correct_order,
            "missing_columns": missing,
            "unexpected_columns": unexpected,
            "is_valid": has_correct_count and has_correct_order,
        }

    def evaluate_numerical_validity(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Check for nulls, infs, negative values in non-negative features, and integer constraints."""
        n_rows = len(df)
        null_counts = df.isnull().sum().to_dict()
        total_nulls = sum(null_counts.values())

        # Check infinite values
        inf_counts = {}
        num_cols = df.select_dtypes(include=[np.number]).columns
        for c in num_cols:
            infs = int(np.isinf(df[c].to_numpy()).sum())
            if infs > 0:
                inf_counts[c] = infs
        total_infs = sum(inf_counts.values())

        # Non-negative metrics (Rates, IATs, packet sizes, counts, variances)
        non_negative_cols = [
            "Header_Length", "Rate", "IAT", "Number", "Min", "Max",
            "AVG", "Std", "Variance", "Tot sum", "syn_count", "ack_count",
            "fin_count", "rst_count"
        ]
        negative_violations = {}
        for c in non_negative_cols:
            if c in df.columns:
                negs = int((df[c] < 0).sum())
                if negs > 0:
                    negative_violations[c] = {
                        "count": negs,
                        "pct": round((negs / n_rows) * 100, 2),
                        "min_value": float(df[c].min()),
                    }

        # Discrete integer checks
        int_cols = ["Number", "syn_count", "ack_count", "fin_count", "rst_count", "Protocol Type", "is_attack"]
        fractional_violations = {}
        for c in int_cols:
            if c in df.columns:
                vals = df[c].to_numpy()
                is_int = np.isclose(vals, np.round(vals), atol=1e-3)
                frac_cnt = int((~is_int).sum())
                if frac_cnt > 0:
                    fractional_violations[c] = {
                        "count": frac_cnt,
                        "pct": round((frac_cnt / n_rows) * 100, 2),
                    }

        return {
            "total_rows": n_rows,
            "total_nulls": total_nulls,
            "total_infs": total_infs,
            "negative_violations": negative_violations,
            "fractional_violations": fractional_violations,
            "has_nulls": total_nulls > 0,
            "has_infs": total_infs > 0,
            "has_negative_violations": len(negative_violations) > 0,
        }

    def evaluate_statistical_invariants(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Verify mathematical invariants:
        1. AVG vs Tot sum / Number
        2. Std vs sqrt(Variance)
        3. Min <= AVG <= Max
        """
        n_rows = len(df)
        violations = {}

        # 1. Min <= AVG <= Max
        if {"Min", "AVG", "Max"}.issubset(df.columns):
            min_gt_avg = int((df["Min"] > df["AVG"] + self.tolerance).sum())
            avg_gt_max = int((df["AVG"] > df["Max"] + self.tolerance).sum())
            violations["min_le_avg_le_max"] = {
                "min_gt_avg_count": min_gt_avg,
                "avg_gt_max_count": avg_gt_max,
                "total_violations": min_gt_avg + avg_gt_max,
                "violation_pct": round(((min_gt_avg + avg_gt_max) / n_rows) * 100, 2),
            }

        # 2. Std ≈ sqrt(Variance)
        if {"Std", "Variance"}.issubset(df.columns):
            std = df["Std"].to_numpy()
            var = df["Variance"].to_numpy()
            # Variance can be slightly negative in generative output; clip for sqrt
            expected_std = np.sqrt(np.maximum(var, 0))
            std_diff = np.abs(std - expected_std)
            # Tolerance: relative or absolute
            is_close = np.isclose(std, expected_std, rtol=0.10, atol=1.0)
            std_mismatch = int((~is_close).sum())
            violations["std_sqrt_variance"] = {
                "violation_count": std_mismatch,
                "violation_pct": round((std_mismatch / n_rows) * 100, 2),
                "mean_abs_diff": float(np.mean(std_diff)),
                "max_abs_diff": float(np.max(std_diff)),
            }

        # 3. AVG ≈ Tot sum / Number
        if {"AVG", "Tot sum", "Number"}.issubset(df.columns):
            num = np.maximum(df["Number"].to_numpy(), 1e-5)
            tot = df["Tot sum"].to_numpy()
            avg = df["AVG"].to_numpy()
            expected_avg = tot / num
            avg_diff = np.abs(avg - expected_avg)
            is_close = np.isclose(avg, expected_avg, rtol=0.10, atol=5.0)
            avg_mismatch = int((~is_close).sum())
            violations["avg_tot_sum_ratio"] = {
                "violation_count": avg_mismatch,
                "violation_pct": round((avg_mismatch / n_rows) * 100, 2),
                "mean_abs_diff": float(np.mean(avg_diff)),
                "max_abs_diff": float(np.max(avg_diff)),
            }

        return violations

    def evaluate_protocol_consistency(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Verify protocol layering and indicator consistency."""
        n_rows = len(df)
        violations = {}

        # Protocol Type vs protocol_name
        proto_map = {6: "TCP", 17: "UDP", 1: "ICMP", 47: "GRE", 2: "IGMP"}
        if {"Protocol Type", "protocol_name"}.issubset(df.columns):
            mismatches = 0
            for p_type, p_name in proto_map.items():
                mask = np.isclose(df["Protocol Type"], p_type, atol=0.5)
                wrong_name = (mask & (df["protocol_name"] != p_name)).sum()
                mismatches += int(wrong_name)
            violations["protocol_type_name_mismatch"] = {
                "count": mismatches,
                "pct": round((mismatches / n_rows) * 100, 2),
            }

        # Protocol indicators consistency (e.g. TCP == 1 and UDP == 1 simultaneously)
        if {"TCP", "UDP"}.issubset(df.columns):
            both_tcp_udp = int(((df["TCP"] > 0.8) & (df["UDP"] > 0.8)).sum())
            violations["simultaneous_tcp_and_udp"] = {
                "count": both_tcp_udp,
                "pct": round((both_tcp_udp / n_rows) * 100, 2),
            }

        return violations

    def evaluate_label_consistency(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Check hierarchical relationships between label_raw, label_category, and is_attack."""
        n_rows = len(df)
        required_cols = {"label_raw", "label_category", "is_attack"}
        if not required_cols.issubset(df.columns):
            return {"error": f"Missing label columns: {required_cols - set(df.columns)}"}

        # 1. label_raw -> expected label_category
        cat_mismatches = 0
        cat_mismatch_details = {}
        for idx, row in df.iterrows():
            raw = str(row["label_raw"]).strip()
            cat = str(row["label_category"]).strip()
            expected_cat = AUTHORITATIVE_LABEL_MAP.get(raw)
            if expected_cat is not None and cat != expected_cat:
                cat_mismatches += 1
                key = f"{raw} -> {cat} (expected {expected_cat})"
                cat_mismatch_details[key] = cat_mismatch_details.get(key, 0) + 1

        # 2. is_attack vs label_category / label_raw
        # Specific check A: Benign with is_attack == 1
        benign_with_attack = int(((df["label_category"] == "Benign") & (df["is_attack"] == 1)).sum())

        # Specific check B: Malicious with is_attack == 0
        attack_with_benign = int(((df["label_category"] != "Benign") & (df["is_attack"] == 0)).sum())

        # Total is_attack semantic violations
        total_target_violations = benign_with_attack + attack_with_benign

        return {
            "total_rows": n_rows,
            "category_mismatches": {
                "count": cat_mismatches,
                "pct": round((cat_mismatches / n_rows) * 100, 2),
                "top_patterns": dict(sorted(cat_mismatch_details.items(), key=lambda x: x[1], reverse=True)[:10]),
            },
            "benign_with_is_attack_1": {
                "count": benign_with_attack,
                "pct_of_benign": round((benign_with_attack / max((df["label_category"] == "Benign").sum(), 1)) * 100, 2),
                "pct_of_total": round((benign_with_attack / n_rows) * 100, 2),
            },
            "attack_with_is_attack_0": {
                "count": attack_with_benign,
                "pct_of_attacks": round((attack_with_benign / max((df["label_category"] != "Benign").sum(), 1)) * 100, 2),
                "pct_of_total": round((attack_with_benign / n_rows) * 100, 2),
            },
            "total_is_attack_violations": {
                "count": total_target_violations,
                "pct": round((total_target_violations / n_rows) * 100, 2),
            },
        }

    def evaluate_all(self, df: pd.DataFrame, expected_columns: List[str]) -> Dict[str, Any]:
        """Run all validity evaluations and compile report."""
        return {
            "schema_validity": self.evaluate_schema(df, expected_columns),
            "numerical_validity": self.evaluate_numerical_validity(df),
            "statistical_invariants": self.evaluate_statistical_invariants(df),
            "protocol_consistency": self.evaluate_protocol_consistency(df),
            "label_consistency": self.evaluate_label_consistency(df),
        }
