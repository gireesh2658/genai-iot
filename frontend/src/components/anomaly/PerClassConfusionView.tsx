"use client";

import React, { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AnomalyModelDetail } from "@/lib/types";
import { fmtClassifierName, fmtMetric } from "@/lib/formatters";
import { ChartContainer } from "@/components/ui/ChartContainer";
import { EmptyState } from "@/components/ui/StateViews";
import { StatusIndicator } from "@/components/ui/StatusIndicator";

const CLASSES = [
  "Benign",
  "DDoS",
  "DoS",
  "Mirai",
  "Reconnaissance",
  "Spoofing",
  "Web-based",
  "Brute Force",
];

export function PerClassConfusionView({
  modelDetail,
}: {
  modelDetail: AnomalyModelDetail | null;
}) {
  const [normMode, setNormMode] = useState<"count" | "pct">("count");
  const [cellInfo, setCellInfo] = useState<{
    trueCls: string;
    predCls: string;
    count: number;
    pct: number;
  } | null>(null);

  if (!modelDetail) {
    return (
      <section className="studio-panel p-6">
        <EmptyState
          title="Select a Classifier Above"
          description="Pick any TRTR, TSTR, TSTR+R, or custom detector row in the leaderboard to inspect per-class scores and its 8×8 confusion matrix."
        />
      </section>
    );
  }

  const perClass = modelDetail.per_class_metrics || {};
  const perClassChart = CLASSES.map((cls) => ({
    name: cls,
    Precision: perClass[cls]?.precision ?? 0,
    Recall: perClass[cls]?.recall ?? 0,
    F1: perClass[cls]?.f1_score ?? 0,
    support: perClass[cls]?.support ?? 0,
  }));

  const cm = modelDetail.confusion_matrix || {};
  const hasCm = Object.keys(cm).length > 0;
  const om = modelDetail.overall_metrics || {};

  return (
    <div className="space-y-6">
      {/* Model Telemetry Strip */}
      <section className="studio-panel p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="break-all font-mono text-base font-bold text-ink">{modelDetail.model_id}</span>
              <StatusIndicator
                tone={modelDetail.is_custom ? "synthetic" : "info"}
                label={modelDetail.is_custom ? "Custom Model" : "Phase 7 Historical Benchmark"}
              />
            </div>
            <p className="mt-1 text-xs text-ink-secondary tabular-nums">
              {fmtClassifierName(modelDetail.classifier_name)} · {modelDetail.experiment_type} ·{" "}
              {modelDetail.train_records?.toLocaleString() ?? "--"} training /{" "}
              {modelDetail.val_records?.toLocaleString() ?? "--"} held-out real validation flows ·{" "}
              {modelDetail.features_count} features
            </p>
          </div>

          <div className="flex flex-wrap gap-2 text-xs font-bold tabular-nums">
            <span className="rounded-lg border border-[#C4DBFA] bg-brand-tint px-3 py-1.5 text-brand">
              Macro F1: {fmtMetric(om.macro_f1)}
            </span>
            <span className="rounded-lg border border-[#BBE5DF] bg-[#E7F7F5] px-3 py-1.5 text-signal">
              Balanced Acc: {fmtMetric(om.balanced_accuracy)}
            </span>
            {typeof om.roc_auc_macro === "number" && (
              <span className="rounded-lg border border-[#D6D0F5] bg-[#F0EEFC] px-3 py-1.5 text-signal-lavender">
                OvR ROC-AUC: {fmtMetric(om.roc_auc_macro)}
              </span>
            )}
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
        {/* Per-Class Performance Bar & Gap Table */}
        <ChartContainer
          title="Per-Class Detection Performance (8 Macro Categories)"
          subtitle="Explicitly inspects rare attack behavior (e.g., Web-based support 5, Brute Force support 3)"
          unit="Score [0–1]"
          className="xl:col-span-6"
        >
          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={perClassChart} margin={{ top: 8, right: 8, left: -12, bottom: 20 }}>
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
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="Precision" fill="#6459BA" radius={[3, 3, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="Recall" fill="#17857B" radius={[3, 3, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="F1" fill="#2A67B1" radius={[3, 3, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-4 overflow-x-auto rounded-xl border border-hairline">
            <table className="w-full text-left text-xs tabular-nums">
              <thead className="bg-well/75 text-[11px] font-semibold uppercase tracking-wide text-ink-secondary">
                <tr>
                  <th className="px-3 py-2">Category</th>
                  <th className="px-3 py-2 text-right">Support</th>
                  <th className="px-3 py-2 text-right">Precision</th>
                  <th className="px-3 py-2 text-right">Recall</th>
                  <th className="px-3 py-2 text-right">F1</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline bg-surface">
                {perClassChart.map((r) => (
                  <tr key={r.name}>
                    <td className="px-3 py-1.5 font-semibold text-ink">{r.name}</td>
                    <td className="px-3 py-1.5 text-right font-mono text-ink-secondary">
                      {r.support}
                    </td>
                    <td className="px-3 py-1.5 text-right font-mono text-ink">
                      {r.Precision.toFixed(4)}
                    </td>
                    <td className="px-3 py-1.5 text-right font-mono text-ink">
                      {r.Recall.toFixed(4)}
                    </td>
                    <td
                      className={`px-3 py-1.5 text-right font-mono font-bold ${
                        r.F1 === 0 ? "text-[#BF4840]" : r.F1 >= 0.85 ? "text-[#1A7D5E]" : "text-brand"
                      }`}
                    >
                      {r.F1.toFixed(4)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </ChartContainer>

        {/* Interactive 8x8 Sequential Confusion Matrix */}
        <section className="studio-panel min-w-0 space-y-4 p-5 xl:col-span-6">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h3 className="text-sm font-bold text-ink">
                8×8 Validation Confusion Matrix Heatmap
              </h3>
              <p className="mt-0.5 text-xs text-ink-secondary">
                Rows = True Class · Columns = Predicted Class. Darker intensity = higher row share.
              </p>
            </div>

            <div className="inline-flex rounded-lg border border-hairline bg-well p-0.5 text-xs font-semibold">
              <button
                type="button"
                onClick={() => setNormMode("count")}
                className={`rounded-md px-2.5 py-1 ${
                  normMode === "count" ? "bg-surface text-brand shadow-sm" : "text-ink-secondary"
                }`}
              >
                Counts
              </button>
              <button
                type="button"
                onClick={() => setNormMode("pct")}
                className={`rounded-md px-2.5 py-1 ${
                  normMode === "pct" ? "bg-surface text-brand shadow-sm" : "text-ink-secondary"
                }`}
              >
                Row %
              </button>
            </div>
          </div>

          <div className="rounded-xl border border-hairline bg-well/65 px-3.5 py-2 font-mono text-xs text-ink">
            {cellInfo ? (
              <span>
                True: <strong>{cellInfo.trueCls}</strong> → Pred:{" "}
                <strong>{cellInfo.predCls}</strong> | Count:{" "}
                <strong className="text-brand">{cellInfo.count}</strong> ({cellInfo.pct.toFixed(1)}% of true row)
              </span>
            ) : (
              <span className="text-ink-secondary">Hover or focus any cell to inspect exact classification breakdown.</span>
            )}
          </div>

          {hasCm ? (
            <div className="overflow-x-auto rounded-xl border border-hairline">
              <table className="w-full border-collapse text-center text-[11px] tabular-nums">
                <thead>
                  <tr className="bg-well/80 text-ink-secondary">
                    <th className="px-2 py-2 text-left font-bold">True \ Pred</th>
                    {CLASSES.map((c) => (
                      <th key={c} title={c} className="px-1.5 py-2 font-semibold">
                        {c.slice(0, 6)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {CLASSES.map((trueCls) => {
                    const rowTotal = CLASSES.reduce(
                      (s, pred) => s + Number(cm[`pred_${pred}`]?.[`true_${trueCls}`] ?? 0),
                      0
                    );
                    return (
                      <tr key={trueCls}>
                        <th
                          scope="row"
                          className="border-t border-hairline bg-well/60 px-2 py-1.5 text-left font-semibold text-ink"
                        >
                          {trueCls}
                        </th>
                        {CLASSES.map((predCls) => {
                          const val = Number(cm[`pred_${predCls}`]?.[`true_${trueCls}`] ?? 0);
                          const pct = rowTotal > 0 ? (val / rowTotal) * 100 : 0;
                          const ratio = rowTotal > 0 ? val / rowTotal : 0;
                          const diag = trueCls === predCls;
                          const bg = diag
                            ? `rgba(42, 103, 177, ${0.12 + ratio * 0.72})`
                            : val > 0
                            ? `rgba(217, 138, 43, ${0.08 + ratio * 0.65})`
                            : "#FFFFFF";
                          const fg = (diag && ratio > 0.55) || (!diag && ratio > 0.6) ? "#FFFFFF" : "#2B3748";
                          return (
                            <td
                              key={predCls}
                              style={{ backgroundColor: bg, color: fg }}
                              className="border-t border-l border-hairline p-0"
                            >
                              <button
                                type="button"
                                onMouseEnter={() => setCellInfo({ trueCls, predCls, count: val, pct })}
                                onFocus={() => setCellInfo({ trueCls, predCls, count: val, pct })}
                                aria-label={`True ${trueCls}, Predicted ${predCls}: ${val} flows (${pct.toFixed(1)} percent)`}
                                className="block h-9 w-full px-1 font-mono text-[11px] font-semibold hover:ring-1 hover:ring-inset hover:ring-ink"
                              >
                                {normMode === "count" ? val : `${pct.toFixed(0)}%`}
                              </button>
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              title="No Confusion Matrix Available"
              description="Confusion matrix JSON was not found for this model."
            />
          )}
        </section>
      </div>
    </div>
  );
}
