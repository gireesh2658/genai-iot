"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { BrainCircuit, Play, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import {
  AnomalyModelDetail,
  AnomalyModelSummary,
  ExperimentComparisonRecord,
} from "@/lib/types";
import { PageHeader } from "@/components/layout/PageHeader";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { ErrorState, LoadingSkeleton } from "@/components/ui/StateViews";
import { StatusIndicator } from "@/components/ui/StatusIndicator";
import { Tabs } from "@/components/ui/Tabs";
import { useToast } from "@/components/ui/ToastProvider";
import { LeaderboardMatrix } from "@/components/anomaly/LeaderboardMatrix";
import { PerClassConfusionView } from "@/components/anomaly/PerClassConfusionView";
import { CustomDetectorTrainer } from "@/components/anomaly/CustomDetectorTrainer";
import { LiveFlowClassifier } from "@/components/anomaly/LiveFlowClassifier";

function AnomalyLabInner() {
  const searchParams = useSearchParams();
  const initialDataset = searchParams.get("dataset");
  const { pushToast } = useToast();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [tab, setTab] = useState<"leaderboard" | "trainer" | "classifier">(
    initialDataset ? "trainer" : "leaderboard"
  );
  const [models, setModels] = useState<AnomalyModelSummary[]>([]);
  const [selectedModelId, setSelectedModelId] = useState("random_forest_tstr_r_25");
  const [modelDetail, setModelDetail] = useState<AnomalyModelDetail | null>(null);
  const [comparisons, setComparisons] = useState<ExperimentComparisonRecord[]>([]);
  const [synthDatasets, setSynthDatasets] = useState<string[]>([]);

  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);

  const loadAll = async (focusModel?: string) => {
    setError(null);
    try {
      const [mRes, cRes, eRes] = await Promise.all([
        api.listAnomalyModels(),
        api.compareAnomalyExperiments(),
        api.getEvaluationStatus(),
      ]);
      setModels(mRes.models || []);
      setComparisons(cRes.comparisons || []);
      setSynthDatasets(eRes.available_synthetic_datasets || []);

      const targetId = focusModel || selectedModelId;
      const d = await api.getAnomalyModelDetail(targetId);
      setModelDetail(d);
    } catch (e: any) {
      setError(e.message || "Failed to load Anomaly Detection Lab.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const handleSelectModel = async (id: string) => {
    setSelectedModelId(id);
    try {
      const d = await api.getAnomalyModelDetail(id);
      setModelDetail(d);
    } catch (e: any) {
      pushToast("error", "Could not inspect model", e.message);
    }
  };

  const handleConfirmDelete = async () => {
    if (!confirmDeleteId) return;
    setDeleteBusy(true);
    try {
      await api.deleteCustomModel(confirmDeleteId);
      const fallback = "random_forest_tstr_r_25";
      setSelectedModelId(fallback);
      await loadAll(fallback);
      pushToast("success", "Deleted custom detector", confirmDeleteId);
      setConfirmDeleteId(null);
    } catch (e: any) {
      pushToast("error", "Could not delete detector", e.message);
    } finally {
      setDeleteBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Downstream Machine Learning Utility"
        title="Anomaly Detection Lab"
        description="Evaluate whether synthetic CTGAN telemetry strengthens real-world multi-class intrusion detection across TRTR, TSTR, and TSTR+R paradigms on 9,616 held-out real flows."
        statusSlot={
          <StatusIndicator
            tone="info"
            label={`${models.length} Registered Detectors · 38 Canonical Inputs`}
          />
        }
        actionSlot={
          <Tabs
            activeId={tab}
            onChange={setTab}
            items={[
              { id: "leaderboard", label: "Benchmarks & 8×8 Matrix", icon: ShieldCheck },
              { id: "trainer", label: "Custom Trainer", icon: BrainCircuit },
              { id: "classifier", label: "Live Classifier", icon: Play },
            ]}
          />
        }
      />

      {error && <ErrorState message={error} onRetry={() => loadAll()} />}

      {loading ? (
        <LoadingSkeleton rows={6} />
      ) : (
        <>
          {tab === "leaderboard" && (
            <div className="space-y-6">
              <LeaderboardMatrix
                models={models}
                selectedModelId={selectedModelId}
                comparisons={comparisons}
                onSelectModel={handleSelectModel}
                onRequestDeleteModel={(id) => setConfirmDeleteId(id)}
              />
              <PerClassConfusionView modelDetail={modelDetail} />
            </div>
          )}

          {tab === "trainer" && (
            <CustomDetectorTrainer
              synthDatasets={synthDatasets}
              initialDataset={initialDataset}
              onTrained={(res) => {
                setSelectedModelId(res.model_id);
                loadAll(res.model_id);
              }}
            />
          )}

          {tab === "classifier" && (
            <LiveFlowClassifier
              models={models}
              selectedModelId={selectedModelId}
              onChangeModelId={handleSelectModel}
            />
          )}
        </>
      )}

      <ConfirmDialog
        open={Boolean(confirmDeleteId)}
        title="Delete Custom Anomaly Detector?"
        description={
          confirmDeleteId
            ? `Permanently delete custom trained detector '${confirmDeleteId}' and its saved confusion matrix? Protected Phase 7 baseline models cannot be deleted.`
            : ""
        }
        busy={deleteBusy}
        onCancel={() => !deleteBusy && setConfirmDeleteId(null)}
        onConfirm={handleConfirmDelete}
      />
    </div>
  );
}

export default function AnomalyPage() {
  return (
    <Suspense fallback={<LoadingSkeleton rows={6} />}>
      <AnomalyLabInner />
    </Suspense>
  );
}
