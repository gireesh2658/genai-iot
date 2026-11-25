"use client";

import React, { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowUpRight, BarChart3, CheckCircle2, Database, Table2 } from "lucide-react";
import { api } from "@/lib/api";
import {
  AttackProfileSummary,
  CTGANGenerateResponse,
  CTGANModelSummary,
  DatasetDetail,
  DatasetItem,
  IoTDeviceProfile,
  V2DeviceCatalogResponse,
} from "@/lib/types";
import { PageHeader } from "@/components/layout/PageHeader";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { ExportMenu } from "@/components/ui/ExportMenu";
import { ErrorState, LoadingSkeleton } from "@/components/ui/StateViews";
import { StatusIndicator } from "@/components/ui/StatusIndicator";
import { Tabs } from "@/components/ui/Tabs";
import { useToast } from "@/components/ui/ToastProvider";
import {
  GenerationConfigPanel,
  GenerationMode,
  SAFE_BALANCED_QUOTAS,
} from "@/components/studio/GenerationConfigPanel";
import { TrainCtganModal } from "@/components/studio/TrainCtganModal";
import { TelemetryCharts } from "@/components/studio/TelemetryCharts";
import { FlowDataTable } from "@/components/studio/FlowDataTable";
import { FlowInspectorDrawer } from "@/components/studio/FlowInspectorDrawer";
import { DatasetVaultPanel } from "@/components/studio/DatasetVaultPanel";

