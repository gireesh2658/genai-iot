"use client";

import React, { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { ChartContainer } from "@/components/ui/ChartContainer";

const HARDWARE_PALETTE = ["#2A67B1", "#17857B", "#6459BA", "#239B78", "#D98A2B", "#C54B43"];

export function TelemetryCharts({
  records,
  totalRecords,
  categoryDistribution,
  hasFullCategoryMetadata = false,
  deviceDistribution,
}: {
  records: Record<string, any>[];
  totalRecords: number;
  categoryDistribution: Record<string, number>;
  hasFullCategoryMetadata?: boolean;
  deviceDistribution: Record<string, number>;
}) {
  const isTruncatedPreview = totalRecords > records.length && records.length > 0;

  const classBars = useMemo(
    () =>
      Object.entries(categoryDistribution)
        .map(([name, count]) => ({ name, count: Number(count) }))
        .sort((a, b) => b.count - a.count),
    [categoryDistribution]
  );

  const deviceSlices = useMemo(
    () =>
      Object.entries(deviceDistribution).map(([name, value]) => ({
        name,
        value: Number(value),
      })),
    [deviceDistribution]
  );

  // Compute Rate histogram buckets + Packet Length by category from actual returned rows
  const { rateHist, sizeByCategory, benignScatter, attackScatter } = useMemo(() => {
    const rateBins = [
      { label: "<10/s", count: 0 },
      { label: "10–100", count: 0 },
      { label: "100–1k", count: 0 },
      { label: "1k–10k", count: 0 },
      { label: ">10k/s", count: 0 },
    ];
    const sizeAcc: Record<string, { sumMin: number; sumAvg: number; sumMax: number; n: number }> = {};
    const benignPts: any[] = [];
    const attackPts: any[] = [];

    for (const r of records) {
      const rate = Math.max(0, Number(r.Rate || 0));
      if (rate < 10) rateBins[0].count += 1;
      else if (rate < 100) rateBins[1].count += 1;
      else if (rate < 1000) rateBins[2].count += 1;
      else if (rate < 10000) rateBins[3].count += 1;
      else rateBins[4].count += 1;

      const cat = String(r.label_category || "Unknown");
      if (!sizeAcc[cat]) sizeAcc[cat] = { sumMin: 0, sumAvg: 0, sumMax: 0, n: 0 };
      sizeAcc[cat].sumMin += Number(r.Min || 0);
      sizeAcc[cat].sumAvg += Number(r.AVG || 0);
      sizeAcc[cat].sumMax += Number(r.Max || 0);
      sizeAcc[cat].n += 1;

      const pt = {
        logRate: Number(Math.log10(rate + 1).toFixed(3)),
        avgBytes: Number(Number(r.AVG || 0).toFixed(1)),
        iatMs: Number((Number(r.IAT || 0) * 1000).toFixed(2)),
        device: String(r.device_id || "raw_ciciot"),
        category: cat,
      };
      if (Number(r.is_attack) === 0) benignPts.push(pt);
      else attackPts.push(pt);
    }

    const sizeList = Object.entries(sizeAcc).map(([name, s]) => ({
      name,
      "Mean Min (B)": Number((s.sumMin / s.n).toFixed(1)),
      "Mean AVG (B)": Number((s.sumAvg / s.n).toFixed(1)),
      "Mean Max (B)": Number((s.sumMax / s.n).toFixed(1)),
    }));

    return {
      rateHist: rateBins,
      sizeByCategory: sizeList,
      benignScatter: benignPts,
      attackScatter: attackPts,
    };
  }, [records]);

  const previewScopeNote = isTruncatedPreview
    ? `Computed across returned ${records.length} preview rows (of ${totalRecords.toLocaleString()} total dataset rows).`
    : `Computed across all ${records.length.toLocaleString()} rows.`;

  return (
    <div className="space-y-5">
      {/* Row 1: Dataset-wide Threat & Hardware Distributions */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <ChartContainer
          title="Traffic Threat Category Breakdown"
          subtitle={
            hasFullCategoryMetadata
              ? "Full-dataset record distribution reported by generation metadata"
              : previewScopeNote
          }
          unit="Flows"
          isEmpty={classBars.length === 0}
        >
          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={classBars} margin={{ top: 6, right: 10, left: -14, bottom: 20 }}>
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
                <Bar
                  dataKey="count"
                  name="Flows"
                  fill="#2A67B1"
                  radius={[5, 5, 0, 0]}
                  isAnimationActive={false}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartContainer>

        <ChartContainer
          title="IoT Hardware Category Allocation"
          subtitle="Native V2 learned device categories or V1 calibrated profiles"
          unit="Devices"
          isEmpty={deviceSlices.length === 0}
          emptyMessage="This 42-column dataset does not contain IoT device categories."
        >
          <div className="grid h-60 grid-cols-1 items-center sm:grid-cols-2">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={deviceSlices}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={42}
                  outerRadius={74}
                  paddingAngle={2}
                  isAnimationActive={false}
                >
                  {deviceSlices.map((_, i) => (
                    <Cell key={i} fill={HARDWARE_PALETTE[i % HARDWARE_PALETTE.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#FFFFFF",
                    borderColor: "#E5EAE7",
                    borderRadius: 10,
                    fontSize: 12,
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-1.5 pr-2 text-xs">
              {deviceSlices.map((d, i) => (
                <div key={d.name} className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 truncate text-ink">
                    <span
                      className="h-2.5 w-2.5 shrink-0 rounded-full"
                      style={{ backgroundColor: HARDWARE_PALETTE[i % HARDWARE_PALETTE.length] }}
                    />
                    <span className="truncate font-medium">{d.name}</span>
                  </span>
                  <span className="font-mono font-bold text-ink tabular-nums">
                    {d.value.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </ChartContainer>
      </div>

      {/* Row 2: Rate Histogram + Packet Size Comparison (Preview Sample Scope Disclosed) */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <ChartContainer
          title="Packet Transmission Rate Histogram"
          subtitle={previewScopeNote}
          unit="pkt/s bins"
          isEmpty={records.length === 0}
        >
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={rateHist} margin={{ top: 8, right: 10, left: -14, bottom: 6 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5EAE7" />
                <XAxis dataKey="label" tick={{ fill: "#556578", fontSize: 11 }} />
                <YAxis tick={{ fill: "#556578", fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#FFFFFF",
                    borderColor: "#E5EAE7",
                    borderRadius: 10,
                    fontSize: 12,
                  }}
                />
                <Bar
                  dataKey="count"
                  name="Flows in bin"
                  fill="#17857B"
                  radius={[5, 5, 0, 0]}
                  isAnimationActive={false}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartContainer>

        <ChartContainer
          title="Mean Packet Sizes by Class"
          subtitle={previewScopeNote}
          unit="Bytes"
          isEmpty={sizeByCategory.length === 0}
        >
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sizeByCategory} margin={{ top: 8, right: 10, left: -14, bottom: 20 }}>
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
                <Bar dataKey="Mean Min (B)" fill="#8B99AA" radius={[3, 3, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="Mean AVG (B)" fill="#17857B" radius={[3, 3, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="Mean Max (B)" fill="#6459BA" radius={[3, 3, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ChartContainer>
      </div>

      {/* Row 3: Feature Relationship Scatter (Rate vs AVG Bytes, IAT in tooltip) */}
      <ChartContainer
        title="Rate vs Average Packet Size Feature Relationship"
        subtitle={`Benign (${benignScatter.length}) vs Attack (${attackScatter.length}) separation · ${previewScopeNote}`}
        unit="Log10(pkt/s+1) × Bytes"
        isEmpty={records.length === 0}
      >
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 8, right: 16, bottom: 26, left: -8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E5EAE7" />
              <XAxis
                type="number"
                dataKey="logRate"
                name="Log10(Rate+1)"
                tick={{ fill: "#556578", fontSize: 11 }}
                label={{
                  value: "Log10(Rate + 1) [packets/s]",
                  position: "insideBottom",
                  offset: -14,
                  fontSize: 11,
                  fill: "#556578",
                }}
              />
              <YAxis
                type="number"
                dataKey="avgBytes"
                name="AVG Bytes"
                tick={{ fill: "#556578", fontSize: 11 }}
              />
              <ZAxis range={[45, 70]} />
              <Tooltip
                cursor={{ strokeDasharray: "3 3" }}
                contentStyle={{
                  backgroundColor: "#FFFFFF",
                  borderColor: "#E5EAE7",
                  borderRadius: 10,
                  fontSize: 12,
                }}
                formatter={(val: any, name: any) => [val, name]}
              />
              <Legend
                verticalAlign="top"
                align="right"
                wrapperStyle={{ fontSize: 11, paddingBottom: 8 }}
              />
              <Scatter
                name="Benign Flows"
                data={benignScatter}
                fill="#1A7D5E"
                fillOpacity={0.85}
                isAnimationActive={false}
              />
              <Scatter
                name="Attack Flows"
                data={attackScatter}
                fill="#C54B43"
                fillOpacity={0.75}
                isAnimationActive={false}
              />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </ChartContainer>
    </div>
  );
}
