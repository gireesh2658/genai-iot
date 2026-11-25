"use client";

import React, { useEffect, useState } from "react";
import { BrainCircuit } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/lib/api";
import { AnomalyTrainResponse } from "@/lib/types";
import { fmtMetric, fmtSignedDelta } from "@/lib/formatters";
import { PrimaryButton } from "@/components/ui/Button";
import { ChartContainer } from "@/components/ui/ChartContainer";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { StatusIndicator } from "@/components/ui/StatusIndicator";
import { useToast } from "@/components/ui/ToastProvider";

const CLASSES = [
  "Benign",
  "Brute Force",
  "DDoS",
  "DoS",
  "Mirai",
  "Reconnaissance",
  "Spoofing",
  "Web-based",
];

export function CustomDetectorTrainer({
  synthDatasets,
  initialDataset,
  onTrained,
}: {
  synthDatasets: string[];
  initialDataset: string | null;
  onTrained: (res: AnomalyTrainResponse) => void;
}) {
  const { pushToast } = useToast();

  const [clf, setClf] = useState("random_forest");
  const [exp, setExp] = useState<"TSTR+R" | "TSTR" | "TRTR">("TSTR+R");
  const [synthId, setSynthId] = useState(
    initialDataset || "ctgan_initial_sample_v1_domain_corrected"
  );
  const [fraction, setFraction] = useState(0.25);
  const [balanceMinority, setBalanceMinority] = useState(true);
  const [tag, setTag] = useState("");
  const [busy, setBusy] = useState(false);
  const [trainOut, setTrainOut] = useState<AnomalyTrainResponse | null>(null);

  useEffect(() => {
    if (initialDataset && synthDatasets.includes(initialDataset)) {
      setSynthId(initialDataset);
    }
  }, [initialDataset, synthDatasets]);

  const handleTrain = async () => {
    setBusy(true);
    try {
      const res = await api.trainAnomalyModel({
        classifier_name: clf,
        experiment_type: exp,
        synthetic_dataset_id: exp === "TRTR" ? null : synthId,
        augmentation_fraction: fraction,
        balance_minority_classes: balanceMinority,
        model_tag: tag.trim() || null,
        random_seed: 42,
      });
      setTrainOut(res);
      onTrained(res);
      pushToast(
        "success",
        `Trained '${res.model_id}'`,
        `Macro F1: ${fmtMetric(res.overall_metrics?.macro_f1)} in ${res.fit_duration_seconds}s`
      );
    } catch (e: any) {
      pushToast("error", "Detector training failed", e.message);
    } finally {
      setBusy(false);
    }
  };

  const classBars = trainOut?.per_class_metrics
    ? CLASSES.map((c) => ({
        name: c,
        "Validation F1": trainOut.per_class_metrics[c]?.f1_score ?? 0,
      }))
    : [];

  return (
    <div className="space-y-6">
      <section className="studio-panel space-y-5 p-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="flex items-center gap-2 text-base font-bold text-ink">
              <BrainCircuit className="h-5 w-5 text-brand" aria-hidden="true" />
              Train Custom Anomaly Detector
              <InfoTooltip term="TRTR" />
            </h2>
            <p className="mt-0.5 text-xs text-ink-secondary">
              Fits strictly on training splits using the 38 numerical network features (never touches the 9,616 held-out validation rows before evaluation).
            </p>
          </div>
          <StatusIndicator tone="info" label="Recommended Mix: TSTR+R (25%)" />
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div>
            <label htmlFor="clf-family" className="mb-1 block text-xs font-bold text-ink-secondary">
              Classifier Family
            </label>
            <select
              id="clf-family"
              value={clf}
              onChange={(e) => setClf(e.target.value)}
              className="studio-input"
            >
              <option value="random_forest">Random Forest</option>
              <option value="hist_gradient_boosting">HistGradientBoosting</option>
              <option value="extra_trees">Extra Trees</option>
              <option value="logistic_regression">Logistic Regression (Scaled)</option>
            </select>
          </div>

          <div>
            <label htmlFor="exp-paradigm" className="mb-1 block text-xs font-bold text-ink-secondary">
              Experiment Paradigm
            </label>
            <select
              id="exp-paradigm"
              value={exp}
              onChange={(e) => setExp(e.target.value as any)}
              className="studio-input"
            >
              <option value="TSTR+R">TSTR+R (Real + Synthetic Mix)</option>
              <option value="TSTR">TSTR (Pure Synthetic Only)</option>
              <option value="TRTR">TRTR (Real Baseline Only)</option>
            </select>
          </div>

          <div>
            <label htmlFor="custom-clf-tag" className="mb-1 block text-xs font-bold text-ink-secondary">
              Custom Identifier Suffix (optional)
            </label>
            <input
              id="custom-clf-tag"
              value={tag}
              onChange={(e) => setTag(e.target.value)}
              placeholder="e.g. rf_ctgan_25"
              className="studio-input font-mono text-xs"
            />
          </div>
        </div>

        {exp !== "TRTR" && (
          <div className="studio-well grid grid-cols-1 gap-4 p-4 md:grid-cols-3">
            <div>
              <label htmlFor="train-synth-src" className="mb-1 block text-xs font-bold text-ink-secondary">
                Synthetic Pool (`datasets/generated/`)
              </label>
              <select
                id="train-synth-src"
                value={synthId}
                onChange={(e) => setSynthId(e.target.value)}
                className="studio-input font-mono text-xs"
              >
                {synthDatasets.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <div className="mb-1 flex items-center justify-between text-xs font-bold text-ink-secondary">
                <span>Synthetic Pool Fraction</span>
                <span className="font-mono text-brand tabular-nums">
                  {Math.round(fraction * 100)}%
                </span>
              </div>
              <div className="flex gap-1.5">
                {[0.1, 0.25, 0.5, 1.0].map((v) => (
                  <button
                    key={v}
                    type="button"
                    onClick={() => setFraction(v)}
                    className={`min-h-[36px] flex-1 rounded-lg border text-xs font-semibold transition ${
                      Math.abs(fraction - v) < 0.01
                        ? "border-brand bg-brand-tint text-brand"
                        : "border-hairline bg-surface text-ink-secondary hover:border-[#B8C4BE]"
                    }`}
                  >
                    {Math.round(v * 100)}%
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center">
              <label className="flex cursor-pointer items-center gap-2 text-xs font-semibold text-ink">
                <input
                  type="checkbox"
                  checked={balanceMinority}
                  onChange={(e) => setBalanceMinority(e.target.checked)}
                />
                Prioritize minority attack classes in TSTR+R sampling
              </label>
            </div>
          </div>
        )}

        <PrimaryButton type="button" loading={busy} onClick={handleTrain}>
          {busy ? "Fitting & Benchmarking..." : "Train & Benchmark on Held-Out Validation"}
        </PrimaryButton>
      </section>

      {trainOut && (
        <section className="studio-panel space-y-5 p-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 className="font-mono text-sm font-bold text-ink">{trainOut.model_id}</h3>
              <p className="text-xs text-ink-secondary tabular-nums">
                Fit duration: {trainOut.fit_duration_seconds}s · Training mix:{" "}
                {trainOut.train_records.toLocaleString()} total ({trainOut.synthetic_records_used.toLocaleString()} synthetic)
              </p>
            </div>
            <StatusIndicator tone="success" label="Live Evaluation Completed" />
          </div>

          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div className="studio-well p-3.5">
              <span className="text-[11px] font-bold text-ink-secondary">Validation Macro F1</span>
              <div className="mt-1 font-mono text-xl font-bold text-brand tabular-nums">
                {fmtMetric(trainOut.overall_metrics?.macro_f1)}
              </div>
              <span className="font-mono text-xs font-semibold text-ink-secondary tabular-nums">
                {fmtSignedDelta(trainOut.macro_f1_delta_vs_trtr)} vs TRTR
              </span>
            </div>
            <div className="studio-well p-3.5">
              <span className="text-[11px] font-bold text-ink-secondary">Balanced Accuracy</span>
              <div className="mt-1 font-mono text-xl font-bold text-ink tabular-nums">
                {fmtMetric(trainOut.overall_metrics?.balanced_accuracy)}
              </div>
            </div>
            <div className="studio-well p-3.5">
              <span className="text-[11px] font-bold text-ink-secondary">OvR ROC-AUC</span>
              <div className="mt-1 font-mono text-xl font-bold text-signal tabular-nums">
                {fmtMetric(trainOut.overall_metrics?.roc_auc_macro)}
              </div>
            </div>
            <div className="studio-well p-3.5">
              <span className="text-[11px] font-bold text-ink-secondary">TRTR Baseline F1</span>
              <div className="mt-1 font-mono text-xl font-bold text-ink-secondary tabular-nums">
                {fmtMetric(trainOut.trtr_baseline_macro_f1)}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <ChartContainer title="Trained Model Per-Class F1" unit="F1 [0–1]">
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={classBars} margin={{ top: 8, right: 8, left: -12, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E5EAE7" />
                    <XAxis
                      dataKey="name"
                      tick={{ fill: "#556578", fontSize: 10 }}
                      angle={-16}
                      textAnchor="end"
                      height={44}
                    />
                    <YAxis domain={[0, 1]} tick={{ fill: "#556578", fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#FFFFFF",
                        borderColor: "#E5EAE7",
                        borderRadius: 10,
                        fontSize: 12,
                      }}
                    />
                    <Bar dataKey="Validation F1" fill="#2A67B1" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartContainer>

            <div className="grid grid-cols-2 gap-2.5 self-start">
              {Object.entries(trainOut.per_class_f1_deltas_vs_trtr || {}).map(([cls, delta]) => (
                <div key={cls} className="studio-well p-3 text-xs tabular-nums">
                  <div className="font-bold text-ink">{cls}</div>
                  <div className="mt-1 font-mono text-sm font-bold text-ink">
                    F1 {fmtMetric(trainOut.per_class_metrics?.[cls]?.f1_score)}
                  </div>
                  <div
                    className={`font-mono text-[11px] font-bold ${
                      delta > 0 ? "text-[#1A7D5E]" : delta < 0 ? "text-[#BF4840]" : "text-ink-muted"
                    }`}
                  >
                    {fmtSignedDelta(delta)} vs TRTR
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