function StudioInner() {
  const searchParams = useSearchParams();
  const deviceParam = searchParams.get("device");
  const { pushToast } = useToast();

  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [models, setModels] = useState<CTGANModelSummary[]>([]);
  const [devices, setDevices] = useState<IoTDeviceProfile[]>([]);
  const [v2Catalog, setV2Catalog] = useState<V2DeviceCatalogResponse | null>(null);
  const [attackProfiles, setAttackProfiles] = useState<AttackProfileSummary[]>([]);
  const [datasets, setDatasets] = useState<DatasetItem[]>([]);

  // Generator Configuration (V2 primary default)
  const [modelId, setModelId] = useState("ctgan_device_aware_v2");
  const [selectedDevices, setSelectedDevices] = useState<string[]>([
    "smart_camera",
    "smart_thermostat",
    "motion_sensor",
    "smart_plug",
    "smart_bulb",
    "smart_speaker",
  ]);
  const [v2DeviceCategory, setV2DeviceCategory] = useState("Camera");
  const [v2DeviceId, setV2DeviceId] = useState("ANY");
  const [mode, setMode] = useState<GenerationMode>("quotas");
  const [quotas, setQuotas] = useState<Record<string, number>>(SAFE_BALANCED_QUOTAS);
  const [numRecords, setNumRecords] = useState(500);
  const [attackConditionType, setAttackConditionType] = useState<"category" | "raw">("category");
  const [selectedAttackCategory, setSelectedAttackCategory] = useState("DDoS");
  const [selectedRawAttack, setSelectedRawAttack] = useState("DDOS-SYN_FLOOD");
  const [applyDomainCorrection, setApplyDomainCorrection] = useState(true);
  const [applyDeviceCalibration, setApplyDeviceCalibration] = useState(true);
  const [exportDataset, setExportDataset] = useState(true);
  const [exportFormat, setExportFormat] = useState<"both" | "parquet" | "csv">("both");
  const [exportPrefix, setExportPrefix] = useState("iot_synthetic_v2");

  // Workspace Data & Interactive UI State
  const [genResult, setGenResult] = useState<CTGANGenerateResponse | null>(null);
  const [inspectedDataset, setInspectedDataset] = useState<DatasetDetail | null>(null);
  const [activeTab, setActiveTab] = useState<"analytics" | "inspector" | "vault">("analytics");
  const [drawerRecord, setDrawerRecord] = useState<Record<string, any> | null>(null);

  const [trainModalOpen, setTrainModalOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<{
    type: "dataset" | "model";
    id: string;
  } | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [generateBusy, setGenerateBusy] = useState(false);

  useEffect(() => {
    if (deviceParam) {
      setSelectedDevices([deviceParam]);
      setApplyDeviceCalibration(true);
      const v1ToV2CategoryMap: Record<string, string> = {
        smart_camera: "Camera",
        smart_speaker: "Audio",
        smart_plug: "Power Outlet",
        smart_bulb: "Lighting",
        smart_thermostat: "Home Automation",
        motion_sensor: "Home Automation",
      };
      const mapped = v1ToV2CategoryMap[deviceParam];
      if (mapped) {
        setV2DeviceCategory(mapped);
        setV2DeviceId("ANY");
      }
    }
  }, [deviceParam]);

  const handleModelChange = (nextModelId: string) => {
    setModelId(nextModelId);
    if (exportPrefix === "iot_synthetic_v2" || exportPrefix === "ctgan_iot_synth" || exportPrefix === "ctgan_v1_baseline") {
      setExportPrefix(nextModelId === "ctgan_device_aware_v2" ? "iot_synthetic_v2" : "ctgan_iot_synth");
    }
  };

  const loadWorkspace = async (preserveActive = true) => {
    setLoadError(null);
    try {
      const [mRes, pRes, v2Res, aRes, dRes] = await Promise.all([
        api.listCtganModels(),
        api.listDeviceProfiles(),
        api.listV2Devices(),
        api.listAttackProfiles(),
        api.listDatasets(),
      ]);
      const mList = mRes.models || [];
      setModels(mList);
      setDevices(pRes || []);
      setV2Catalog(v2Res || null);
      setAttackProfiles(aRes || []);
      const dsList = dRes.datasets || [];
      setDatasets(dsList);

      if (mList.length > 0 && !mList.some((m) => m.model_id === modelId)) {
        const fallbackModel =
          mList.find((m) => m.is_primary) || mList[0];
        if (fallbackModel) setModelId(fallbackModel.model_id);
      }

      if ((!preserveActive || (!genResult && !inspectedDataset)) && dsList.length > 0) {
        const preferred =
          dsList.find((d) => d.dataset_id === "ctgan_initial_sample_v1_domain_corrected") ||
          dsList[0];
        if (preferred) {
          const detail = await api.getDatasetDetail(preferred.dataset_id, 80);
          setInspectedDataset(detail);
        }
      }
    } catch (e: any) {
      setLoadError(e.message || "Unable to load CTGAN workspace from FastAPI backend.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWorkspace(false);
  }, []);

  const selectedModelMeta = models.find((m) => m.model_id === modelId);
  const isNativeV2Model = Boolean(
    selectedModelMeta?.is_primary ||
      modelId === "ctgan_device_aware_v2" ||
      (selectedModelMeta?.discrete_columns_count && selectedModelMeta.discrete_columns_count <= 7)
  );

  const handleGenerate = async () => {
    setGenerateBusy(true);
    try {
      const totalQuota = Object.values(quotas).reduce((acc, v) => acc + (Number(v) || 0), 0);
      const canCalibrate = !isNativeV2Model && applyDeviceCalibration && selectedDevices.length > 0;
      const defaultPrefix = isNativeV2Model ? "iot_synthetic_v2" : "ctgan_iot_synth";

      const payload: any = {
        model_id: modelId,
        num_records: mode === "quotas" ? totalQuota : numRecords,
        device_profiles: canCalibrate ? selectedDevices : null,
        apply_device_calibration: canCalibrate,
        apply_domain_correction: applyDomainCorrection,
        max_records_to_return: 80,
        export_dataset: exportDataset,
        export_format: exportFormat,
        export_filename_prefix: exportDataset ? exportPrefix.trim() || defaultPrefix : undefined,
      };

      const conditions: Record<string, any> = {};
      if (isNativeV2Model) {
        if (v2DeviceCategory && v2DeviceCategory !== "ALL") {
          conditions.device_category = v2DeviceCategory;
        }
        if (v2DeviceId && v2DeviceId !== "ANY") {
          conditions.device_id = v2DeviceId;
        }
      }

      if (mode === "quotas") {
        payload.category_counts = quotas;
      } else if (mode === "normal") {
        conditions.label_category = "Benign";
        conditions.is_attack = 0;
      } else if (mode === "attack") {
        if (attackConditionType === "category") {
          conditions.label_category = selectedAttackCategory;
          conditions.is_attack = 1;
        } else {
          conditions.label_raw = selectedRawAttack;
          conditions.is_attack = 1;
        }
      }

      if (Object.keys(conditions).length > 0) {
        payload.conditions = conditions;
      }

      const res = await api.generateCtganTraffic(payload);
      setGenResult(res);
      setInspectedDataset(null);
      await loadWorkspace(true);

      pushToast(
        "success",
        `Generated ${res.total_generated.toLocaleString()} IoT flows in ${res.generation_time_sec}s`,
        res.dataset_id ? `Saved to Vault as '${res.dataset_id}'` : "In-memory preview updated"
      );
    } catch (e: any) {
      pushToast("error", "Synthesis failed", e.message);
    } finally {
      setGenerateBusy(false);
    }
  };

  const handleInspectDataset = async (datasetId: string) => {
    try {
      const detail = await api.getDatasetDetail(datasetId, 80);
      setInspectedDataset(detail);
      setGenResult(null);
      setActiveTab("analytics");
      pushToast("info", "Loaded Vault dataset", `Previewing ${detail.preview_records.length} of ${detail.num_records} rows from '${datasetId}'`);
    } catch (e: any) {
      pushToast("error", "Could not load dataset", e.message);
    }
  };

  const executeConfirmedDelete = async () => {
    if (!confirmDelete) return;
    setDeleteBusy(true);
    try {
      if (confirmDelete.type === "dataset") {
        await api.deleteDataset(confirmDelete.id);
        if (inspectedDataset?.dataset_id === confirmDelete.id) setInspectedDataset(null);
        if (genResult?.dataset_id === confirmDelete.id) setGenResult(null);
        pushToast("success", "Dataset deleted", confirmDelete.id);
      } else {
        await api.deleteCtganModel(confirmDelete.id);
        if (modelId === confirmDelete.id) setModelId("ctgan_device_aware_v2");
        pushToast("success", "CTGAN checkpoint deleted", confirmDelete.id);
      }
      await loadWorkspace(true);
      setConfirmDelete(null);
    } catch (e: any) {
      pushToast("error", "Delete failed", e.message);
    } finally {
      setDeleteBusy(false);
    }
  };

  // Derive active view metrics accurately
  const activeDatasetId = genResult?.dataset_id || inspectedDataset?.dataset_id || null;
  const activeRecords = genResult?.records || inspectedDataset?.preview_records || [];
  const activeTotal = genResult?.total_generated || inspectedDataset?.num_records || 0;
  const activeCols = genResult?.features_count || inspectedDataset?.num_columns || 42;

  const categoryDistribution: Record<string, number> =
    genResult?.category_distribution ||
    inspectedDataset?.metadata?.category_distribution ||
    inspectedDataset?.metadata?.macro_category_counts ||
    activeRecords.reduce((acc: Record<string, number>, r) => {
      const k = String(r.label_category || "Unknown");
      acc[k] = (acc[k] || 0) + 1;
      return acc;
    }, {});

  const deviceDistribution: Record<string, number> =
    genResult?.device_distribution ||
    inspectedDataset?.metadata?.device_distribution ||
    activeRecords.reduce((acc: Record<string, number>, r) => {
      if (r.device_category) {
        const k = String(r.device_category);
        acc[k] = (acc[k] || 0) + 1;
      }
      return acc;
    }, {});

  const repairSummary =
    genResult?.domain_correction_summary ||
    inspectedDataset?.metadata?.domain_correction_summary ||
    null;

  const activeVaultItem = datasets.find((d) => d.dataset_id === activeDatasetId);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Synthetic Data Workbench"
        title="Synthetic IoT Traffic Generator"
        description="Generate realistic normal and attack IoT network telemetry using a trained CTGAN model with conditional threat sampling, deterministic domain repair, and post-hoc device calibration."
        statusSlot={
          selectedModelMeta ? (
            <StatusIndicator
              tone="synthetic"
              label={`Model: ${selectedModelMeta.model_id} (${selectedModelMeta.epochs} ep)`}
            />
          ) : null
        }
      />

      {loadError && <ErrorState message={loadError} onRetry={() => loadWorkspace(false)} />}

      {loading ? (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
          <div className="xl:col-span-4">
            <LoadingSkeleton rows={6} />
          </div>
          <div className="xl:col-span-8">
            <LoadingSkeleton rows={6} />
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
          {/* Left Workbench Config Panel */}
          <div className="xl:col-span-4">
            <GenerationConfigPanel
              models={models}
              devices={devices}
              v2Catalog={v2Catalog}
              attackProfiles={attackProfiles}
              modelId={modelId}
              onChangeModelId={handleModelChange}
              onOpenTrainModal={() => setTrainModalOpen(true)}
              onRequestDeleteModel={(id) => setConfirmDelete({ type: "model", id })}
              selectedDevices={selectedDevices}
              onChangeDevices={setSelectedDevices}
              v2DeviceCategory={v2DeviceCategory}
              onChangeV2DeviceCategory={setV2DeviceCategory}
              v2DeviceId={v2DeviceId}
              onChangeV2DeviceId={setV2DeviceId}
              mode={mode}
              onChangeMode={setMode}
              quotas={quotas}
              onChangeQuotas={setQuotas}
              numRecords={numRecords}
              onChangeNumRecords={setNumRecords}
              attackConditionType={attackConditionType}
              onChangeAttackConditionType={setAttackConditionType}
              selectedAttackCategory={selectedAttackCategory}
              onChangeSelectedAttackCategory={setSelectedAttackCategory}
              selectedRawAttack={selectedRawAttack}
              onChangeSelectedRawAttack={setSelectedRawAttack}
              applyDomainCorrection={applyDomainCorrection}
              onChangeApplyDomainCorrection={setApplyDomainCorrection}
              applyDeviceCalibration={applyDeviceCalibration}
              onChangeApplyDeviceCalibration={setApplyDeviceCalibration}
              exportDataset={exportDataset}
              onChangeExportDataset={setExportDataset}
              exportFormat={exportFormat}
              onChangeExportFormat={setExportFormat}
              exportPrefix={exportPrefix}
              onChangeExportPrefix={setExportPrefix}
              busy={generateBusy}
              onGenerate={handleGenerate}
            />
          </div>

          {/* Right Output Workspace */}
          <div className="space-y-5 xl:col-span-8">
            {/* Active Result Summary Header */}
            <section className="studio-panel p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusIndicator
                      tone={genResult ? "success" : "info"}
                      label={genResult ? "Fresh CTGAN Synthesis" : "Loaded Vault Baseline"}
                    />
                    {activeDatasetId && (
                      <span className="rounded-md border border-hairline bg-canvas px-2 py-0.5 font-mono text-xs font-semibold text-ink">
                        {activeDatasetId}
                      </span>
                    )}
                  </div>

                  <div className="mt-2.5 flex flex-wrap items-baseline gap-4 tabular-nums">
                    <span className="text-2xl font-bold text-ink">
                      {activeTotal.toLocaleString()}{" "}
                      <span className="text-sm font-medium text-ink-secondary">total flows</span>
                    </span>
                    <span className="font-mono text-xs font-semibold text-ink-secondary">
                      {activeCols} columns
                    </span>
                    <span className="font-mono text-xs font-semibold text-ink-secondary">
                      Previewing {activeRecords.length} rows
                    </span>
                    {genResult?.model_id && (
                      <span className="rounded-md border border-[#C4DBFA] bg-[#EAF2FD] px-2 py-0.5 font-mono text-[11px] font-semibold text-brand">
                        {genResult.model_id}
                      </span>
                    )}
                    {genResult?.conditions_applied?.device_category && (
                      <span className="rounded-md border border-[#BBE5DF] bg-[#E7F7F5] px-2 py-0.5 font-mono text-[11px] font-semibold text-signal">
                        Device: {String(genResult.conditions_applied.device_category)}
                        {genResult.conditions_applied.device_id
                          ? ` (${String(genResult.conditions_applied.device_id)})`
                          : ""}
                      </span>
                    )}
                    {genResult?.generation_time_sec !== undefined && (
                      <span className="font-mono text-xs font-semibold text-signal">
                        {genResult.generation_time_sec}s runtime
                      </span>
                    )}
                  </div>
                </div>

                {(activeDatasetId || activeRecords.length > 0) && (
                  <div className="flex flex-wrap items-center gap-2">
                    <ExportMenu
                      datasetId={activeDatasetId}
                      records={activeRecords}
                      fallbackFilename={exportPrefix.trim() || `${modelId}_preview`}
                      availableFormats={activeVaultItem?.available_formats || ["csv", "parquet"]}
                    />
                    {activeDatasetId && (
                      <>
                        <Link
                          href={`/quality?dataset=${encodeURIComponent(activeDatasetId)}`}
                          className="inline-flex min-h-[34px] items-center gap-1 rounded-[10px] border border-hairline bg-well/60 px-3 py-1 text-xs font-semibold text-brand hover:border-[#C4DBFA] hover:bg-brand-tint"
                        >
                          Run Quality Audit <ArrowUpRight className="h-3.5 w-3.5" />
                        </Link>
                        <Link
                          href={`/anomaly?dataset=${encodeURIComponent(activeDatasetId)}`}
                          className="inline-flex min-h-[34px] items-center gap-1 rounded-[10px] border border-hairline bg-well/60 px-3 py-1 text-xs font-semibold text-signal hover:border-[#BBE5DF] hover:bg-[#E7F7F5]"
                        >
                          Train Detector <ArrowUpRight className="h-3.5 w-3.5" />
                        </Link>
                      </>
                    )}
                  </div>
                )}
              </div>

              {repairSummary && (
                <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-hairline pt-3 text-[11px]">
                  <span className="inline-flex items-center gap-1 font-bold text-[#1A7D5E]">
                    <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                    Domain Corrections Fixed:
                  </span>
                  {Object.entries(repairSummary).map(([k, v]) => (
                    <span
                      key={k}
                      className="rounded-md border border-hairline bg-well px-2 py-0.5 font-mono text-ink"
                    >
                      {k.replace(/_fixed/g, "").replace(/_/g, " ")}: <strong>{String(v)}</strong>
                    </span>
                  ))}
                </div>
              )}

              <div className="mt-4 border-t border-hairline pt-4">
                <Tabs
                  activeId={activeTab}
                  onChange={setActiveTab}
                  items={[
                    { id: "analytics", label: "Telemetry Visualizations", icon: BarChart3 },
                    {
                      id: "inspector",
                      label: "Flow Inspector",
                      badge: activeRecords.length,
                      icon: Table2,
                    },
                    {
                      id: "vault",
                      label: "Dataset Vault & Attacks",
                      badge: datasets.length,
                      icon: Database,
                    },
                  ]}
                />
              </div>
            </section>

            {activeTab === "analytics" && (
              <TelemetryCharts
                records={activeRecords}
                totalRecords={activeTotal}
                categoryDistribution={categoryDistribution}
                deviceDistribution={deviceDistribution}
              />
            )}

            {activeTab === "inspector" && (
              <FlowDataTable
                records={activeRecords}
                totalRecords={activeTotal}
                onInspectRecord={(r) => setDrawerRecord(r)}
              />
            )}

            {activeTab === "vault" && (
              <DatasetVaultPanel
                datasets={datasets}
                attackProfiles={attackProfiles}
                activeDatasetId={activeDatasetId}
                onInspectDataset={handleInspectDataset}
                onRequestDeleteDataset={(id) => setConfirmDelete({ type: "dataset", id })}
                onRefresh={() => loadWorkspace(true)}
              />
            )}
          </div>
        </div>
      )}

      <TrainCtganModal
        open={trainModalOpen}
        onClose={() => setTrainModalOpen(false)}
        onSuccess={(res) => {
          setModelId(res.model_id);
          loadWorkspace(true);
        }}
      />

      <FlowInspectorDrawer
        record={drawerRecord}
        onClose={() => setDrawerRecord(null)}
      />

      <ConfirmDialog
        open={Boolean(confirmDelete)}
        title={
          confirmDelete?.type === "dataset"
            ? "Delete Generated Dataset?"
            : "Delete Custom CTGAN Checkpoint?"
        }
        description={
          confirmDelete
            ? `Permanently delete '${confirmDelete.id}' from disk? Baseline protected checkpoints and datasets cannot be deleted.`
            : ""
        }
        busy={deleteBusy}
        onCancel={() => !deleteBusy && setConfirmDelete(null)}
        onConfirm={executeConfirmedDelete}
      />
    </div>
  );
}

export default function StudioPage() {
  return (
    <Suspense fallback={<LoadingSkeleton rows={6} />}>
      <StudioInner />
    </Suspense>
  );
}
