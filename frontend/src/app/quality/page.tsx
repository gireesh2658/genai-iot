"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Play } from "lucide-react";
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
import { api } from "@/lib/api";
import {
  EvaluationDetailResponse,
  EvaluationRunResponse,
  EvaluationStatusResponse,
  EvaluationSummaryItem,
} from "@/lib/types";
import { fmtMetric, fmtTimestamp } from "@/lib/formatters";
import { PageHeader } from "@/components/layout/PageHeader";
import { PrimaryButton } from "@/components/ui/Button";
import { ChartContainer } from "@/components/ui/ChartContainer";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { ErrorState, LoadingSkeleton } from "@/components/ui/StateViews";
import { StatusIndicator } from "@/components/ui/StatusIndicator";
import { useToast } from "@/components/ui/ToastProvider";
import { FeatureDistributionExplorer } from "@/components/quality/FeatureDistributionExplorer";
import { CorrelationHeatmaps } from "@/components/quality/CorrelationHeatmaps";
import { DomainValidityAudit } from "@/components/quality/DomainValidityAudit";

function QualityAuditInner() {
  const searchParams = useSearchParams();
  const initialDataset = searchParams.get("dataset");
  const { pushToast } = useToast();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [statusInfo, setStatusInfo] = useState<EvaluationStatusResponse | null>(null);
  const [resultsList, setResultsList] = useState<EvaluationSummaryItem[]>([]);
  const [selectedEvalId, setSelectedEvalId] = useState("phase6_approved");
  const [detail, setDetail] = useState<EvaluationDetailResponse | null>(null);

  const [synthDatasetId, setSynthDatasetId] = useState(
    initialDataset || "ctgan_initial_sample_v1_domain_corrected"
  );
  const [runResult, setRunResult] = useState<EvaluationRunResponse | null>(null);
  const [auditBusy, setAuditBusy] = useState(false);

  const loadAll = async (targetEvalId?: string) => {
    setError(null);
    try {
      const [st, list] = await Promise.all([api.getEvaluationStatus(), api.listEvaluationResults()]);
      setStatusInfo(st);
      setResultsList(list.results || []);
      if (initialDataset && (st.available_synthetic_datasets || []).includes(initialDataset)) {
        setSynthDatasetId(initialDataset);
      }
      const idToFetch = targetEvalId || selectedEvalId;
      const d = await api.getEvaluationDetail(idToFetch);
      setDetail(d);
    } catch (e: any) {
      setError(e.message || "Failed to load evaluation reports.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const handleSelectEval = async (id: string) => {
    setSelectedEvalId(id);
    setRunResult(null);
    try {
      const d = await api.getEvaluationDetail(id);
      setDetail(d);
    } catch (e: any) {
      pushToast("error", "Could not open report", e.message);
    }
  };

  const handleRunEvaluation = async () => {
    setAuditBusy(true);
    try {
      const refId = (statusInfo?.available_reference_datasets || ["ciciot2023_preprocessed_sample"])[0];
      const res = await api.runEvaluation({
        reference_dataset_id: refId,
        synthetic_dataset_id: synthDatasetId,
        generate_plots: false,
        test_conditional_sampling: false,
      });
      setRunResult(res);
      setSelectedEvalId(res.evaluation_id);
      await loadAll(res.evaluation_id);
      pushToast(
        "success",
        "Statistical audit completed",
        `Evaluated '${synthDatasetId}' against CICIoT2023 (${res.evaluation_id})`
      );
    } catch (e: any) {
      pushToast("error", "Quality audit failed", e.message);
    } finally {
      setAuditBusy(false);
    }
  };

  const activeSummaryMeta = resultsList.find((r) => r.evaluation_id === selectedEvalId);

  const statFull =
    detail?.statistical_similarity || runResult?.reports?.statistical_similarity || {};
  const statSummary = statFull.summary_metrics || runResult?.summary_metrics || {};

  const corrFull =
    detail?.feature_correlation || runResult?.reports?.feature_correlation || null;
  const corrSummary = corrFull?.summary || {};

  const divFull =
    detail?.diversity_and_memorization || runResult?.reports?.diversity_summary || null;
  const divSummary = divFull?.summary || {};
  const nnSummary = divFull?.nearest_neighbor_distance || {};

  const classMacro =
    detail?.class_distribution?.distribution_comparison?.macro_category_comparison ||
    runResult?.reports?.class_distribution?.macro_category_comparison ||
    {};

  const classAlignChart = Object.entries(classMacro).map(([name, vals]: [string, any]) => ({
    name,
    "Real Train (%)": Number(vals?.train_pct ?? 0),
    "Real Val (%)": Number(vals?.val_pct ?? 0),
    "Synthetic (%)": Number(vals?.synth_pct ?? 0),
  }));

  const synthRowsCount =
    detail?.data_validity?.numerical_validity?.total_rows ||
    divFull?.internal_diversity?.total_records ||
    null;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Statistical Fidelity & Domain Integrity"
        title="Synthetic Data Quality Audit"
        description="Verify marginal distributions, multivariate correlation preservation, exact-duplicate novelty, and physical/taxonomy constraints against the 38,466-row real training and 9,616-row validation splits."
        statusSlot={
          activeSummaryMeta ? (
            <StatusIndicator
              tone={activeSummaryMeta.source === "baseline_benchmark" ? "info" : "synthetic"}
              label={`${activeSummaryMeta.evaluation_id} · ${fmtTimestamp(activeSummaryMeta.created_at)}`}
            />
          ) : null
        }
      />

      {error && <ErrorState message={error} onRetry={() => loadAll()} />}

      {loading ? (
        <LoadingSkeleton rows={5} />
      ) : (
        <>
          {/* Isolated Scientific Control Bar (Michelin Filter Panel) */}
          <section className="studio-well grid grid-cols-1 gap-4 p-4 md:grid-cols-12">
            <div className="md:col-span-5">
              <label htmlFor="audit-dataset-select" className="mb-1 block text-xs font-bold text-ink-secondary">
                Target Synthetic Dataset
              </label>
              <select
                id="audit-dataset-select"
                value={synthDatasetId}
                onChange={(e) => setSynthDatasetId(e.target.value)}
                className="studio-input font-mono text-xs"
              >
                {(statusInfo?.available_synthetic_datasets || []).map((id) => (
                  <option key={id} value={id}>
                    {id}
                  </option>
                ))}
              </select>
            </div>

            <div className="md:col-span-4">
              <label htmlFor="audit-history-select" className="mb-1 block text-xs font-bold text-ink-secondary">
                Saved Evaluation Run
              </label>
              <select
                id="audit-history-select"
                value={selectedEvalId}
                onChange={(e) => handleSelectEval(e.target.value)}
                className="studio-input text-xs font-semibold"
              >
                {resultsList.map((r) => (
                  <option key={r.evaluation_id} value={r.evaluation_id}>
                    {r.title || r.evaluation_id}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-end md:col-span-3">
              <PrimaryButton
                type="button"
                loading={auditBusy}
                onClick={handleRunEvaluation}
                className="w-full"
              >
                <Play className="h-4 w-4" />
                {auditBusy ? "Running Audit..." : "Run Live Quality Audit"}
              </PrimaryButton>
            </div>
          </section>

          {/* Reference Provenance + 5 Scientific Readouts */}
          <section className="studio-panel p-5">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2 border-b border-hairline pb-3 text-xs text-ink-secondary tabular-nums">
              <div>
                Reference: <strong className="font-mono text-ink">ciciot2023_preprocessed_sample</strong> (38,466 train / 9,616 val) · Evaluated Synthetic Rows:{" "}
                <strong className="font-mono text-ink">{synthRowsCount?.toLocaleString() ?? "--"}</strong>
              </div>
              <div className="font-mono text-[11px]">Report Source: {detail?.source ?? "--"}</div>
            </div>

            <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
              <div className="studio-well p-3.5">
                <div className="flex items-center text-[11px] font-bold text-ink-secondary">
                  Mean KS <InfoTooltip term="KS Statistic" />
                </div>
                <div className="mt-1 font-mono text-xl font-bold text-brand tabular-nums">
                  {fmtMetric(statSummary.average_ks_statistic_vs_train)}
                </div>
                <div className="mt-0.5 text-[11px] text-ink-secondary">17 continuous CDFs</div>
              </div>

              <div className="studio-well p-3.5">
                <div className="flex items-center text-[11px] font-bold text-ink-secondary">
                  Mean JS <InfoTooltip term="Jensen-Shannon Distance" />
                </div>
                <div className="mt-1 font-mono text-xl font-bold text-signal tabular-nums">
                  {fmtMetric(statSummary.average_jensen_shannon_distance_vs_train)}
                </div>
                <div className="mt-0.5 text-[11px] text-ink-secondary">Discrete balance</div>
              </div>

              <div className="studio-well p-3.5">
                <div className="flex items-center text-[11px] font-bold text-ink-secondary">
                  Pearson MACE <InfoTooltip term="Pearson MACE" />
                </div>
                <div className="mt-1 font-mono text-xl font-bold text-signal-lavender tabular-nums">
                  {fmtMetric(corrSummary.pearson_mace ?? runResult?.summary_metrics?.pearson_mace)}
                </div>
                <div className="mt-0.5 text-[11px] text-ink-secondary">13×13 matrix error</div>
              </div>

              <div className="studio-well p-3.5">
                <div className="text-[11px] font-bold text-ink-secondary">Exact Train Overlap</div>
                <div className="mt-1 font-mono text-xl font-bold text-[#1A7D5E] tabular-nums">
                  {divSummary.exact_training_overlaps ??
                    runResult?.summary_metrics?.exact_duplicate_rows_in_train ??
                    0}{" "}
                  rows
                </div>
                <div className="mt-0.5 text-[11px] text-ink-secondary">Unmemorized generation</div>
              </div>

              <div className="studio-well p-3.5">
                <div className="flex items-center text-[11px] font-bold text-ink-secondary">
                  Min 1-NN Dist <InfoTooltip term="1-NN Distance" />
                </div>
                <div className="mt-1 font-mono text-xl font-bold text-ink tabular-nums">
                  {fmtMetric(
                    nnSummary.min_distance ?? runResult?.summary_metrics?.min_nearest_neighbor_distance
                  )}
                </div>
                <div className="mt-0.5 text-[11px] text-ink-secondary">Standardized Euclidean</div>
              </div>
            </div>
          </section>

          {/* Class Balance */}
          <ChartContainer
            title="Macro Threat Composition: Real Train vs Real Val vs Synthetic"
            subtitle="Note: Conditional quota datasets intentionally elevate rare-attack share above real CICIoT2023 prevalence."
            unit="Share (%)"
            isEmpty={classAlignChart.length === 0}
          >
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={classAlignChart} margin={{ top: 8, right: 12, left: -12, bottom: 20 }}>
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
                  <Bar dataKey="Real Val (%)" fill="#90A0B2" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                  <Bar dataKey="Synthetic (%)" fill="#17857B" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ChartContainer>

          <FeatureDistributionExplorer
            continuousTrain={statFull.continuous_feature_comparisons_vs_train || {}}
            continuousVal={statFull.continuous_feature_comparisons_vs_val || {}}
            categoricalTrain={statFull.categorical_feature_comparisons_vs_train || {}}
          />

          <CorrelationHeatmaps correlationReport={corrFull} />

          <DomainValidityAudit
            validityReport={detail?.data_validity || runResult?.reports?.data_validity || null}
            diversityReport={divFull}
            threeCandidates={detail?.three_candidate_comparison || null}
          />
        </>
      )}
    </div>
  );
}

export default function QualityPage() {
  return (
    <Suspense fallback={<LoadingSkeleton rows={5} />}>
      <QualityAuditInner />
    </Suspense>
  );
}
