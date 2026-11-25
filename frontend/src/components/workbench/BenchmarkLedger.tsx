"use client";

import React, { useMemo } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
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
import { AnomalyModelDetail, ExperimentComparisonRecord } from "@/lib/types";
import { fmtClassifierName, fmtMetric, fmtSignedDelta } from "@/lib/formatters";
import { ChartContainer } from "@/components/ui/ChartContainer";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { StatusIndicator } from "@/components/ui/StatusIndicator";

export function BenchmarkLedger({
  comparisons,
  rfBaseline,
  rfAugmented,
}: {
  comparisons: ExperimentComparisonRecord[];
  rfBaseline: AnomalyModelDetail | null;
  rfAugmented: AnomalyModelDetail | null;
}) {
  const chartData = useMemo(() => {
    const grouped: Record<string, any> = {};
    for (const row of comparisons) {
      const model = row.Model;
      if (!grouped[model]) {
        grouped[model] = { classifier: fmtClassifierName(model) };
      }
      if (row.Experiment.startsWith("TRTR")) grouped[model]["TRTR (Real)"] = row["Macro F1"];
      else if (row.Experiment.startsWith("TSTR (")) grouped[model]["TSTR (Pure Synth)"] = row["Macro F1"];
      else if (row.Experiment === "TSTR+R (25%)")
        grouped[model]["TSTR+R (25% CTGAN)"] = row["Macro F1"];
    }
    return Object.values(grouped);
  }, [comparisons]);

  const rfBaseF1 = rfBaseline?.overall_metrics?.macro_f1 ?? null;
  const rfAugF1 = rfAugmented?.overall_metrics?.macro_f1 ?? null;
  const bruteBase = rfBaseline?.per_class_metrics?.["Brute Force"]?.f1_score ?? null;
  const bruteAug = rfAugmented?.per_class_metrics?.["Brute Force"]?.f1_score ?? null;
  const webF1 = rfAugmented?.per_class_metrics?.["Web-based"]?.f1_score ?? null;

  return (
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
      {/* Left: Audited Benchmark Proof Summary */}
      <section className="studio-panel flex flex-col justify-between p-5 sm:p-6 xl:col-span-5">
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <StatusIndicator tone="info" label="Historical Phase 7 Benchmarks" />
            <Link
              href="/anomaly"
              className="inline-flex items-center gap-1 text-xs font-bold text-brand hover:underline"
            >
              Open Full Lab <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          <div>
            <h2 className="text-base font-bold text-ink">
              Does CTGAN Data Improve Real Attack Detection?
            </h2>
            <p className="mt-1 text-xs leading-relaxed text-ink-secondary">
              Evaluated strictly on the untouched <strong className="text-ink">9,616 real CICIoT2023 validation flows</strong>. Pure synthetic training (TSTR) trails real data, whereas mixing <strong className="text-ink">25% CTGAN augmentation (TSTR+R)</strong> improves both tree ensemble &amp; gradient-boosted Macro F1.
            </p>
          </div>

          <div className="overflow-x-auto rounded-xl border border-hairline">
            <table className="w-full text-left text-xs tabular-nums">
              <thead className="bg-well/80 text-[11px] font-semibold uppercase tracking-wide text-ink-secondary">
                <tr>
                  <th className="px-3 py-2">Metric / Slice (RF)</th>
                  <th className="px-3 py-2 text-right">TRTR Baseline</th>
                  <th className="px-3 py-2 text-right">TSTR+R (25%)</th>
                  <th className="px-3 py-2 text-right">Delta</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline bg-surface">
                <tr>
                  <td className="px-3 py-2 font-semibold text-ink">
                    Overall Macro F1 <InfoTooltip term="Macro F1" />
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-ink-secondary">
                    {fmtMetric(rfBaseF1)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono font-bold text-brand">
                    {fmtMetric(rfAugF1)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono font-bold text-[#1A7D5E]">
                    {rfBaseF1 !== null && rfAugF1 !== null
                      ? fmtSignedDelta(rfAugF1 - rfBaseF1)
                      : "--"}
                  </td>
                </tr>
                <tr>
                  <td className="px-3 py-2 font-semibold text-ink">Brute Force (Support 3)</td>
                  <td className="px-3 py-2 text-right font-mono text-ink-secondary">
                    {fmtMetric(bruteBase)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono font-bold text-signal">
                    {fmtMetric(bruteAug)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono font-bold text-[#1A7D5E]">
                    {bruteBase !== null && bruteAug !== null
                      ? fmtSignedDelta(bruteAug - bruteBase)
                      : "--"}
                  </td>
                </tr>
                <tr>
                  <td className="px-3 py-2 font-semibold text-ink">Web-based (Support 5)</td>
                  <td className="px-3 py-2 text-right font-mono text-ink-secondary">0.0000</td>
                  <td className="px-3 py-2 text-right font-mono font-bold text-[#A36312]">
                    {fmtMetric(webF1)}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-ink-secondary">0.0000 (Gap)</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <p className="mt-4 border-t border-hairline pt-3 text-[11px] leading-relaxed text-ink-secondary">
          <strong className="text-ink">Research Honesty:</strong> Figures above come from saved Phase 7 benchmark JSONs, not live user inference. Sparse real examples (10 Brute Force, 19 Web-based in training) keep Web-based F1 at 0.0000.
        </p>
      </section>

      {/* Right: Grouped Recharts Comparison */}
      <ChartContainer
        title={
          <>
            Paradigm Benchmark Across Classifier Families
            <InfoTooltip term="TSTR+R" />
          </>
        }
        subtitle="Real-only baseline (TRTR) vs Pure CTGAN (TSTR) vs Optimal 25% CTGAN Augmentation (TSTR+R)"
        unit="Macro F1 [0–1]"
        isEmpty={chartData.length === 0}
        emptyMessage="Benchmark matrix unavailable from backend /anomaly/experiments/compare."
        className="xl:col-span-7"
      >
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 8, right: 12, left: -12, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E5EAE7" />
              <XAxis dataKey="classifier" tick={{ fill: "#556578", fontSize: 11 }} />
              <YAxis domain={[0, 0.8]} tick={{ fill: "#556578", fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#FFFFFF",
                  borderColor: "#E5EAE7",
                  borderRadius: 10,
                  fontSize: 12,
                  color: "#2B3748",
                }}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="TRTR (Real)" fill="#8B99AA" radius={[4, 4, 0, 0]} isAnimationActive={false} />
              <Bar dataKey="TSTR (Pure Synth)" fill="#17857B" radius={[4, 4, 0, 0]} isAnimationActive={false} />
              <Bar dataKey="TSTR+R (25% CTGAN)" fill="#2A67B1" radius={[4, 4, 0, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </ChartContainer>
    </div>
  );
}
