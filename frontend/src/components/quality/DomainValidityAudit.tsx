"use client";

import React from "react";
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

export function DomainValidityAudit({
  validityReport,
  diversityReport,
  threeCandidates,
}: {
  validityReport: Record<string, any> | null;
  diversityReport: Record<string, any> | null;
  threeCandidates: Record<string, any> | null;
}) {
  const numVal = validityReport?.numerical_validity || {};
  const inv = validityReport?.statistical_invariants || {};
  const proto = validityReport?.protocol_consistency || {};
  const lbl = validityReport?.label_consistency || {};

  const checks: Array<{
    name: string;
    result: string;
    tone: "success" | "warning" | "danger" | "info";
    note: string;
  }> = [
    {
      name: "Schema Alignment",
      result: validityReport?.schema_validity?.is_valid ? "42/42 Valid" : "Check Failed",
      tone: validityReport?.schema_validity?.is_valid ? "success" : "danger",
      note: "Exact column order matching reference baseline (44-col calibrated files project cleanly).",
    },
    {
      name: "Null / Infinite Numbers",
      result: `${numVal.total_nulls ?? 0} nulls · ${numVal.total_infs ?? 0} infs`,
      tone: (numVal.total_nulls ?? 0) === 0 && (numVal.total_infs ?? 0) === 0 ? "success" : "danger",
      note: "All generated numeric entries are finite.",
    },
    {
      name: "Non-Negative Volumetric Bounds",
      result: numVal.has_negative_violations ? "Violations Detected" : "0 Negatives",
      tone: numVal.has_negative_violations ? "danger" : "success",
      note: "Packet rates, byte lengths, counts, and variances >= 0.",
    },
    {
      name: "Label Taxonomy Hierarchy",
      result: `${lbl.category_mismatches?.count ?? 0} cat · ${lbl.total_is_attack_violations?.count ?? 0} target`,
      tone:
        (lbl.category_mismatches?.count ?? 0) === 0 &&
        (lbl.total_is_attack_violations?.count ?? 0) === 0
          ? "success"
          : "warning",
      note: "label_raw <-> label_category <-> is_attack alignment.",
    },
    {
      name: "Protocol Name Consistency",
      result: `${proto.protocol_type_name_mismatch?.count ?? 0} mismatches`,
      tone: (proto.protocol_type_name_mismatch?.count ?? 0) === 0 ? "success" : "warning",
      note: "Protocol Type integer vs protocol_name string alignment.",
    },
    {
      name: "Dispersion Rule (Std = sqrt(Var))",
      result: `${inv.std_sqrt_variance?.violation_count ?? 0} violations`,
      tone: (inv.std_sqrt_variance?.violation_count ?? 0) === 0 ? "success" : "warning",
      note: "Variance-derived Std repair applied when domain correction is enabled.",
    },
    {
      name: "Packet Ordering (Min <= AVG <= Max)",
      result: `${inv.min_le_avg_le_max?.total_violations ?? 0} unresolved`,
      tone: (inv.min_le_avg_le_max?.total_violations ?? 0) === 0 ? "success" : "warning",
      note: "Unresolved by design on pure attack flows: sorting distorted Min KS by +57%.",
    },
    {
      name: "Aggregation Quotient (AVG ≈ TotSum/N)",
      result: `${inv.avg_tot_sum_ratio?.violation_count ?? 0} unresolved`,
      tone: (inv.avg_tot_sum_ratio?.violation_count ?? 0) === 0 ? "success" : "warning",
      note: "Unresolved by design: recalculation distorted Tot sum KS & AVG mean.",
    },
  ];

  const candidateChart = threeCandidates
    ? Object.entries(threeCandidates).map(([name, obj]: [string, any]) => ({
        name,
        "Category Mismatch": obj?.validity?.category_mismatches ?? 0,
        "is_attack Error": obj?.validity?.is_attack_violations ?? 0,
        "Protocol Mismatch": obj?.validity?.protocol_mismatches ?? 0,
        "Std != sqrt(Var)": obj?.validity?.dispersion_violations ?? 0,
      }))
    : [];

  const divInternal = diversityReport?.internal_diversity || {};
  const divOverlap = diversityReport?.training_overlap || {};
  const nn = diversityReport?.nearest_neighbor_distance || {};

  return (
    <div className="space-y-6">
      {/* Domain Validity Grid */}
      <section className="studio-panel p-5">
        <div className="mb-4">
          <h3 className="text-sm font-bold text-ink">
            Domain Constraints &amp; Physical Invariant Audit
          </h3>
          <p className="mt-0.5 text-xs text-ink-secondary">
            Distinguishes passed schema/taxonomy checks from intentional unresolved order-statistic caveats.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-4">
          {checks.map((c) => (
            <div key={c.name} className="studio-well flex flex-col justify-between p-3.5">
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div className="text-xs font-bold text-ink">{c.name}</div>
                  <StatusIndicator tone={c.tone} label={c.tone === "success" ? "Pass" : c.tone === "warning" ? "Caveat" : "Fail"} />
                </div>
                <div className="mt-1.5 font-mono text-sm font-bold text-ink tabular-nums">
                  {c.result}
                </div>
              </div>
              <p className="mt-2 border-t border-hairline pt-2 text-[11px] leading-snug text-ink-secondary">
                {c.note}
              </p>
            </div>
          ))}
        </div>
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        {/* Three Candidate Remediation Chart */}
        {candidateChart.length > 0 && (
          <ChartContainer
            title="Raw CTGAN vs Label-Corrected vs Domain-Corrected (5,000 Flows)"
            subtitle="Pre/post repair violation reduction from Phase 6 comparative audit"
            unit="Violating rows"
            className="lg:col-span-7"
          >
            <div className="h-60">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={candidateChart} margin={{ top: 8, right: 8, left: -12, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5EAE7" />
                  <XAxis dataKey="name" tick={{ fill: "#556578", fontSize: 11 }} />
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
                  <Bar dataKey="Category Mismatch" fill="#BF4840" radius={[3, 3, 0, 0]} isAnimationActive={false} />
                  <Bar dataKey="Protocol Mismatch" fill="#D98A2B" radius={[3, 3, 0, 0]} isAnimationActive={false} />
                  <Bar dataKey="Std != sqrt(Var)" fill="#2A67B1" radius={[3, 3, 0, 0]} isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ChartContainer>
        )}

        {/* Diversity & Empirical Overlap */}
        <section
          className={`studio-panel flex flex-col justify-between p-5 ${
            candidateChart.length > 0 ? "lg:col-span-5" : "lg:col-span-12"
          }`}
        >
          <div className="space-y-4">
            <div className="flex items-center justify-between gap-2">
              <h3 className="flex items-center text-sm font-bold text-ink">
                Diversity &amp; Memorization Audit
                <InfoTooltip term="1-NN Distance" />
              </h3>
              <StatusIndicator
                tone={(divOverlap.exact_overlap_count ?? 0) === 0 ? "success" : "warning"}
                label={
                  (divOverlap.exact_overlap_count ?? 0) === 0
                    ? "0 Exact Copies"
                    : `${divOverlap.exact_overlap_count} Copies`
                }
              />
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs tabular-nums">
              <div className="studio-well p-3">
                <span className="text-ink-secondary">Internal Uniqueness</span>
                <div className="mt-1 font-mono text-base font-bold text-ink">
                  {((divInternal.uniqueness_ratio ?? 1) * 100).toFixed(2)}%
                </div>
                <span className="text-[11px] text-ink-secondary">
                  {divInternal.exact_duplicate_records ?? 0} internal duplicates
                </span>
              </div>
              <div className="studio-well p-3">
                <span className="text-ink-secondary">Exact Train Overlap</span>
                <div className="mt-1 font-mono text-base font-bold text-[#1A7D5E]">
                  {divOverlap.exact_overlap_count ?? 0} rows
                </div>
                <span className="text-[11px] text-ink-secondary">
                  vs 38,466 real training rows
                </span>
              </div>
              <div className="studio-well p-3">
                <span className="text-ink-secondary">Min 1-NN Distance</span>
                <div className="mt-1 font-mono text-base font-bold text-ink">
                  {typeof nn.min_distance === "number" ? nn.min_distance.toFixed(4) : "--"}
                </div>
                <span className="text-[11px] text-ink-secondary">
                  P01: {typeof nn.p01_distance === "number" ? nn.p01_distance.toFixed(4) : "--"}
                </span>
              </div>
              <div className="studio-well p-3">
                <span className="text-ink-secondary">Median / P95 1-NN</span>
                <div className="mt-1 font-mono text-base font-bold text-ink">
                  {typeof nn.median_distance === "number" ? nn.median_distance.toFixed(4) : "--"}
                </div>
                <span className="text-[11px] text-ink-secondary">
                  P95: {typeof nn.p95_distance === "number" ? nn.p95_distance.toFixed(4) : "--"}
                </span>
              </div>
            </div>
          </div>

          <p className="mt-4 rounded-xl border border-[#C4DBFA] bg-[#EAF2FD]/70 px-3 py-2.5 text-[11px] leading-relaxed text-[#1E4F8A]">
            <strong>Research Boundary:</strong> Zero exact matches and non-zero 1-NN Euclidean distance show sample novelty over standardized continuous features, but ordinary CTGAN training provides no formal differential-privacy (ε, δ) guarantee.
          </p>
        </section>
      </div>
    </div>
  );
}
