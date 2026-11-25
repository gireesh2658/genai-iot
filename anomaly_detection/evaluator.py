"""
IoTSynth AI - Anomaly Detection Model Evaluator (Phase 7.2)

Evaluates multi-class network traffic anomaly detection models with rigorous
imbalanced classification metrics, zero-division safeguards, and per-class analysis.
"""

from typing import Dict, Any, List, Optional, Union
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
)

from anomaly_detection.feature_config import EXPECTED_LABEL_CATEGORIES


class AnomalyDetectionEvaluator:
    """Standardized evaluator for multi-class and binary IoT anomaly detection models."""

    def __init__(self, target_categories: Optional[List[str]] = None):
        self.target_categories = target_categories or list(EXPECTED_LABEL_CATEGORIES)

    def evaluate_predictions(
        self,
        y_true: Union[pd.Series, np.ndarray, List[str]],
        y_pred: Union[pd.Series, np.ndarray, List[str]],
        y_prob: Optional[np.ndarray] = None,
        model_name: str = "model",
        fit_duration_seconds: Optional[float] = None,
        inference_duration_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Compute exhaustive evaluation metrics on held-out validation predictions.

        Args:
            y_true: Ground-truth target labels.
            y_pred: Predicted target labels.
            y_prob: Optional predicted class probability matrix (N x K).
            model_name: Identifier for the model being evaluated.
            fit_duration_seconds: Measured training runtime.
            inference_duration_seconds: Measured validation prediction runtime.

        Returns:
            Dictionary containing overall summary metrics, per-class metrics,
            confusion matrix, and classification report.
        """
        y_true_arr = np.asarray(y_true)
        y_pred_arr = np.asarray(y_pred)
        n_records = len(y_true_arr)

        # 1. Overall Summary Metrics
        acc = float(accuracy_score(y_true_arr, y_pred_arr))
        bal_acc = float(balanced_accuracy_score(y_true_arr, y_pred_arr))

        macro_p = float(precision_score(y_true_arr, y_pred_arr, average="macro", zero_division=0))
        macro_r = float(recall_score(y_true_arr, y_pred_arr, average="macro", zero_division=0))
        macro_f1 = float(f1_score(y_true_arr, y_pred_arr, average="macro", zero_division=0))

        weighted_p = float(precision_score(y_true_arr, y_pred_arr, average="weighted", zero_division=0))
        weighted_r = float(recall_score(y_true_arr, y_pred_arr, average="weighted", zero_division=0))
        weighted_f1 = float(f1_score(y_true_arr, y_pred_arr, average="weighted", zero_division=0))

        # 2. Per-Class Precision, Recall, F1, and Support
        per_class_report = classification_report(
            y_true_arr,
            y_pred_arr,
            labels=self.target_categories,
            target_names=self.target_categories,
            output_dict=True,
            zero_division=0,
        )

        per_class_metrics: Dict[str, Dict[str, Any]] = {}
        for cat in self.target_categories:
            if cat in per_class_report:
                per_class_metrics[cat] = {
                    "precision": round(float(per_class_report[cat]["precision"]), 4),
                    "recall": round(float(per_class_report[cat]["recall"]), 4),
                    "f1_score": round(float(per_class_report[cat]["f1-score"]), 4),
                    "support": int(per_class_report[cat]["support"]),
                }
            else:
                per_class_metrics[cat] = {
                    "precision": 0.0,
                    "recall": 0.0,
                    "f1_score": 0.0,
                    "support": 0,
                }

        # 3. Confusion Matrix
        cm_array = confusion_matrix(
            y_true_arr,
            y_pred_arr,
            labels=self.target_categories,
        )
        cm_df = pd.DataFrame(
            cm_array,
            index=[f"true_{c}" for c in self.target_categories],
            columns=[f"pred_{c}" for c in self.target_categories],
        )

        # 4. Multi-Class ROC-AUC (One-vs-Rest) calculation if probabilities are available
        roc_auc_macro: Optional[float] = None
        roc_auc_status: str = "not_computed"
        if y_prob is not None:
            try:
                # Ensure all classes in self.target_categories have columns in y_prob
                # Only valid if len(y_prob.shape) == 2 and shape[1] == len(self.target_categories)
                if y_prob.shape[1] == len(self.target_categories):
                    # Check if all classes are represented in y_true
                    classes_in_y = set(y_true_arr)
                    if len(classes_in_y) == len(self.target_categories):
                        roc_auc_macro = float(
                            roc_auc_score(
                                y_true_arr,
                                y_prob,
                                multi_class="ovr",
                                average="macro",
                                labels=self.target_categories,
                            )
                        )
                        roc_auc_status = "computed_ovr_macro"
                    else:
                        missing = set(self.target_categories) - classes_in_y
                        roc_auc_status = f"unreliable_missing_classes_in_eval_{missing}"
                else:
                    roc_auc_status = f"probability_dim_mismatch_{y_prob.shape[1]}_vs_{len(self.target_categories)}"
            except Exception as e:
                roc_auc_status = f"error_{str(e)}"

        return {
            "model_name": model_name,
            "total_records_evaluated": n_records,
            "overall_metrics": {
                "accuracy": round(acc, 4),
                "balanced_accuracy": round(bal_acc, 4),
                "macro_precision": round(macro_p, 4),
                "macro_recall": round(macro_r, 4),
                "macro_f1": round(macro_f1, 4),
                "weighted_precision": round(weighted_p, 4),
                "weighted_recall": round(weighted_r, 4),
                "weighted_f1": round(weighted_f1, 4),
                "roc_auc_macro": round(roc_auc_macro, 4) if roc_auc_macro is not None else None,
                "roc_auc_status": roc_auc_status,
            },
            "per_class_metrics": per_class_metrics,
            "confusion_matrix": cm_df.to_dict(),
            "confusion_matrix_raw": cm_array.tolist(),
            "fit_duration_seconds": round(fit_duration_seconds, 3) if fit_duration_seconds is not None else None,
            "inference_duration_seconds": round(inference_duration_seconds, 3) if inference_duration_seconds is not None else None,
        }

    @staticmethod
    def generate_comparison_summary(
        results_list: List[Dict[str, Any]],
    ) -> pd.DataFrame:
        """Tabulate and rank models by macro F1 score descending."""
        rows = []
        for r in results_list:
            om = r["overall_metrics"]
            rows.append({
                "Model": r["model_name"],
                "Macro F1": om["macro_f1"],
                "Balanced Accuracy": om["balanced_accuracy"],
                "Accuracy": om["accuracy"],
                "Macro Precision": om["macro_precision"],
                "Macro Recall": om["macro_recall"],
                "Weighted F1": om["weighted_f1"],
                "Training Time (s)": r.get("fit_duration_seconds"),
                "Inference Time (s)": r.get("inference_duration_seconds"),
            })
        df_summary = pd.DataFrame(rows)
        if not df_summary.empty:
            df_summary = df_summary.sort_values(by="Macro F1", ascending=False).reset_index(drop=True)
            df_summary.index = df_summary.index + 1  # 1-based rank
        return df_summary

    @staticmethod
    def generate_trtr_vs_tstr_comparison(
        trtr_results: List[Dict[str, Any]],
        tstr_results: List[Dict[str, Any]],
    ) -> pd.DataFrame:
        """Tabulate side-by-side comparison between TRTR and TSTR experiments.

        Computes:
        - Absolute difference = TSTR score - TRTR score
        - Relative difference (%) = ((TSTR score - TRTR score) / TRTR score) * 100
        """
        trtr_map = {r["model_name"]: r["overall_metrics"] for r in trtr_results}
        tstr_map = {r["model_name"]: r["overall_metrics"] for r in tstr_results}

        rows = []
        for model_name in trtr_map.keys():
            if model_name not in tstr_map:
                continue
            tr = trtr_map[model_name]
            ts = tstr_map[model_name]

            f1_tr = tr["macro_f1"]
            f1_ts = ts["macro_f1"]
            f1_abs = round(f1_ts - f1_tr, 4)
            f1_rel = round(((f1_ts - f1_tr) / f1_tr) * 100, 2) if f1_tr != 0 else 0.0

            bal_tr = tr["balanced_accuracy"]
            bal_ts = ts["balanced_accuracy"]
            bal_abs = round(bal_ts - bal_tr, 4)
            bal_rel = round(((bal_ts - bal_tr) / bal_tr) * 100, 2) if bal_tr != 0 else 0.0

            wf1_tr = tr["weighted_f1"]
            wf1_ts = ts["weighted_f1"]
            wf1_abs = round(wf1_ts - wf1_tr, 4)
            wf1_rel = round(((wf1_ts - wf1_tr) / wf1_tr) * 100, 2) if wf1_tr != 0 else 0.0

            rows.append({
                "Model": model_name,
                "TRTR Macro F1": f1_tr,
                "TSTR Macro F1": f1_ts,
                "Abs Macro F1 Diff": f1_abs,
                "Rel Macro F1 Diff (%)": f1_rel,
                "TRTR Bal Acc": bal_tr,
                "TSTR Bal Acc": bal_ts,
                "TRTR Weighted F1": wf1_tr,
                "TSTR Weighted F1": wf1_ts,
                "Abs Weighted F1 Diff": wf1_abs,
                "Rel Weighted F1 Diff (%)": wf1_rel,
            })

        df_comp = pd.DataFrame(rows)
        if not df_comp.empty:
            df_comp = df_comp.sort_values(by="TSTR Macro F1", ascending=False).reset_index(drop=True)
            df_comp.index = df_comp.index + 1
        return df_comp

    @staticmethod
    def generate_tstr_plus_r_comparison(
        trtr_results: List[Dict[str, Any]],
        tstr_results: List[Dict[str, Any]],
        tstr_r_by_level: Dict[str, List[Dict[str, Any]]],
    ) -> pd.DataFrame:
        """Tabulate comprehensive comparison across TRTR, TSTR, and all TSTR+R augmentation levels.

        Computes:
        - Absolute difference = Variant score - TRTR baseline score
        - Relative difference (%) = ((Variant score - TRTR baseline score) / TRTR baseline score) * 100
        """
        trtr_map = {r["model_name"]: r["overall_metrics"] for r in trtr_results}
        tstr_map = {r["model_name"]: r["overall_metrics"] for r in tstr_results}

        rows = []
        for model_name, tr in trtr_map.items():
            f1_tr = tr["macro_f1"]
            bal_tr = tr["balanced_accuracy"]
            wf1_tr = tr["weighted_f1"]
            acc_tr = tr["accuracy"]

            # 1. TRTR Reference
            rows.append({
                "Model": model_name,
                "Experiment": "TRTR (0% Synth)",
                "Augmentation Level": "0%",
                "Train Records": 38466,
                "Synthetic Records": 0,
                "Macro F1": f1_tr,
                "Balanced Accuracy": bal_tr,
                "Accuracy": acc_tr,
                "Weighted F1": wf1_tr,
                "Abs Macro F1 Diff": 0.0,
                "Rel Macro F1 Diff (%)": 0.0,
                "Abs Bal Acc Diff": 0.0,
                "Rel Bal Acc Diff (%)": 0.0,
                "Abs Weighted F1 Diff": 0.0,
                "Rel Weighted F1 Diff (%)": 0.0,
            })

            # 2. TSTR Baseline (Pure Synthetic)
            if model_name in tstr_map:
                ts = tstr_map[model_name]
                f1_ts = ts["macro_f1"]
                bal_ts = ts["balanced_accuracy"]
                wf1_ts = ts["weighted_f1"]
                acc_ts = ts["accuracy"]
                rows.append({
                    "Model": model_name,
                    "Experiment": "TSTR (100% Synth Only)",
                    "Augmentation Level": "Pure Synth",
                    "Train Records": 5000,
                    "Synthetic Records": 5000,
                    "Macro F1": f1_ts,
                    "Balanced Accuracy": bal_ts,
                    "Accuracy": acc_ts,
                    "Weighted F1": wf1_ts,
                    "Abs Macro F1 Diff": round(f1_ts - f1_tr, 4),
                    "Rel Macro F1 Diff (%)": round(((f1_ts - f1_tr) / f1_tr) * 100, 2) if f1_tr != 0 else 0.0,
                    "Abs Bal Acc Diff": round(bal_ts - bal_tr, 4),
                    "Rel Bal Acc Diff (%)": round(((bal_ts - bal_tr) / bal_tr) * 100, 2) if bal_tr != 0 else 0.0,
                    "Abs Weighted F1 Diff": round(wf1_ts - wf1_tr, 4),
                    "Rel Weighted F1 Diff (%)": round(((wf1_ts - wf1_tr) / wf1_tr) * 100, 2) if wf1_tr != 0 else 0.0,
                })

            # 3. TSTR+R Augmentation Levels (25%, 50%, 100%)
            for level_label, runs in tstr_r_by_level.items():
                m_run = next((r for r in runs if r["model_name"] == model_name), None)
                if not m_run:
                    continue
                om = m_run["overall_metrics"]
                f1_m = om["macro_f1"]
                bal_m = om["balanced_accuracy"]
                wf1_m = om["weighted_f1"]
                acc_m = om["accuracy"]
                n_train = m_run.get("train_records", 38466)
                n_synth = n_train - 38466

                rows.append({
                    "Model": model_name,
                    "Experiment": f"TSTR+R ({level_label})",
                    "Augmentation Level": level_label,
                    "Train Records": n_train,
                    "Synthetic Records": n_synth,
                    "Macro F1": f1_m,
                    "Balanced Accuracy": bal_m,
                    "Accuracy": acc_m,
                    "Weighted F1": wf1_m,
                    "Abs Macro F1 Diff": round(f1_m - f1_tr, 4),
                    "Rel Macro F1 Diff (%)": round(((f1_m - f1_tr) / f1_tr) * 100, 2) if f1_tr != 0 else 0.0,
                    "Abs Bal Acc Diff": round(bal_m - bal_tr, 4),
                    "Rel Bal Acc Diff (%)": round(((bal_m - bal_tr) / bal_tr) * 100, 2) if bal_tr != 0 else 0.0,
                    "Abs Weighted F1 Diff": round(wf1_m - wf1_tr, 4),
                    "Rel Weighted F1 Diff (%)": round(((wf1_m - wf1_tr) / wf1_tr) * 100, 2) if wf1_tr != 0 else 0.0,
                })

        df_comp = pd.DataFrame(rows)
        return df_comp

    @staticmethod
    def generate_per_class_augmentation_summary(
        trtr_per_class: Dict[str, Dict[str, Any]],
        tstr_per_class: Dict[str, Dict[str, Any]],
        tstr_r_per_class_by_level: Dict[str, Dict[str, Dict[str, Any]]],
        categories: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """Tabulate per-class F1-scores across TRTR, TSTR, and all TSTR+R levels."""
        cats = categories or EXPECTED_LABEL_CATEGORIES
        rows = []
        for cat in cats:
            f1_tr = trtr_per_class.get(cat, {}).get("f1_score", 0.0)
            f1_ts = tstr_per_class.get(cat, {}).get("f1_score", 0.0)
            support = trtr_per_class.get(cat, {}).get("support", 0)

            row = {
                "Category": cat,
                "Support": support,
                "TRTR F1": f1_tr,
                "TSTR F1": f1_ts,
            }
            # Add TSTR+R levels
            for level_label, pc_dict in tstr_r_per_class_by_level.items():
                row[f"TSTR+R ({level_label}) F1"] = pc_dict.get(cat, {}).get("f1_score", 0.0)

            # Determine best performing paradigm for this category
            scores = {
                "TRTR": f1_tr,
                "TSTR": f1_ts,
            }
            for level_label, pc_dict in tstr_r_per_class_by_level.items():
                scores[f"TSTR+R {level_label}"] = pc_dict.get(cat, {}).get("f1_score", 0.0)

            best_paradigm = max(scores, key=scores.get)
            best_score = scores[best_paradigm]
            row["Best Paradigm"] = best_paradigm
            row["Best F1"] = best_score
            row["Delta vs TRTR"] = round(best_score - f1_tr, 4)

            rows.append(row)

        return pd.DataFrame(rows)

