"""
IoTSynth AI - Class Distribution & Conditional Generation Evaluator (Phase 6)
Audits macro-category and raw-label distribution preservation across splits,
and assesses class-conditioned sampling fidelity using the fitted CTGAN model.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from synthetic_engine.ctgan_model import CTGANModel


class ClassDistributionEvaluator:
    """Evaluates multi-tier class distributions and conditional generation fidelity."""

    def compare_class_distributions(
        self,
        real_train: pd.DataFrame,
        real_val: pd.DataFrame,
        synth_df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Compare macro-category and raw-label distributions across train, val, and synthetic sets."""
        n_train = len(real_train)
        n_val = len(real_val)
        n_synth = len(synth_df)

        # 1. Macro categories
        train_macro = real_train["label_category"].value_counts()
        val_macro = real_val["label_category"].value_counts()
        synth_macro = synth_df["label_category"].value_counts()

        all_macros = sorted(list(set(train_macro.index).union(set(synth_macro.index))))
        macro_table = {}
        for m in all_macros:
            tr_cnt = int(train_macro.get(m, 0))
            va_cnt = int(val_macro.get(m, 0))
            sy_cnt = int(synth_macro.get(m, 0))
            macro_table[m] = {
                "train_count": tr_cnt,
                "train_pct": round((tr_cnt / n_train) * 100, 2),
                "val_count": va_cnt,
                "val_pct": round((va_cnt / n_val) * 100, 2),
                "synth_count": sy_cnt,
                "synth_pct": round((sy_cnt / n_synth) * 100, 2),
                "diff_vs_train_pct": round(((sy_cnt / n_synth) - (tr_cnt / n_train)) * 100, 2),
            }

        # 2. Raw labels
        train_raw = real_train["label_raw"].value_counts()
        val_raw = real_val["label_raw"].value_counts()
        synth_raw = synth_df["label_raw"].value_counts()

        all_raws = sorted(list(set(train_raw.index).union(set(synth_raw.index))))
        raw_table = {}
        absent_in_synth = []
        for r in all_raws:
            tr_cnt = int(train_raw.get(r, 0))
            va_cnt = int(val_raw.get(r, 0))
            sy_cnt = int(synth_raw.get(r, 0))
            if sy_cnt == 0:
                absent_in_synth.append(r)
            raw_table[r] = {
                "train_count": tr_cnt,
                "train_pct": round((tr_cnt / n_train) * 100, 3),
                "val_count": va_cnt,
                "val_pct": round((va_cnt / n_val) * 100, 3),
                "synth_count": sy_cnt,
                "synth_pct": round((sy_cnt / n_synth) * 100, 3),
            }

        # 3. Target is_attack distribution
        train_target = real_train["is_attack"].value_counts()
        synth_target = synth_df["is_attack"].value_counts()
        target_table = {
            "train_is_attack_1": int(train_target.get(1, 0)),
            "train_is_attack_0": int(train_target.get(0, 0)),
            "synth_is_attack_1": int(synth_target.get(1, 0)),
            "synth_is_attack_0": int(synth_target.get(0, 0)),
            "train_attack_pct": round((train_target.get(1, 0) / n_train) * 100, 2),
            "synth_attack_pct": round((synth_target.get(1, 0) / n_synth) * 100, 2),
        }

        return {
            "macro_category_comparison": macro_table,
            "raw_label_comparison": raw_table,
            "target_comparison": target_table,
            "unique_raw_labels_in_train": len(train_raw),
            "unique_raw_labels_in_synth": len(synth_raw),
            "absent_raw_labels_in_synth": absent_in_synth,
            "coverage_pct": round((len(synth_raw) / len(train_raw)) * 100, 2),
        }

    def evaluate_conditional_generation(
        self,
        model: CTGANModel,
        scenarios: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Evaluate class-conditioned sampling fidelity across specified threat categories and labels."""
        if scenarios is None:
            scenarios = [
                {"name": "DDoS", "condition": {"label_category": "DDoS"}, "num_rows": 100},
                {"name": "DoS", "condition": {"label_category": "DoS"}, "num_rows": 100},
                {"name": "Mirai", "condition": {"label_category": "Mirai"}, "num_rows": 100},
                {"name": "Benign", "condition": {"label_category": "Benign"}, "num_rows": 100},
                {"name": "Reconnaissance", "condition": {"label_category": "Reconnaissance"}, "num_rows": 100},
                {"name": "DNS_SPOOFING", "condition": {"label_raw": "DNS_SPOOFING"}, "num_rows": 50},
                {"name": "DICTIONARYBRUTEFORCE", "condition": {"label_raw": "DICTIONARYBRUTEFORCE"}, "num_rows": 50},
            ]

        results = []
        for s in scenarios:
            name = s["name"]
            cond = s["condition"]
            n_req = s["num_rows"]

            try:
                sampled = model.sample(num_rows=n_req, conditions=cond)
                cond_col = list(cond.keys())[0]
                expected_val = cond[cond_col]

                actual_matches = int((sampled[cond_col] == expected_val).sum())
                match_pct = round((actual_matches / len(sampled)) * 100, 2) if len(sampled) > 0 else 0.0

                results.append({
                    "scenario": name,
                    "condition": cond,
                    "requested_rows": n_req,
                    "generated_rows": len(sampled),
                    "matching_rows": actual_matches,
                    "match_percentage": match_pct,
                    "success": actual_matches == n_req,
                })
            except Exception as e:
                results.append({
                    "scenario": name,
                    "condition": cond,
                    "requested_rows": n_req,
                    "generated_rows": 0,
                    "matching_rows": 0,
                    "match_percentage": 0.0,
                    "success": False,
                    "error": str(e),
                })

        return results
