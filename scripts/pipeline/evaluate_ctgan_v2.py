"""
Comprehensive CTGAN v2 Evaluation & Downstream Anomaly Detection Benchmarking Suite.

Evaluates:
1. Conditional generation (device-only, attack-only, combined, under-supported, unsupported)
2. Zero raw MAC/IP leakage across all generated outputs
3. Statistical similarity (KS, Wasserstein, JSD) vs held-out train & validation splits
4. Pairwise feature correlation Frobenius norm error
5. Domain-constraint validity (raw CTGAN v2 vs domain-repaired v2)
6. Diversity & memorization resistance (uniqueness, exact overlap, 1-NN Euclidean distance)
7. Controlled v1 vs v2 comparison
8. Multi-seed downstream anomaly-detection utility on UNTOUCHED held-out real test split
   (TRTR, v1 TSTR cross-corpus, v2 TSTR, and v2 TSTR+R augmentation + per-device & rare-class F1)
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from anomaly_detection.evaluator import AnomalyDetectionEvaluator
from anomaly_detection.feature_config import CANONICAL_MODEL_FEATURES
from anomaly_detection.model_factory import create_baseline_pipeline
from backend.services.ctgan_service import CTGANService
from synthetic_engine.ctgan_model import CTGANModel
from synthetic_engine.ctgan_v2_pipeline import (
    CTGAN_V2_ALL_COLUMNS,
    CTGAN_V2_DISCRETE_COLUMNS,
    conditional_sample_with_support_check,
)
from synthetic_engine.evaluation.correlation import FeatureCorrelationEvaluator
from synthetic_engine.evaluation.diversity import DiversityAndMemorizationEvaluator
from synthetic_engine.evaluation.statistical import StatisticalDistributionEvaluator
from synthetic_engine.evaluation.validity import SyntheticDataValidityEvaluator


EXT_DIR = ROOT / "datasets" / "external" / "device_labelled_iot_data"
SPLITS_DIR = EXT_DIR / "splits"
MODELS_DIR = ROOT / "models" / "ctgan"
V1_SYNTH_PARQUET = ROOT / "datasets" / "generated" / "ctgan_initial_sample_v1.parquet"
GEN_DIR = ROOT / "datasets" / "generated" / "ctgan_device_aware_v2"
REPORT_DIR = ROOT / "reports" / "ctgan_v2"

MAC_OR_IP_RE = re.compile(r"([0-9a-f]{2}(?::[0-9a-f]{2}){5}|(?:\d{1,3}\.){3}\d{1,3})", re.IGNORECASE)


def verify_no_mac_ip(df: pd.DataFrame, tag: str) -> bool:
    for col in df.columns:
        if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
            for val in df[col].dropna().astype(str).unique():
                if MAC_OR_IP_RE.search(val):
                    raise AssertionError(f"MAC/IP leaked in {tag}.{col}: {val}")
    return True


def _sample_df(synth, num_rows: int) -> pd.DataFrame:
    if isinstance(synth, CTGANModel):
        df = synth.sample(num_rows=num_rows)
    else:
        out = synth.sample(num_rows=num_rows)
        df = out["ciciot_device_v2"] if isinstance(out, dict) else out
    return df[CTGAN_V2_ALL_COLUMNS].copy()


def run_conditional_tests(synth, train_df: pd.DataFrame) -> Dict[str, Any]:
    results = {
        "device_category_tests": [],
        "device_id_tests": [],
        "attack_category_tests": [],
        "combined_tests": [],
        "unsupported_tests": [],
    }
    cond_pools: List[pd.DataFrame] = []

    # A. Device-category conditioning
    for dcat in sorted(train_df["device_category"].unique()):
        df_c, audit = conditional_sample_with_support_check(
            synth, train_df, {"device_category": dcat}, num_rows=200
        )
        if df_c is not None:
            verify_no_mac_ip(df_c, f"cond_dcat_{dcat}")
            cond_pools.append(df_c)
        results["device_category_tests"].append({"condition": {"device_category": dcat}, **audit})

    # B. Specific device_id conditioning (sample 6 diverse physical devices across categories)
    top_devs = (
        train_df.groupby(["device_category", "device_id"])
        .size()
        .reset_index(name="n")
        .sort_values(["device_category", "n"], ascending=[True, False])
        .groupby("device_category")
        .first()
        .reset_index()
    )
    for _, row in top_devs.iterrows():
        did = str(row["device_id"])
        df_c, audit = conditional_sample_with_support_check(
            synth, train_df, {"device_id": did}, num_rows=100
        )
        if df_c is not None:
            verify_no_mac_ip(df_c, f"cond_did_{did}")
            # Also check device_id -> device_category consistency!
            expected_cat = str(row["device_category"])
            cat_consistency = round(float((df_c["device_category"] == expected_cat).mean()), 4)
            audit["expected_device_category"] = expected_cat
            audit["device_category_consistency_rate"] = cat_consistency
        results["device_id_tests"].append({"condition": {"device_id": did}, **audit})

    # C. Attack-category conditioning (all 8 macro categories)
    for lcat in sorted(train_df["label_category"].unique()):
        df_c, audit = conditional_sample_with_support_check(
            synth, train_df, {"label_category": lcat}, num_rows=300
        )
        if df_c is not None:
            verify_no_mac_ip(df_c, f"cond_lcat_{lcat}")
            cond_pools.append(df_c)
        results["attack_category_tests"].append({"condition": {"label_category": lcat}, **audit})

    # D. Combined (device_category + label_category) well-supported + under-supported
    cross = pd.crosstab(train_df["device_category"], train_df["label_category"])
    well_pairs = []
    under_pairs = []
    zero_pairs = []
    for dcat in cross.index:
        for lcat in cross.columns:
            cnt = int(cross.loc[dcat, lcat])
            if cnt >= 50:
                well_pairs.append((dcat, lcat, cnt))
            elif 0 < cnt < 20:
                under_pairs.append((dcat, lcat, cnt))
            elif cnt == 0:
                zero_pairs.append((dcat, lcat, cnt))

    for dcat, lcat, cnt in well_pairs[:8]:
        df_c, audit = conditional_sample_with_support_check(
            synth, train_df, {"device_category": dcat, "label_category": lcat}, num_rows=100
        )
        if df_c is not None:
            verify_no_mac_ip(df_c, f"cond_comb_{dcat}_{lcat}")
        results["combined_tests"].append({"condition": {"device_category": dcat, "label_category": lcat}, **audit})

    for dcat, lcat, cnt in under_pairs[:4]:
        df_c, audit = conditional_sample_with_support_check(
            synth, train_df, {"device_category": dcat, "label_category": lcat}, num_rows=50
        )
        if df_c is not None:
            verify_no_mac_ip(df_c, f"cond_under_{dcat}_{lcat}")
        results["combined_tests"].append({"condition": {"device_category": dcat, "label_category": lcat}, **audit})

    # E. Unsupported / nonexistent combinations (must refuse cleanly, zero hallucination)
    fake_combos = [
        {"device_category": "QuantumRouter", "label_category": "DDoS"},
        {"device_id": "device_999", "label_category": "Benign"},
    ]
    for dcat, lcat, _ in zero_pairs[:2]:
        fake_combos.append({"device_category": dcat, "label_category": lcat})

    for combo in fake_combos:
        df_u, audit = conditional_sample_with_support_check(synth, train_df, combo, num_rows=50)
        assert df_u is None and audit["supported"] is False
        results["unsupported_tests"].append({"condition": combo, **audit})

    # Aggregate compliance summaries
    def _mean_rate(items: List[Dict[str, Any]]) -> float:
        rates = [x["compliance_rate"] for x in items if x.get("supported") and "compliance_rate" in x]
        return round(float(np.mean(rates)), 4) if rates else 0.0

    results["summary"] = {
        "device_category_mean_compliance": _mean_rate(results["device_category_tests"]),
        "device_id_mean_compliance": _mean_rate(results["device_id_tests"]),
        "device_id_category_consistency_mean": round(
            float(np.mean([x["device_category_consistency_rate"] for x in results["device_id_tests"] if "device_category_consistency_rate" in x])),
            4,
        ),
        "attack_category_mean_compliance": _mean_rate(results["attack_category_tests"]),
        "combined_supported_mean_compliance": _mean_rate(results["combined_tests"]),
        "unsupported_combinations_properly_rejected": sum(1 for x in results["unsupported_tests"] if not x["supported"]),
        "total_unsupported_tested": len(results["unsupported_tests"]),
    }

    if cond_pools:
        combined_cond_df = pd.concat(cond_pools, ignore_index=True)
        repaired_cond_df, _ = CTGANService._apply_domain_correction(combined_cond_df)
        repaired_cond_df.to_parquet(GEN_DIR / "ctgan_v2_conditional_repaired.parquet", index=False)

    return results


def build_balanced_synthetic_pool(synth, train_df: pd.DataFrame, target_per_macro: int = 800) -> pd.DataFrame:
    """Generate macro-balanced device-aware CTGAN v2 synthetic dataset for TSTR & TSTR+R utility."""
    chunks = []
    for lcat in sorted(train_df["label_category"].unique()):
        n_req = min(target_per_macro, max(400, int((train_df["label_category"] == lcat).sum())))
        # Generate target_per_macro across every class so rare classes get strong balanced representation
        n_req = target_per_macro
        df_c, audit = conditional_sample_with_support_check(
            synth, train_df, {"label_category": lcat}, num_rows=n_req, max_tries_per_batch=300
        )
        if df_c is not None and len(df_c) > 0:
            chunks.append(df_c)
    if not chunks:
        raise RuntimeError("Failed generating balanced synthetic pool.")
    return pd.concat(chunks, ignore_index=True)


def run_utility_benchmarks(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    synth_v2_raw: pd.DataFrame,
    synth_v2_rep: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Evaluate TRTR, v1 TSTR (if present), v2 TSTR (raw & repaired), and v2 TSTR+R
    strictly against the untouched real held-out test set across multiple seeds.
    """
    X_test = test_df[CANONICAL_MODEL_FEATURES].copy()
    y_test = test_df["label_category"].copy()
    X_train_real = train_df[CANONICAL_MODEL_FEATURES].copy()
    y_train_real = train_df["label_category"].copy()

    seeds = [42, 123, 456]
    models_to_run = ["random_forest", "extra_trees", "hist_gradient_boosting", "logistic_regression"]

    ev = AnomalyDetectionEvaluator(target_categories=sorted(y_test.unique()))

    def eval_multi_seed(X_tr: pd.DataFrame, y_tr: pd.Series, model_name: str, run_seeds: List[int]) -> Dict[str, Any]:
        seed_results = []
        last_preds = None
        for sd in run_seeds:
            clf = create_baseline_pipeline(model_name, random_state=sd)
            t_fit0 = time.perf_counter()
            clf.fit(X_tr, y_tr)
            fit_s = time.perf_counter() - t_fit0
            t_inf0 = time.perf_counter()
            preds = clf.predict(X_test)
            inf_s = time.perf_counter() - t_inf0
            probs = clf.predict_proba(X_test) if hasattr(clf, "predict_proba") else None
            res = ev.evaluate_predictions(
                y_true=y_test,
                y_pred=preds,
                y_prob=probs,
                model_name=model_name,
                fit_duration_seconds=fit_s,
                inference_duration_seconds=inf_s,
            )
            seed_results.append(res)
            if sd == 42:
                last_preds = preds
        accs = [r["overall_metrics"]["accuracy"] for r in seed_results]
        bal_accs = [r["overall_metrics"]["balanced_accuracy"] for r in seed_results]
        f1s = [r["overall_metrics"]["macro_f1"] for r in seed_results]
        wf1s = [r["overall_metrics"]["weighted_f1"] for r in seed_results]
        per_cls_seed42 = seed_results[0]["per_class_metrics"]

        # Per-device-category test accuracy/macro-F1 breakdown (using seed=42 model)
        per_device_cat = {}
        if last_preds is not None:
            from sklearn.metrics import accuracy_score, f1_score
            for dcat in sorted(test_df["device_category"].unique()):
                mask = (test_df["device_category"] == dcat).to_numpy()
                if mask.sum() == 0:
                    continue
                yt_d = y_test.iloc[mask]
                yp_d = last_preds[mask]
                per_device_cat[dcat] = {
                    "test_rows": int(mask.sum()),
                    "accuracy": round(float(accuracy_score(yt_d, yp_d)), 4),
                    "macro_f1": round(float(f1_score(yt_d, yp_d, average="macro", zero_division=0)), 4),
                }

        return {
            "seeds": run_seeds,
            "train_rows": int(len(X_tr)),
            "accuracy_mean": round(float(np.mean(accs)), 4),
            "accuracy_std": round(float(np.std(accs)), 4),
            "balanced_accuracy_mean": round(float(np.mean(bal_accs)), 4),
            "macro_f1_mean": round(float(np.mean(f1s)), 4),
            "macro_f1_std": round(float(np.std(f1s)), 4),
            "weighted_f1_mean": round(float(np.mean(wf1s)), 4),
            "roc_auc_macro_seed42": seed_results[0]["overall_metrics"].get("roc_auc_macro"),
            "per_class_seed42": per_cls_seed42,
            "per_device_category_seed42": per_device_cat,
        }

    regimes: Dict[str, Any] = {}

    # 1. TRTR Baseline
    regimes["TRTR"] = {}
    for m in models_to_run:
        regimes["TRTR"][m] = eval_multi_seed(X_train_real, y_train_real, m, seeds)

    # 2. v1 TSTR Cross-Corpus (if v1 sample file exists)
    if V1_SYNTH_PARQUET.exists():
        v1_df = pd.read_parquet(V1_SYNTH_PARQUET)
        if all(c in v1_df.columns for c in CANONICAL_MODEL_FEATURES) and "label_category" in v1_df.columns:
            regimes["TSTR_v1_cross_corpus"] = {}
            for m in ["random_forest", "extra_trees", "hist_gradient_boosting"]:
                regimes["TSTR_v1_cross_corpus"][m] = eval_multi_seed(
                    v1_df[CANONICAL_MODEL_FEATURES], v1_df["label_category"], m, [42]
                )

    # 3. v2 TSTR (raw & domain-repaired)
    regimes["TSTR_v2_raw"] = {}
    regimes["TSTR_v2_repaired"] = {}
    for m in models_to_run:
        regimes["TSTR_v2_raw"][m] = eval_multi_seed(
            synth_v2_raw[CANONICAL_MODEL_FEATURES], synth_v2_raw["label_category"], m, seeds
        )
        regimes["TSTR_v2_repaired"][m] = eval_multi_seed(
            synth_v2_rep[CANONICAL_MODEL_FEATURES], synth_v2_rep["label_category"], m, seeds
        )

    # 4. v2 TSTR+R Augmentation (25%, 50%, 100% synthetic added to real train + targeted rare-class balancing)
    for pct, ratio in [("25pct", 0.25), ("50pct", 0.50), ("100pct", 1.00)]:
        n_syn = max(100, int(round(len(X_train_real) * ratio)))
        if n_syn <= len(synth_v2_rep):
            syn_sub = synth_v2_rep.sample(n=n_syn, random_state=42)
        else:
            syn_sub = synth_v2_rep.sample(n=n_syn, replace=True, random_state=42)
        X_aug = pd.concat([X_train_real, syn_sub[CANONICAL_MODEL_FEATURES]], ignore_index=True)
        y_aug = pd.concat([y_train_real, syn_sub["label_category"]], ignore_index=True)

        key = f"TSTR_plus_R_v2_{pct}"
        regimes[key] = {}
        for m in models_to_run:
            regimes[key][m] = eval_multi_seed(X_aug, y_aug, m, seeds)

    # Targeted rare-class & device balancing: top up minority real classes toward median support
    cls_counts = y_train_real.value_counts()
    target_floor = int(max(600, cls_counts.median()))
    rare_chunks = []
    for cls_name, real_cnt in cls_counts.items():
        deficit = target_floor - int(real_cnt)
        if deficit > 0:
            pool_cls = synth_v2_rep[synth_v2_rep["label_category"] == cls_name]
            if len(pool_cls) > 0:
                rare_chunks.append(pool_cls.sample(n=deficit, replace=(deficit > len(pool_cls)), random_state=42))
    if rare_chunks:
        rare_syn = pd.concat(rare_chunks, ignore_index=True)
        X_bal_aug = pd.concat([X_train_real, rare_syn[CANONICAL_MODEL_FEATURES]], ignore_index=True)
        y_bal_aug = pd.concat([y_train_real, rare_syn["label_category"]], ignore_index=True)
        regimes["TSTR_plus_R_v2_rare_balanced"] = {}
        for m in models_to_run:
            regimes["TSTR_plus_R_v2_rare_balanced"][m] = eval_multi_seed(X_bal_aug, y_bal_aug, m, seeds)

    return {
        "held_out_test_rows": int(len(test_df)),
        "held_out_test_class_counts": {k: int(v) for k, v in y_test.value_counts().items()},
        "regimes": regimes,
    }


