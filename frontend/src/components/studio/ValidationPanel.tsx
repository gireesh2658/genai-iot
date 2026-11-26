"use client";

import React, { useState } from "react";
import { CheckCircle2, ChevronDown, ChevronUp, ShieldCheck } from "lucide-react";
import { CTGANGenerateResponse, EvaluationRunResponse } from "@/lib/types";
import { fmtMetric } from "@/lib/formatters";
import { SecondaryButton } from "@/components/ui/Button";
import { StatusIndicator } from "@/components/ui/StatusIndicator";

export function ValidationPanel({
  genResult,
  evalResult,
  evalBusy,
  evalError,
  onRunEvaluation,
}: {
  genResult: CTGANGenerateResponse;
  evalResult: EvaluationRunResponse | null;
  evalBusy: boolean;
  evalError: string | null;
  onRunEvaluation: () => void;
}) {
  const [expanded, setExpanded] = useState(false);

  const repair = genResult.domain_correction_summary;
  const sm = evalResult?.summary_metrics;
  const dv = evalResult?.reports?.data_validity;
  const numVal = dv?.numerical_validity;
  const protoVal = dv?.protocol_consistency;
  const lblVal = dv?.label_consistency;
  const invVal = dv?.statistical_invariants;

  return (
    <section className="studio-panel overflow-hidden" aria-label="Data validation and quality checks">
      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between gap-3 px-5 py-3.5 text-left transition hover:bg-well/40"
      >
        <div className="flex flex-wrap items-center gap-2.5">
          <ShieldCheck className="h-4 w-4 text-signal" aria-hidden="true" />
          <span className="text-sm font-bold text-ink">
            Data Validation &amp; Quality Checks
          </span>
          <StatusIndicator
            tone={genResult.domain_correction_applied ? "success" : "neutral"}
            label={
              genResult.domain_correction_applied
                ? "Domain Repair Applied"
                : "Raw CTGAN Output"
            }
          />
          {evalResult && (
            <StatusIndicator tone="info" label="Statistical Audit Completed" />
          )}
        </div>
        {expanded ? (
          <ChevronUp className="h-4 w-4 shrink-0 text-ink-secondary" />
        ) : (
          <ChevronDown className="h-4 w-4 shrink-0 text-ink-secondary" />
        )}
      </button>

      {expanded && (
        <div className="space-y-4 border-t border-hairline px-5 py-4 text-xs">
          {/* 1. Domain Consistency Summary returned directly from /ctgan/generate */}
          <div className="space-y-2">
            <h3 className="font-bold text-ink">
              Domain Consistency Repair Summary
            </h3>
            {repair ? (
              <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
                <div className="studio-well p-3">
                  <div className="text-[11px] text-ink-secondary">Category Mismatches Fixed</div>
                  <div className="mt-0.5 font-mono text-sm font-bold text-ink tabular-nums">
                    {repair.category_mismatches_fixed ?? 0}
                  </div>
                </div>
                <div className="studio-well p-3">
                  <div className="text-[11px] text-ink-secondary">is_attack Violations Fixed</div>
                  <div className="mt-0.5 font-mono text-sm font-bold text-ink tabular-nums">
                    {repair.is_attack_violations_fixed ?? 0}
                  </div>
                </div>
                <div className="studio-well p-3">
                  <div className="text-[11px] text-ink-secondary">Protocol Mismatches Fixed</div>
                  <div className="mt-0.5 font-mono text-sm font-bold text-ink tabular-nums">
                    {repair.protocol_mismatches_fixed ?? 0}
                  </div>
                </div>
                <div className="studio-well p-3">
                  <div className="text-[11px] text-ink-secondary">Std Dispersion Fixes</div>
                  <div className="mt-0.5 font-mono text-sm font-bold text-ink tabular-nums">
                    {repair.dispersion_violations_fixed ?? 0}
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-ink-secondary">
                Domain repair was not enabled for this generation run.
              </p>
            )}
          </div>

          {/* 2. Optional On-Demand Statistical Evaluation against real CICIoT2023 reference */}
          <div className="space-y-3 border-t border-hairline pt-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="font-bold text-ink">
                  Statistical Quality Evaluation (vs Real CICIoT2023 Reference)
                </h3>
                <p className="mt-0.5 text-[11px] text-ink-secondary">
                  Runs on demand against{" "}
                  <code className="font-mono">
                    {evalResult?.reference_dataset_id ||
                      (genResult.model_id === "ctgan_device_aware_v2"
                        ? "ciciot2023_device_v2_train"
                        : "ciciot2023_preprocessed_sample")}
                  </code>{" "}
                  to measure distribution distance, correlation fidelity, and training overlap.
                </p>
              </div>
              {genResult.dataset_id && (
                <SecondaryButton
                  type="button"
                  size="sm"
                  loading={evalBusy}
                  onClick={onRunEvaluation}
                >
                  {evalBusy ? "Evaluating..." : evalResult ? "Re-run Audit" : "Run Quality Audit"}
                </SecondaryButton>
              )}
            </div>

            {evalError && (
              <div
                role="alert"
                className="rounded-lg border border-[#F2C3BF] bg-[#FDECEC] px-3 py-2 text-xs font-semibold text-[#9A332D]"
              >
                {evalError}
              </div>
            )}

            {evalResult && sm ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-6">
                  <div className="studio-well p-3">
                    <div className="text-[11px] text-ink-secondary">Mean KS Distance</div>
                    <div className="mt-0.5 font-mono text-sm font-bold text-brand tabular-nums">
                      {fmtMetric(sm.average_ks_statistic_vs_train)}
                    </div>
                  </div>
                  <div className="studio-well p-3">
                    <div className="text-[11px] text-ink-secondary">Mean JS Distance</div>
                    <div className="mt-0.5 font-mono text-sm font-bold text-signal tabular-nums">
                      {fmtMetric(sm.average_jensen_shannon_distance_vs_train)}
                    </div>
                  </div>
                  <div className="studio-well p-3">
                    <div className="text-[11px] text-ink-secondary">Std. Wasserstein (W1)</div>
                    <div className="mt-0.5 font-mono text-sm font-bold text-ink tabular-nums">
                      {sm.average_normalized_wasserstein_distance_vs_train != null
                        ? fmtMetric(sm.average_normalized_wasserstein_distance_vs_train, 4)
                        : fmtMetric(sm.average_wasserstein_distance_vs_train, 2)}
                    </div>
                  </div>
                  <div className="studio-well p-3">
                    <div className="text-[11px] text-ink-secondary">Pearson MACE</div>
                    <div className="mt-0.5 font-mono text-sm font-bold text-ink tabular-nums">
                      {fmtMetric(sm.pearson_mace)}
                    </div>
                  </div>
                  <div className="studio-well p-3">
                    <div className="text-[11px] text-ink-secondary">Exact Train Overlaps</div>
                    <div className="mt-0.5 font-mono text-sm font-bold text-[#1A7D5E] tabular-nums">
                      {sm.exact_duplicate_rows_in_train ?? 0} rows
                    </div>
                  </div>
                  <div className="studio-well p-3">
                    <div className="text-[11px] text-ink-secondary">Min 1-NN Distance</div>
                    <div className="mt-0.5 font-mono text-sm font-bold text-ink tabular-nums">
                      {fmtMetric(sm.min_nearest_neighbor_distance)}
                    </div>
                  </div>
                </div>

                {dv && (
                  <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 rounded-lg border border-hairline bg-canvas px-3.5 py-2.5 text-[11px] text-ink-secondary">
                    <span className="inline-flex items-center gap-1 font-semibold text-ink">
                      <CheckCircle2 className="h-3.5 w-3.5 text-[#1A7D5E]" aria-hidden="true" />
                      Audit ID: <code className="font-mono">{evalResult.evaluation_id}</code>
                    </span>
                    <span>
                      Nulls / Infs:{" "}
                      <strong className="font-mono text-ink">
                        {numVal?.total_nulls ?? 0} / {numVal?.total_infs ?? 0}
                      </strong>
                    </span>
                    <span>
                      Negatives:{" "}
                      <strong className="font-mono text-ink">
                        {numVal?.has_negative_violations ? "Yes" : "0"}
                      </strong>
                    </span>
                    <span>
                      Label Mismatches:{" "}
                      <strong className="font-mono text-ink">
                        {lblVal?.category_mismatches?.count ?? 0}
                      </strong>
                    </span>
                    <span>
                      Protocol Mismatches:{" "}
                      <strong className="font-mono text-ink">
                        {protoVal?.protocol_type_name_mismatch?.count ?? 0}
                      </strong>
                    </span>
                    <span>
                      Std Violations:{" "}
                      <strong className="font-mono text-ink">
                        {invVal?.std_sqrt_variance?.violation_count ?? 0}
                      </strong>
                    </span>
                  </div>
                )}
              </div>
            ) : (
              !evalBusy && (
                <p className="text-[11px] text-ink-secondary">
                  {genResult.dataset_id
                    ? "Click Run Quality Audit above when needed to evaluate statistical similarity and memorization risk."
                    : "Quality audit requires an exported dataset saved on disk."}
                </p>
              )
            )}
          </div>
        </div>
      )}
    </section>
  );
}
