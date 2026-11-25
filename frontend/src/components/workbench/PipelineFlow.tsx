"use client";

import React from "react";
import { ArrowRight, CheckCircle2, Clock } from "lucide-react";
import { SystemModelsStatus, SystemStatus } from "@/lib/types";
import { InfoTooltip } from "@/components/ui/InfoTooltip";

interface StageSpec {
  step: string;
  title: string;
  metric: string;
  detail: string;
  ready: boolean;
  tone: "blue" | "teal" | "lavender";
  note?: string;
}

export function PipelineFlow({
  systemStatus,
  modelsStatus,
  datasetCount,
  evalCount,
}: {
  systemStatus: SystemStatus | null;
  modelsStatus: SystemModelsStatus | null;
  datasetCount: number;
  evalCount: number;
}) {
  const s = systemStatus?.storage_status || {};
  const stages: StageSpec[] = [
    {
      step: "01",
      title: "Real CICIoT2023",
      metric: "125,924 flows",
      detail: "48 PCAPs · 70 physical MACs · V1 baseline uses 48,082 flows",
      ready: Boolean(s.datasets_processed_ready),
      tone: "blue",
    },
    {
      step: "02",
      title: "Stratified Split",
      metric: "88,146 / 18,889",
      detail: "70/15/15 disjoint split (+18,889 test) across devices & classes",
      ready: Boolean(s.datasets_processed_ready),
      tone: "blue",
    },
    {
      step: "03",
      title: "CTGAN Synthesis",
      metric: `${modelsStatus?.ctgan_models_count ?? "--"} model(s)`,
      detail: "Primary V2 (44 cols, 7 discrete) + retained V1 baseline (42 cols)",
      ready: Boolean(s.ctgan_models_ready && (modelsStatus?.ctgan_models_count ?? 0) > 0),
      tone: "teal",
      note: "CTGAN",
    },
    {
      step: "04",
      title: "Repair & Hardware",
      metric: "44-col output",
      detail: "V2 native device conditioning + domain repair (V1 uses post-hoc calibration)",
      ready: Boolean(s.datasets_generated_ready),
      tone: "teal",
    },
    {
      step: "05",
      title: "Quality Audit",
      metric: `${evalCount} report(s)`,
      detail: `${datasetCount} vault files · KS, MACE & 0-overlap checks`,
      ready: Boolean(s.reports_ready),
      tone: "lavender",
      note: "KS Statistic",
    },
    {
      step: "06",
      title: "Detector Lab",
      metric: `${modelsStatus?.anomaly_models_count ?? "--"} detectors`,
      detail: "TRTR, TSTR & TSTR+R on 38 flow features",
      ready: Boolean(s.anomaly_models_ready && (modelsStatus?.anomaly_models_count ?? 0) > 0),
      tone: "blue",
      note: "TSTR+R",
    },
  ];

  const toneBadge = {
    blue: "bg-brand-tint text-brand border-[#C4DBFA]",
    teal: "bg-[#E7F7F5] text-signal border-[#BBE5DF]",
    lavender: "bg-[#F0EEFC] text-signal-lavender border-[#D6D0F5]",
  };

  return (
    <section className="studio-panel p-5 sm:p-6" aria-label="End-to-End Pipeline Architecture">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-bold text-ink">End-to-End Signal Generation Pipeline</h2>
          <p className="mt-0.5 text-xs text-ink-secondary">
            Live stage readiness across preprocessing, CTGAN neural synthesis, post-hoc hardware calibration, auditing, and detection training.
          </p>
        </div>
        <span className="rounded-full border border-[#BBE5DF] bg-[#E7F7F5] px-3 py-1 text-[11px] font-semibold text-signal">
          Active Primary V2 learns device_id &amp; device_category natively; Baseline V1 uses Stage 04 post-processing
        </span>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-6">
        {stages.map((st, idx) => (
          <div key={st.step} className="relative flex items-stretch">
            <div className="studio-well flex w-full flex-col justify-between p-3.5 transition hover:border-[#C4DBFA] hover:bg-surface">
              <div>
                <div className="flex items-center justify-between gap-2">
                  <span
                    className={`inline-flex items-center rounded-md border px-2 py-0.5 font-mono text-[10px] font-bold ${toneBadge[st.tone]}`}
                  >
                    {st.step}
                  </span>
                  {st.ready ? (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-[#1A7D5E]">
                      <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                      Ready
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-ink-muted">
                      <Clock className="h-3.5 w-3.5" aria-hidden="true" />
                      Pending
                    </span>
                  )}
                </div>

                <h3 className="mt-2.5 flex items-center text-xs font-bold text-ink">
                  <span>{st.title}</span>
                  {st.note && <InfoTooltip term={st.note} />}
                </h3>
                <div className="mt-0.5 font-mono text-sm font-bold text-ink tabular-nums">
                  {st.metric}
                </div>
              </div>

              <p className="mt-2 border-t border-hairline pt-2 text-[11px] leading-snug text-ink-secondary">
                {st.detail}
              </p>
            </div>

            {idx < stages.length - 1 && (
              <div
                aria-hidden="true"
                className="hidden items-center px-0.5 text-ink-muted xl:flex"
              >
                <ArrowRight className="h-3.5 w-3.5 shrink-0" />
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
