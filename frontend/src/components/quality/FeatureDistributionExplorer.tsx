"use client";

import React, { useEffect, useMemo, useState } from "react";
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
import { ChartContainer } from "@/components/ui/ChartContainer";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { StatusIndicator } from "@/components/ui/StatusIndicator";
import { interpretKs } from "@/lib/formatters";

export function FeatureDistributionExplorer({
  continuousTrain,
  continuousVal,
  categoricalTrain,
}: {
  continuousTrain: Record<string, any>;
  continuousVal: Record<string, any>;
  categoricalTrain: Record<string, any>;
}) {
  const featureKeys = useMemo(() => Object.keys(continuousTrain || {}), [continuousTrain]);
  const catKeys = useMemo(() => Object.keys(categoricalTrain || {}), [categoricalTrain]);

  const [selectedFeature, setSelectedFeature] = useState<string>("Rate");
  const [selectedCat, setSelectedCat] = useState<string>("label_category");
  const [tableFilter, setTableFilter] = useState("");

  useEffect(() => {
    if (featureKeys.length > 0 && !featureKeys.includes(selectedFeature)) {
      setSelectedFeature(featureKeys[0]);
    }
  }, [featureKeys, selectedFeature]);

  useEffect(() => {
    if (catKeys.length > 0 && !catKeys.includes(selectedCat)) {
      setSelectedCat(catKeys[0]);
    }
  }, [catKeys, selectedCat]);

  const activeTrainFeat = continuousTrain?.[selectedFeature];
  const activeValFeat = continuousVal?.[selectedFeature];

  const quantileBars = useMemo(() => {
    if (!activeTrainFeat) return [];
    const rs = activeTrainFeat.real_stats || {};
    const vs = activeValFeat?.real_stats || {};
    const ss = activeTrainFeat.synth_stats || {};
    return [
      { stat: "Q25", "Real Train": rs.q25 ?? 0, "Real Val": vs.q25 ?? 0, Synthetic: ss.q25 ?? 0 },
      { stat: "Median", "Real Train": rs.median ?? 0, "Real Val": vs.median ?? 0, Synthetic: ss.median ?? 0 },
      { stat: "Mean", "Real Train": rs.mean ?? 0, "Real Val": vs.mean ?? 0, Synthetic: ss.mean ?? 0 },
      { stat: "Q75", "Real Train": rs.q75 ?? 0, "Real Val": vs.q75 ?? 0, Synthetic: ss.q75 ?? 0 },
    ];
  }, [activeTrainFeat, activeValFeat]);

  const catBars = useMemo(() => {
    const obj = categoricalTrain?.[selectedCat]?.category_frequencies;
    if (!obj) return [];
    return Object.entries(obj)
      .map(([name, v]: [string, any]) => ({
        name: name.length > 16 ? `${name.slice(0, 15)}…` : name,
        fullName: name,
        "Real Train (%)": Number(v?.real_pct ?? 0),
        "Synthetic (%)": Number(v?.synth_pct ?? 0),
      }))
      .sort((a, b) => Math.max(b["Real Train (%)"], b["Synthetic (%)"]) - Math.max(a["Real Train (%)"], a["Synthetic (%)"]))
      .slice(0, 12);
  }, [categoricalTrain, selectedCat]);

  const ksSorted = useMemo(() => {
    const q = tableFilter.trim().toLowerCase();
    return Object.entries(continuousTrain || {})
      .filter(([name]) => !q || name.toLowerCase().includes(q))
      .map(([name, obj]: [string, any]) => ({
        name,
        ks: Number(obj?.ks_statistic ?? 0),
        wasserstein: Number(obj?.wasserstein_distance ?? 0),
        realMean: Number(obj?.real_stats?.mean ?? 0),
        synthMean: Number(obj?.synth_stats?.mean ?? 0),
        realStd: Number(obj?.real_stats?.std ?? 0),
        synthStd: Number(obj?.synth_stats?.std ?? 0),
      }));
  }, [continuousTrain, tableFilter]);

  const ksInterp = interpretKs(activeTrainFeat?.ks_statistic);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Continuous Feature Quantile & Moment Comparator */}
        <ChartContainer
          title={
            <>
              Continuous Feature Moments Comparison
              <InfoTooltip term="KS Statistic" />
            </>
          }
          subtitle="Select any numerical attribute to inspect Real Train vs Real Val vs Synthetic central & quartile alignment."
          unit={selectedFeature}
          isEmpty={quantileBars.length === 0}
          headerAction={
            <select
              aria-label="Select continuous feature to inspect"
              value={selectedFeature}
              onChange={(e) => setSelectedFeature(e.target.value)}
              className="studio-input w-44 py-1 font-mono text-xs"
            >
              {featureKeys.map((k) => (
                <option key={k} value={k}>
                  {k}
                </option>
              ))}
            </select>
          }
        >
          {activeTrainFeat && (
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-hairline bg-well/65 px-3 py-2 text-xs tabular-nums">
              <div className="flex flex-wrap gap-3 font-mono">
                <span>
                  KS: <strong>{Number(activeTrainFeat.ks_statistic).toFixed(4)}</strong>
                </span>
                <span>
                  W1 <InfoTooltip term="Wasserstein Distance" />:{" "}
                  <strong>{Number(activeTrainFeat.wasserstein_distance).toFixed(2)}</strong>
                </span>
                <span>
                  Max: Real {Number(activeTrainFeat.real_stats?.max).toFixed(1)} vs Synth{" "}
                  {Number(activeTrainFeat.synth_stats?.max).toFixed(1)}
                </span>
              </div>
              <StatusIndicator
                tone={
                  ksInterp.tone === "good"
                    ? "success"
                    : ksInterp.tone === "warn"
                    ? "warning"
                    : "neutral"
                }
                label={ksInterp.label}
              />
            </div>
          )}

          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={quantileBars} margin={{ top: 8, right: 8, left: -8, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5EAE7" />
                <XAxis dataKey="stat" tick={{ fill: "#556578", fontSize: 11 }} />
                <YAxis tick={{ fill: "#556578", fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#FFFFFF",
                    borderColor: "#E5EAE7",
                    borderRadius: 10,
                    fontSize: 12,
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="Real Train" fill="#2A67B1" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="Real Val" fill="#90A0B2" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="Synthetic" fill="#17857B" radius={[4, 4, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartContainer>

        {/* Discrete / Categorical Distribution Frequency Compare */}
        <ChartContainer
          title={
            <>
              Discrete Feature Balance Comparison
              <InfoTooltip term="Jensen-Shannon Distance" />
            </>
          }
          subtitle="Top category share (%) comparing Real Train vs Synthetic across evaluated discrete fields."
          unit="Share (%)"
          isEmpty={catBars.length === 0}
          headerAction={
            <select
              aria-label="Select discrete feature to inspect"
              value={selectedCat}
              onChange={(e) => setSelectedCat(e.target.value)}
              className="studio-input w-44 py-1 font-mono text-xs"
            >
              {catKeys.map((k) => (
                <option key={k} value={k}>
                  {k}
                </option>
              ))}
            </select>
          }
        >
          {categoricalTrain?.[selectedCat] && (
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-hairline bg-well/65 px-3 py-2 text-xs tabular-nums">
              <span className="font-mono">
                JS Distance:{" "}
                <strong>{Number(categoricalTrain[selectedCat].jensen_shannon_distance).toFixed(4)}</strong>
              </span>
              <span className="text-ink-secondary">
                {categoricalTrain[selectedCat].categories_count} distinct observed categories
              </span>
            </div>
          )}

          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={catBars} margin={{ top: 8, right: 8, left: -12, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5EAE7" />
                <XAxis
                  dataKey="name"
                  tick={{ fill: "#556578", fontSize: 10 }}
                  angle={-16}
                  textAnchor="end"
                  height={44}
                />
                <YAxis tick={{ fill: "#556578", fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#FFFFFF",
                    borderColor: "#E5EAE7",
                    borderRadius: 10,
                    fontSize: 12,
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="Real Train (%)" fill="#2A67B1" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="Synthetic (%)" fill="#17857B" radius={[4, 4, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartContainer>
      </div>

      {/* Full Continuous Moments & Distance Table */}
      {ksSorted.length > 0 && (
        <section className="studio-panel overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-hairline px-5 py-3.5">
            <div>
              <h3 className="text-sm font-bold text-ink">
                All Continuous Features Statistical Summary ({ksSorted.length} Attributes)
              </h3>
              <p className="text-xs text-ink-secondary">
                Parametric moments &amp; distance metrics vs 38,466-row real training distribution. Click any row to inspect quartiles above.
              </p>
            </div>
            <input
              aria-label="Filter statistical features"
              value={tableFilter}
              onChange={(e) => setTableFilter(e.target.value)}
              placeholder="Filter Rate, AVG, Std..."
              className="studio-input w-56 py-1.5 text-xs"
            />
          </div>

          <div className="max-h-72 overflow-auto">
            <table className="w-full text-left text-xs tabular-nums">
              <thead className="sticky top-0 bg-well/80 text-[11px] font-semibold uppercase tracking-wide text-ink-secondary">
                <tr>
                  <th className="px-4 py-2.5">Feature</th>
                  <th className="px-4 py-2.5 text-right">Real Mean</th>
                  <th className="px-4 py-2.5 text-right">Synth Mean</th>
                  <th className="px-4 py-2.5 text-right">Real Std</th>
                  <th className="px-4 py-2.5 text-right">Synth Std</th>
                  <th className="px-4 py-2.5 text-right">KS Stat</th>
                  <th className="px-4 py-2.5 text-right">Wasserstein</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-hairline bg-surface">
                {ksSorted.map((row) => (
                  <tr
                    key={row.name}
                    onClick={() => setSelectedFeature(row.name)}
                    className={`cursor-pointer transition ${
                      selectedFeature === row.name ? "bg-brand-tint/50" : "hover:bg-[#FAFBF9]"
                    }`}
                  >
                    <td className="px-4 py-2 font-mono font-bold text-ink">{row.name}</td>
                    <td className="px-4 py-2 text-right font-mono text-ink-secondary">
                      {row.realMean.toFixed(2)}
                    </td>
                    <td className="px-4 py-2 text-right font-mono text-ink">
                      {row.synthMean.toFixed(2)}
                    </td>
                    <td className="px-4 py-2 text-right font-mono text-ink-secondary">
                      {row.realStd.toFixed(2)}
                    </td>
                    <td className="px-4 py-2 text-right font-mono text-ink">
                      {row.synthStd.toFixed(2)}
                    </td>
                    <td className="px-4 py-2 text-right font-mono font-bold text-brand">
                      {row.ks.toFixed(4)}
                    </td>
                    <td className="px-4 py-2 text-right font-mono text-ink-secondary">
                      {row.wasserstein.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