def main() -> None:
    GEN_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    train_df = pd.read_parquet(SPLITS_DIR / "train.parquet")
    val_df = pd.read_parquet(SPLITS_DIR / "val.parquet")
    test_df = pd.read_parquet(SPLITS_DIR / "test.parquet")

    # Load model cleanly through canonical CTGANModel.load (CPU-portable path)
    wrapper = CTGANModel.load(directory=MODELS_DIR, model_name="ctgan_device_aware_v2")
    synth = wrapper

    # 1. Generate unconditional pool matching validation/test-scale evaluation (6,000 rows)
    t0 = time.perf_counter()
    raw_pool = _sample_df(synth, num_rows=6000)
    verify_no_mac_ip(raw_pool, "v2_unconditional_raw")
    val_eval = SyntheticDataValidityEvaluator(tolerance=1e-2)
    raw_val_summary = val_eval.evaluate_all(raw_pool, expected_columns=CTGAN_V2_ALL_COLUMNS)
    rep_pool, repair_stats = CTGANService._apply_domain_correction(raw_pool)
    rep_val_summary = val_eval.evaluate_all(rep_pool, expected_columns=CTGAN_V2_ALL_COLUMNS)

    raw_pool.to_parquet(GEN_DIR / "ctgan_v2_unconditional_raw.parquet", index=False)
    rep_pool.to_parquet(GEN_DIR / "ctgan_v2_unconditional_repaired.parquet", index=False)
    rep_pool.head(1000).to_csv(GEN_DIR / "ctgan_v2_sample_preview.csv", index=False)

    # 2. Conditional generation matrix
    cond_report = run_conditional_tests(synth, train_df)
    (REPORT_DIR / "conditional_generation_report.json").write_text(
        json.dumps(cond_report, indent=2), encoding="utf-8"
    )

    # 3. Macro-balanced pool for TSTR / TSTR+R utility & quality audit
    bal_raw = build_balanced_synthetic_pool(synth, train_df, target_per_macro=1500)
    verify_no_mac_ip(bal_raw, "v2_balanced_raw")
    bal_rep, _ = CTGANService._apply_domain_correction(bal_raw)
    bal_rep.to_parquet(GEN_DIR / "ctgan_v2_balanced_repaired.parquet", index=False)

    # 4. Statistical similarity, correlation & diversity audit (Raw vs Repaired against Train & Val)
    stat_eval = StatisticalDistributionEvaluator()
    corr_eval = FeatureCorrelationEvaluator()
    div_eval = DiversityAndMemorizationEvaluator()

    stat_raw = stat_eval.evaluate_distributions(
        train_df, val_df, raw_pool, discrete_columns=CTGAN_V2_DISCRETE_COLUMNS
    )
    stat_rep = stat_eval.evaluate_distributions(
        train_df, val_df, rep_pool, discrete_columns=CTGAN_V2_DISCRETE_COLUMNS
    )
    corr_raw = corr_eval.evaluate_all(val_df, raw_pool)
    corr_rep = corr_eval.evaluate_all(val_df, rep_pool)
    div_raw = div_eval.evaluate_all(train_df, raw_pool)
    div_rep = div_eval.evaluate_all(train_df, rep_pool)

    # Per-device-category statistical KS check between real val and v2 repaired
    per_device_stat = {}
    for dcat in sorted(val_df["device_category"].unique()):
        real_sub = val_df[val_df["device_category"] == dcat]
        syn_sub = rep_pool[rep_pool["device_category"] == dcat]
        if len(real_sub) >= 10 and len(syn_sub) >= 10:
            s_sub = stat_eval.evaluate_distributions(
                train_df[train_df["device_category"] == dcat],
                real_sub,
                syn_sub,
                discrete_columns=CTGAN_V2_DISCRETE_COLUMNS,
            )
            per_device_stat[dcat] = {
                "real_val_rows": int(len(real_sub)),
                "synth_rows": int(len(syn_sub)),
                **s_sub["summary_metrics"],
            }

    def _summarize_validity(vdict: Dict[str, Any]) -> Dict[str, Any]:
        schema_ok = bool(vdict.get("schema_validity", {}).get("is_valid", False))
        num_v = vdict.get("numerical_validity", {})
        stat_v = vdict.get("statistical_invariants", {})
        prot_v = vdict.get("protocol_consistency", {})
        lbl_v = vdict.get("label_consistency", {})
        all_passed = bool(
            schema_ok
            and not num_v.get("has_nulls", True)
            and not num_v.get("has_infs", True)
            and not num_v.get("has_negative_violations", True)
            and stat_v.get("min_le_avg_le_max", {}).get("total_violations", 1) == 0
            and stat_v.get("std_sqrt_variance", {}).get("violation_count", 1) == 0
            and stat_v.get("avg_tot_sum_ratio", {}).get("violation_count", 1) == 0
            and prot_v.get("protocol_type_name_mismatch", {}).get("count", 1) == 0
            and prot_v.get("simultaneous_tcp_and_udp", {}).get("count", 1) == 0
            and lbl_v.get("category_mismatches", {}).get("count", 1) == 0
            and lbl_v.get("total_is_attack_violations", {}).get("count", 1) == 0
        )
        return {
            "all_passed": all_passed,
            "schema_valid": schema_ok,
            "negative_violations": sum(num_v.get("negative_violations", {}).values()) if isinstance(num_v.get("negative_violations"), dict) else 0,
            "min_le_avg_le_max_violations": stat_v.get("min_le_avg_le_max", {}).get("total_violations", 0),
            "std_sqrt_variance_violations": stat_v.get("std_sqrt_variance", {}).get("violation_count", 0),
            "avg_tot_sum_violations": stat_v.get("avg_tot_sum_ratio", {}).get("violation_count", 0),
            "protocol_mismatch_count": prot_v.get("protocol_type_name_mismatch", {}).get("count", 0),
            "simultaneous_tcp_udp_count": prot_v.get("simultaneous_tcp_and_udp", {}).get("count", 0),
            "label_category_mismatch_count": lbl_v.get("category_mismatches", {}).get("count", 0),
            "is_attack_violation_count": lbl_v.get("total_is_attack_violations", {}).get("count", 0),
        }

    raw_val_compact = _summarize_validity(raw_val_summary)
    rep_val_compact = _summarize_validity(rep_val_summary)

    quality_report = {
        "evaluation_elapsed_s": round(time.perf_counter() - t0, 2),
        "sample_rows": int(len(raw_pool)),
        "zero_mac_ip_leakage_verified": True,
        "repair_counts": repair_stats,
        "domain_validity_raw_summary": raw_val_compact,
        "domain_validity_repaired_summary": rep_val_compact,
        "domain_validity_raw": raw_val_summary,
        "domain_validity_repaired": rep_val_summary,
        "statistical_similarity_raw": stat_raw["summary_metrics"],
        "statistical_similarity_repaired": stat_rep["summary_metrics"],
        "correlation_raw": corr_raw,
        "correlation_repaired": corr_rep,
        "diversity_raw": div_raw["summary"],
        "diversity_repaired": div_rep["summary"],
        "per_device_category_similarity_repaired": per_device_stat,
    }
    (REPORT_DIR / "quality_report.json").write_text(json.dumps(quality_report, indent=2), encoding="utf-8")

    # 5. Controlled v1 vs v2 Comparison Report
    v1_meta = json.loads((MODELS_DIR / "v1" / "ctgan_full_v1_metadata.json").read_text(encoding="utf-8"))
    v2_meta = json.loads((MODELS_DIR / "v2" / "ctgan_device_aware_v2_metadata.json").read_text(encoding="utf-8"))
    v1_stat_json = ROOT / "reports" / "phase6" / "statistical_similarity_report.json"
    v1_stat = json.loads(v1_stat_json.read_text(encoding="utf-8")) if v1_stat_json.exists() else {}
    v1_div_json = ROOT / "reports" / "phase6" / "diversity_report.json"
    v1_div = json.loads(v1_div_json.read_text(encoding="utf-8")) if v1_div_json.exists() else {}

    v1_tm = v1_meta.get("training_metadata", v1_meta)
    v2_tm = v2_meta.get("training_metadata", v2_meta)
    v1_vs_v2 = {
        "note": "v1 historical benchmark was evaluated on anonymized ciciot2023_preprocessed_sample (no device labels); v2 was trained & evaluated on MAC-attributed CICIoT2023 PCAPNG windows.",
        "v1": {
            "epochs": v1_meta.get("config", {}).get("epochs"),
            "cuda": v1_meta.get("config", {}).get("cuda"),
            "training_seconds": v1_tm.get("elapsed_seconds", 6030.28),
            "discrete_columns": len(v1_meta.get("discrete_columns", [])),
            "dim_cond_vec": v2_tm.get("encoding_comparison", {}).get("v1_measured_checkpoint", {}).get("v1_actual_dim_cond_vec"),
            "device_aware_conditioning": False,
            "statistical_summary_phase6": v1_stat.get("summary_metrics", {}),
            "diversity_phase6": v1_div.get("summary", {}),
        },
        "v2": {
            "epochs": v2_meta.get("config", {}).get("epochs"),
            "enable_gpu": v2_meta.get("config", {}).get("cuda"),
            "training_seconds": v2_tm.get("elapsed_seconds"),
            "discrete_columns": len(v2_meta.get("discrete_columns", [])),
            "dim_cond_vec": v2_tm.get("actual_dim_cond_vec"),
            "device_aware_conditioning": True,
            "statistical_summary_repaired": stat_rep["summary_metrics"],
            "statistical_summary_raw": stat_raw["summary_metrics"],
            "diversity_repaired": div_rep["summary"],
            "domain_validity_raw_summary": raw_val_compact,
            "domain_validity_repaired_summary": rep_val_compact,
        },
    }
    (REPORT_DIR / "v1_vs_v2_comparison_report.json").write_text(json.dumps(v1_vs_v2, indent=2), encoding="utf-8")

    # 6. Downstream Anomaly-Detection Utility Benchmarks on UNTOUCHED Held-Out Test Split
    utility_report = run_utility_benchmarks(train_df, test_df, bal_raw, bal_rep)
    (REPORT_DIR / "anomaly_utility_report.json").write_text(json.dumps(utility_report, indent=2), encoding="utf-8")

    print("\n[EVAL DONE] Saved conditional, quality, v1-vs-v2, and anomaly_utility reports to reports/ctgan_v2/")
    print("Raw validity:", raw_val_compact, "| Repaired validity:", rep_val_compact)
    print("RF TRTR F1:", utility_report["regimes"]["TRTR"]["random_forest"]["macro_f1_mean"],
          "| RF TSTR_v2_repaired F1:", utility_report["regimes"]["TSTR_v2_repaired"]["random_forest"]["macro_f1_mean"],
          "| RF TSTR+R(25%) F1:", utility_report["regimes"]["TSTR_plus_R_v2_25pct"]["random_forest"]["macro_f1_mean"])


if __name__ == "__main__":
    main()
