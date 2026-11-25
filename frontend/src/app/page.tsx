"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Cpu, Database, Layers, ShieldCheck, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import {
  AnomalyModelDetail,
  AnomalyModelSummary,
  CTGANModelDetail,
  DatasetItem,
  EvaluationSummaryItem,
  ExperimentComparisonRecord,
  IoTDeviceProfile,
  SystemModelsStatus,
  SystemStatus,
} from "@/lib/types";
import { fmtNumber } from "@/lib/formatters";
import { PageHeader } from "@/components/layout/PageHeader";
import { PrimaryButton } from "@/components/ui/Button";
import { StatusIndicator } from "@/components/ui/StatusIndicator";
import { ErrorState, LoadingSkeleton } from "@/components/ui/StateViews";
import { PipelineFlow } from "@/components/workbench/PipelineFlow";
import { BenchmarkLedger } from "@/components/workbench/BenchmarkLedger";
import { DeviceFleetGrid } from "@/components/workbench/DeviceFleetGrid";

export default function ExecutiveWorkbenchPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [modelsStatus, setModelsStatus] = useState<SystemModelsStatus | null>(null);
  const [ctganMeta, setCtganMeta] = useState<CTGANModelDetail | null>(null);
  const [devices, setDevices] = useState<IoTDeviceProfile[]>([]);
  const [datasets, setDatasets] = useState<DatasetItem[]>([]);
  const [evaluations, setEvaluations] = useState<EvaluationSummaryItem[]>([]);
  const [comparisons, setComparisons] = useState<ExperimentComparisonRecord[]>([]);
  const [rfBase, setRfBase] = useState<AnomalyModelDetail | null>(null);
  const [rfAug, setRfAug] = useState<AnomalyModelDetail | null>(null);
  const [customModels, setCustomModels] = useState<AnomalyModelSummary[]>([]);

  const loadWorkbench = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sysR, msR, ctR, devR, dsR, evR, cmpR, rf0R, rf25R, amR] = await Promise.allSettled([
        api.getSystemStatus(),
        api.getSystemModelsStatus(),
        api.getCtganModelDetail("ctgan_device_aware_v2"),
        api.listDeviceProfiles(),
        api.listDatasets(),
        api.listEvaluationResults(),
        api.compareAnomalyExperiments(),
        api.getAnomalyModelDetail("random_forest_trtr"),
        api.getAnomalyModelDetail("random_forest_tstr_r_25"),
        api.listAnomalyModels(),
      ]);

      if (sysR.status === "rejected" && msR.status === "rejected") {
        const backendTarget = process.env.NEXT_PUBLIC_BACKEND_URL || "the configured backend API (/api/v1)";
        throw new Error(`Could not connect to FastAPI backend at ${backendTarget}.`);
      }

      if (sysR.status === "fulfilled") setSystemStatus(sysR.value);
      if (msR.status === "fulfilled") setModelsStatus(msR.value);
      if (ctR.status === "fulfilled") setCtganMeta(ctR.value);
      if (devR.status === "fulfilled") setDevices(devR.value);
      if (dsR.status === "fulfilled") setDatasets(dsR.value.datasets || []);
      if (evR.status === "fulfilled") setEvaluations(evR.value.results || []);
      if (cmpR.status === "fulfilled") setComparisons(cmpR.value.comparisons || []);
      if (rf0R.status === "fulfilled") setRfBase(rf0R.value);
      if (rf25R.status === "fulfilled") setRfAug(rf25R.value);
      if (amR.status === "fulfilled") {
        setCustomModels((amR.value.models || []).filter((m) => m.is_custom));
      }
    } catch (e: any) {
      setError(e.message || "Failed to load Executive Workbench.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWorkbench();
  }, []);

  const totalGeneratedRows = datasets.reduce((acc, d) => acc + (d.num_records || 0), 0);
  const trainRows = ctganMeta?.training_metadata?.train_rows ?? 88146;
  const valRows = ctganMeta?.training_metadata?.val_rows ?? 18889;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="IoTSynth AI · Signal Intelligence Studio"
        title="Executive System Workbench"
        description="Synthetic IoT network telemetry platform featuring CTGAN V2 (primary native device-aware generator across 70 physical devices) and CTGAN V1 (baseline comparison) over 8 CICIoT2023 traffic categories."
        statusSlot={
          systemStatus ? (
            <StatusIndicator tone="success" label={`API v${systemStatus.app_version} Online`} />
          ) : null
        }
        actionSlot={
          <Link href="/studio">
            <PrimaryButton type="button">
              <Sparkles className="h-4 w-4" />
              Open Synthetic Data Studio
              <ArrowRight className="h-4 w-4" />
            </PrimaryButton>
          </Link>
        }
      />

      {error && <ErrorState message={error} onRetry={loadWorkbench} />}

      {loading ? (
        <div className="space-y-6">
          <LoadingSkeleton rows={2} />
          <LoadingSkeleton rows={4} />
        </div>
      ) : (
        <>
          {/* Concise System Inventory Strip */}
          <section
            aria-label="Verified system inventory"
            className="grid grid-cols-2 gap-3.5 lg:grid-cols-4"
          >
            <div className="studio-panel p-4">
              <div className="flex items-center justify-between text-xs font-semibold text-ink-secondary">
                <span>Real Training / Validation</span>
                <Layers className="h-4 w-4 text-brand" aria-hidden="true" />
              </div>
              <div className="mt-1.5 font-mono text-xl font-bold text-ink tabular-nums">
                {fmtNumber(trainRows)} / {fmtNumber(valRows)}
              </div>
              <div className="mt-0.5 text-[11px] text-ink-secondary">
                V2 PCAP corpus (70 devices · +18,889 test)
              </div>
            </div>

            <div className="studio-panel p-4">
              <div className="flex items-center justify-between text-xs font-semibold text-ink-secondary">
                <span>Stored Synthetic Flows</span>
                <Database className="h-4 w-4 text-signal" aria-hidden="true" />
              </div>
              <div className="mt-1.5 font-mono text-xl font-bold text-signal tabular-nums">
                {fmtNumber(totalGeneratedRows)}
              </div>
              <div className="mt-0.5 text-[11px] text-ink-secondary">
                Across {datasets.length} vaulted dataset(s)
              </div>
            </div>

            <div className="studio-panel p-4">
              <div className="flex items-center justify-between text-xs font-semibold text-ink-secondary">
                <span>CTGAN &amp; Threat Scope</span>
                <Cpu className="h-4 w-4 text-signal-lavender" aria-hidden="true" />
              </div>
              <div className="mt-1.5 font-mono text-xl font-bold text-ink tabular-nums">
                {modelsStatus?.ctgan_models_count ?? 1} Model · 8 Classes
              </div>
              <div className="mt-0.5 text-[11px] text-ink-secondary">
                32 attack signatures + Benign in corpus
              </div>
            </div>

            <div className="studio-panel p-4">
              <div className="flex items-center justify-between text-xs font-semibold text-ink-secondary">
                <span>Anomaly Detectors Ready</span>
                <ShieldCheck className="h-4 w-4 text-[#1A7D5E]" aria-hidden="true" />
              </div>
              <div className="mt-1.5 font-mono text-xl font-bold text-ink tabular-nums">
                {modelsStatus?.anomaly_models_count ?? 20} Pipelines
              </div>
              <div className="mt-0.5 text-[11px] text-ink-secondary">
                4 classifier families · lazy cached
              </div>
            </div>
          </section>

          <PipelineFlow
            systemStatus={systemStatus}
            modelsStatus={modelsStatus}
            datasetCount={datasets.length}
            evalCount={evaluations.length}
          />

          <BenchmarkLedger
            comparisons={comparisons}
            rfBaseline={rfBase}
            rfAugmented={rfAug}
          />

          <DeviceFleetGrid
            devices={devices}
            datasets={datasets}
            evaluations={evaluations}
            customModels={customModels}
          />
        </>
      )}
    </div>
  );
}
