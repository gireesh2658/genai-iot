"use client";

import React, { useMemo, useState } from "react";
import { Trash2 } from "lucide-react";
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
import { AnomalyModelSummary, ExperimentComparisonRecord } from "@/lib/types";
import { fmtClassifierName, fmtMetric, fmtSignedDelta } from "@/lib/formatters";
import { IconButton } from "@/components/ui/Button";
import { ChartContainer } from "@/components/ui/ChartContainer";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { StatusIndicator } from "@/components/ui/StatusIndicator";

export function LeaderboardMatrix({
  models,
  selectedModelId,
  comparisons,
  onSelectModel,
  onRequestDeleteModel,
}: {
  models: AnomalyModelSummary[];
  selectedModelId: string;
  comparisons: ExperimentComparisonRecord[];
  onSelectModel: (id: string) => void;
  onRequestDeleteModel: (id: string) => void;
}) {
  const [expFilter, setExpFilter] = useState<"ALL" | "TRTR" | "TSTR" | "TSTR+R">("ALL");

  const sortedModels = useMemo(() => {
    const base = [...models].sort((a, b) => (b.macro_f1 ?? -1) - (a.macro_f1 ?? -1));
    if (expFilter === "ALL") return base;
    return base.filter((m) => m.experiment_type === expFilter);
  }, [models, expFilter]);

  const paradigmBars = useMemo(() => {
    const grouped: Record<string, any> = {};
    for (const r of comparisons) {
      const m = r.Model;
      if (!grouped[m]) grouped[m] = { classifier: fmtClassifierName(m) };
      if (r.Experiment.startsWith("TRTR")) grouped[m]["TRTR"] = r["Macro F1"];
      else if (r.Experiment.startsWith("TSTR (")) grouped[m]["TSTR"] = r["Macro F1"];
      else if (r.Experiment === "TSTR+R (25%)") grouped[m]["TSTR+R (25%)"] = r["Macro F1"];
      else if (r.Experiment === "TSTR+R (100%)") grouped[m]["TSTR+R (100%)"] = r["Macro F1"];
    }
    return Object.values(grouped);
  }, [comparisons]);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
        {/* Selectable Model Leaderboard */}
        <section className="studio-panel flex min-w-0 flex-col p-5 xl:col-span-5">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="text-sm font-bold text-ink">
                Model Leaderboard ({sortedModels.length})
              </h2>
              <p className="text-[11px] text-ink-secondary">
                Select any model to inspect per-class F1 &amp; confusion matrix.
              </p>
            </div>
            <div className="inline-flex rounded-lg border border-hairline bg-well p-0.5 text-[11px] font-bold">
              {(["ALL", "TRTR", "TSTR", "TSTR+R"] as const).map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setExpFilter(f)}
                  className={`rounded-md px-2 py-1 ${
                    expFilter === f ? "bg-surface text-brand shadow-sm" : "text-ink-secondary"
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          <div className="max-h-[420px] space-y-2 overflow-y-auto pr-1">
            {sortedModels.map((m, idx) => {
              const active = m.model_id === selectedModelId;
              return (
                <div
                  key={m.model_id}
                  className={`flex items-center justify-between gap-2 rounded-xl border p-3 transition ${
                    active
                      ? "border-brand bg-brand-tint/60"
                      : "border-hairline bg-surface hover:border-[#B8C4BE]"
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => onSelectModel(m.model_id)}
                    className="min-w-0 flex-1 text-left"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded bg-well px-1.5 py-0.5 font-mono text-[10px] font-bold text-ink-secondary">
                        #{idx + 1}
                      </span>
                      <span className="truncate font-mono text-xs font-bold text-ink">
                        {m.model_id}
                      </span>
                      <StatusIndicator
                        tone={m.is_custom ? "synthetic" : "info"}
                        label={m.is_custom ? "Custom Live" : "Historical Benchmark"}
                      />
                    </div>
                    <div className="mt-1.5 flex flex-wrap gap-3 text-[11px] text-ink-secondary tabular-nums">
                      <span className="font-semibold text-ink">{m.experiment_type}</span>
                      <span>
                        Macro F1:{" "}
                        <strong className="font-mono text-brand">
                          {fmtMetric(m.macro_f1)}
                        </strong>
                      </span>
                      <span>
                        Bal Acc:{" "}
                        <strong className="font-mono text-ink">
                          {fmtMetric(m.balanced_accuracy)}
                        </strong>
                      </span>
                    </div>
                  </button>

                  {m.is_custom && (
                    <IconButton
                      label={`Delete custom model ${m.model_id}`}
                      onClick={() => onRequestDeleteModel(m.model_id)}
                      className="hover:border-[#F2C3BF] hover:bg-[#FDECEC] hover:text-[#BF4840]"
                    >
                      <Trash2 className="h-4 w-4" />
                    </IconButton>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        {/* Cross-Paradigm Visual Comparison */}
        <ChartContainer
          title={
            <>
              Augmentation Experiment Comparison (TRTR vs TSTR vs TSTR+R)
              <InfoTooltip term="TSTR+R" />
            </>
          }
          subtitle="Historical Phase 7 Macro F1 scores evaluated strictly on 9,616 held-out real CICIoT2023 flows"
          unit="Macro F1 [0–1]"
          isEmpty={paradigmBars.length === 0}
          className="xl:col-span-7"
        >
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={paradigmBars} margin={{ top: 8, right: 12, left: -12, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5EAE7" />
                <XAxis dataKey="classifier" tick={{ fill: "#556578", fontSize: 11 }} />
                <YAxis domain={[0, 0.8]} tick={{ fill: "#556578", fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#FFFFFF",
                    borderColor: "#E5EAE7",
                    borderRadius: 10,
                    fontSize: 12,
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="TRTR" fill="#8B99AA" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="TSTR" fill="#E98278" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="TSTR+R (25%)" fill="#2A67B1" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="TSTR+R (100%)" fill="#17857B" radius={[4, 4, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-3 text-[11px] text-ink-secondary">
            Notice: Synthetic augmentation helps <strong className="text-ink">Random Forest</strong> and <strong className="text-ink">HistGradientBoosting</strong> at 25%, whereas Extra Trees &amp; Logistic Regression slightly decline vs TRTR baselines.
          </p>
        </ChartContainer>
      </div>

      {/* Full Audited Comparison Matrix Table */}
      <section className="studio-panel min-w-0 overflow-hidden">
        <div className="border-b border-hairline px-5 py-3.5">
          <h3 className="text-sm font-bold text-ink">
            Audited Phase 7 Comparison Ledger ({comparisons.length} Runs)
          </h3>
          <p className="text-xs text-ink-secondary">
            Side-by-side accuracy, balanced accuracy, Macro F1, and absolute difference relative to each classifier&apos;s TRTR baseline.
          </p>
        </div>
        <div className="max-h-72 overflow-auto">
          <table className="w-full text-left text-xs tabular-nums">
            <thead className="sticky top-0 bg-well/80 text-[11px] font-semibold uppercase tracking-wide text-ink-secondary">
              <tr>
                <th className="px-4 py-2.5">Classifier</th>
                <th className="px-4 py-2.5">Experiment</th>
                <th className="px-4 py-2.5 text-right">Train Rows</th>
                <th className="px-4 py-2.5 text-right">Accuracy</th>
                <th className="px-4 py-2.5 text-right">Balanced Acc</th>
                <th className="px-4 py-2.5 text-right">Macro F1</th>
                <th className="px-4 py-2.5 text-right">Weighted F1</th>
                <th className="px-4 py-2.5 text-right">Delta vs TRTR</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-hairline bg-surface">
              {comparisons.map((r, i) => {
                const diff = Number(r["Abs Macro F1 Diff"] ?? 0);
                return (
                  <tr key={i} className="hover:bg-[#FAFBF9]">
                    <td className="px-4 py-2 font-mono font-bold text-ink">{r.Model}</td>
                    <td className="px-4 py-2 font-semibold text-ink-secondary">{r.Experiment}</td>
                    <td className="px-4 py-2 text-right font-mono text-ink-secondary">
                      {r["Train Records"]?.toLocaleString() ?? "--"}
                    </td>
                    <td className="px-4 py-2 text-right font-mono text-ink">
                      {fmtMetric(r.Accuracy)}
                    </td>
                    <td className="px-4 py-2 text-right font-mono text-ink">
                      {fmtMetric(r["Balanced Accuracy"])}
                    </td>
                    <td className="px-4 py-2 text-right font-mono font-bold text-brand">
                      {fmtMetric(r["Macro F1"])}
                    </td>
                    <td className="px-4 py-2 text-right font-mono text-ink-secondary">
                      {fmtMetric(r["Weighted F1"])}
                    </td>
                    <td
                      className={`px-4 py-2 text-right font-mono font-bold ${
                        diff > 0
                          ? "text-[#1A7D5E]"
                          : diff < 0
                          ? "text-[#BF4840]"
                          : "text-ink-muted"
                      }`}
                    >
                      {fmtSignedDelta(diff)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
