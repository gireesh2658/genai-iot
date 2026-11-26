"use client";

import React, { useEffect, useState } from "react";
import { FileSpreadsheet, Loader2, Package } from "lucide-react";
import { api } from "@/lib/api";
import {
  AttackProfileSummary,
  CTGANGenerateResponse,
  CTGANModelSummary,
  EvaluationRunResponse,
  IoTDeviceProfileSummary,
  V2DeviceCatalogResponse,
} from "@/lib/types";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/ui/StateViews";
import { StatusIndicator } from "@/components/ui/StatusIndicator";
import {
  ALL_TRAFFIC_CATEGORIES,
  buildCategoryQuotas,
  GenerationConfigPanel,
  GenerationStrategy,
} from "@/components/studio/GenerationConfigPanel";
import { FlowDataTable } from "@/components/studio/FlowDataTable";
import { FlowInspectorDrawer } from "@/components/studio/FlowInspectorDrawer";
import { ValidationPanel } from "@/components/studio/ValidationPanel";

export default function StudioPage() {
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [models, setModels] = useState<CTGANModelSummary[]>([]);
  const [v2Catalog, setV2Catalog] = useState<V2DeviceCatalogResponse | null>(null);
  const [v1DeviceProfiles, setV1DeviceProfiles] = useState<IoTDeviceProfileSummary[]>([]);
  const [attackProfiles, setAttackProfiles] = useState<AttackProfileSummary[]>([]);

  // Configuration state
  const [modelId, setModelId] = useState("ctgan_device_aware_v2");
  const [v2DeviceCategory, setV2DeviceCategory] = useState("Camera");
  const [v2DeviceId, setV2DeviceId] = useState("ANY");
  const [v1CalibrateDevices, setV1CalibrateDevices] = useState(false);
  const [v1DeviceProfile, setV1DeviceProfile] = useState("ALL");
  const [strategy, setStrategy] = useState<GenerationStrategy>("balanced");
  const [boostRareClasses, setBoostRareClasses] = useState(false);
  const [numRecordsInput, setNumRecordsInput] = useState("500");
  const [attackConditionType, setAttackConditionType] = useState<"category" | "raw">("category");
  const [selectedAttackCategory, setSelectedAttackCategory] = useState("DDoS");
  const [selectedRawAttack, setSelectedRawAttack] = useState("DDOS-SYN_FLOOD");
  const [applyDomainCorrection, setApplyDomainCorrection] = useState(true);

  // Generation & Evaluation states
  const [generateBusy, setGenerateBusy] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);
  const [genResult, setGenResult] = useState<CTGANGenerateResponse | null>(null);
  const [drawerRecord, setDrawerRecord] = useState<Record<string, any> | null>(null);

  const [evalBusy, setEvalBusy] = useState(false);
  const [evalError, setEvalError] = useState<string | null>(null);
  const [evalResult, setEvalResult] = useState<EvaluationRunResponse | null>(null);

  const loadCatalog = async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const [mRes, v2Res, pRes, aRes] = await Promise.all([
        api.listCtganModels(),
        api.listV2Devices(),
        api.listDeviceProfiles(),
        api.listAttackProfiles(),
      ]);
      const mList = mRes.models || [];
      setModels(mList);
      setV2Catalog(v2Res || null);
      setV1DeviceProfiles(pRes || []);
      setAttackProfiles(aRes || []);

      const primary =
        mList.find((m) => m.model_id === "ctgan_device_aware_v2") ||
        mList.find((m) => m.is_primary) ||
        mList[0];
      if (primary) {
        setModelId(primary.model_id);
      }
    } catch (e: any) {
      setLoadError(
        e.message || "Unable to connect to the IoTSynth AI backend service."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCatalog();
  }, []);

  // Keep selected device_category, strategy, and attack choices valid when device_id changes
  const handleChangeV2DeviceId = (nextDevId: string) => {
    setV2DeviceId(nextDevId);
    if (nextDevId === "ANY" || !v2Catalog) return;

    const matched = v2Catalog.devices.find((d) => d.device_id === nextDevId);
    if (!matched) return;

    if (matched.device_category !== v2DeviceCategory) {
      setV2DeviceCategory(matched.device_category);
    }

    if (strategy === "balanced") {
      setStrategy("general");
    } else if (
      strategy === "normal" &&
      !matched.supported_label_categories.includes("Benign")
    ) {
      setStrategy("general");
    }

    const supportedAttacks = ALL_TRAFFIC_CATEGORIES.filter(
      (c) => c !== "Benign" && matched.supported_label_categories.includes(c)
    );
    if (
      supportedAttacks.length > 0 &&
      !supportedAttacks.includes(selectedAttackCategory as any)
    ) {
      setSelectedAttackCategory(supportedAttacks[0]);
    } else if (supportedAttacks.length === 0 && strategy === "attack") {
      setStrategy("general");
    }

    const validRaw = attackProfiles.filter(
      (atk) =>
        atk.label_raw !== "UPLOADING_ATTACK" &&
        matched.supported_label_categories.includes(atk.label_category)
    );
    if (
      validRaw.length > 0 &&
      !validRaw.some((atk) => atk.label_raw === selectedRawAttack)
    ) {
      setSelectedRawAttack(validRaw[0].label_raw);
    }
  };

  const selectedModelMeta = models.find((m) => m.model_id === modelId) || null;
  const isV2DeviceModel =
    modelId === "ctgan_device_aware_v2" ||
    ((selectedModelMeta?.feature_columns_count ?? 0) >= 44 && modelId !== "ctgan_full_v1");

  const handleChangeModelId = (nextId: string) => {
    setModelId(nextId);
    setGenerateError(null);
    setEvalError(null);
  };

  const handleGenerate = async () => {
    const parsedCount = Number(numRecordsInput);
    if (
      numRecordsInput.trim() === "" ||
      !Number.isInteger(parsedCount) ||
      parsedCount < 1 ||
      parsedCount > 10000
    ) {
      setGenerateError("Record count must be a whole number between 1 and 10,000.");
      return;
    }

    setGenerateBusy(true);
    setGenerateError(null);
    setEvalError(null);
    setEvalResult(null);

    try {
      const conditions: Record<string, any> = {};
      if (isV2DeviceModel) {
        if (v2DeviceCategory && v2DeviceCategory !== "ALL") {
          conditions.device_category = v2DeviceCategory;
        }
        if (v2DeviceId && v2DeviceId !== "ANY") {
          const devMeta = v2Catalog?.devices.find((d) => d.device_id === v2DeviceId);
          if (devMeta) {
            conditions.device_category = devMeta.device_category;
          }
          conditions.device_id = v2DeviceId;
        }
      }

      const payload: any = {
        model_id: modelId,
        num_records: parsedCount,
        apply_device_calibration: !isV2DeviceModel && v1CalibrateDevices,
        apply_domain_correction: applyDomainCorrection,
        max_records_to_return: 80,
        export_dataset: true,
        export_format: "both",
        export_filename_prefix: isV2DeviceModel
          ? "iot_synthetic_v2"
          : modelId === "ctgan_full_v1"
          ? "iot_synthetic_v1"
          : `iot_synthetic_${modelId}`,
      };

      if (!isV2DeviceModel && v1CalibrateDevices && v1DeviceProfile !== "ALL") {
        payload.device_profiles = [v1DeviceProfile];
      }

      if (strategy === "balanced") {
        payload.category_counts = buildCategoryQuotas(parsedCount, boostRareClasses);
      } else if (strategy === "normal") {
        conditions.label_category = "Benign";
        conditions.is_attack = 0;
      } else if (strategy === "attack") {
        if (attackConditionType === "category") {
          conditions.label_category = selectedAttackCategory;
        } else {
          conditions.label_raw = selectedRawAttack;
        }
        conditions.is_attack = 1;
      }

      if (Object.keys(conditions).length > 0) {
        payload.conditions = conditions;
      }

      const res = await api.generateCtganTraffic(payload);
      setGenResult(res);
    } catch (e: any) {
      setGenerateError(e.message || "Synthetic traffic generation failed.");
    } finally {
      setGenerateBusy(false);
    }
  };

  const handleRunEvaluation = async () => {
    if (!genResult?.dataset_id) return;
    setEvalBusy(true);
    setEvalError(null);
    try {
      const refId =
        genResult.model_id === "ctgan_device_aware_v2"
          ? "ciciot2023_device_v2_train"
          : "ciciot2023_preprocessed_sample";
      const res = await api.runEvaluation({
        reference_dataset_id: refId,
        synthetic_dataset_id: genResult.dataset_id,
        generate_plots: false,
        generate_corrected_dataset: false,
        test_conditional_sampling: false,
      });
      setEvalResult(res);
    } catch (e: any) {
      setEvalError(e.message || "Statistical quality evaluation failed.");
    } finally {
      setEvalBusy(false);
    }
  };

  const activeCategoryEntries = genResult
    ? Object.entries(genResult.category_distribution || {}).sort((a, b) => b[1] - a[1])
    : [];

  return (
    <div className="space-y-6">
      <div className="border-b border-hairline pb-4">
        <h1 className="text-xl font-bold tracking-tight text-ink sm:text-2xl">
          Synthetic IoT Traffic Generator
        </h1>
        <p className="mt-1 text-sm text-ink-secondary">
          Generate synthetic normal and attack IoT network traffic using CTGAN V2 (device-aware) or CTGAN V1 (baseline), inspect sample flows, audit quality, and export CSV or Parquet.
        </p>
      </div>

      {loadError && <ErrorState message={loadError} onRetry={loadCatalog} />}

      {loading ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <div className="lg:col-span-4">
            <LoadingSkeleton rows={6} />
          </div>
          <div className="lg:col-span-8">
            <LoadingSkeleton rows={6} />
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 lg:items-start">
          {/* Left Configuration Column */}
          <div className="lg:col-span-4">
            <GenerationConfigPanel
              models={models}
              modelId={modelId}
              onChangeModelId={handleChangeModelId}
              isV2DeviceModel={isV2DeviceModel}
              v2Catalog={v2Catalog}
              v1DeviceProfiles={v1DeviceProfiles}
              attackProfiles={attackProfiles}
              v2DeviceCategory={v2DeviceCategory}
              onChangeV2DeviceCategory={setV2DeviceCategory}
              v2DeviceId={v2DeviceId}
              onChangeV2DeviceId={handleChangeV2DeviceId}
              v1CalibrateDevices={v1CalibrateDevices}
              onChangeV1CalibrateDevices={setV1CalibrateDevices}
              v1DeviceProfile={v1DeviceProfile}
              onChangeV1DeviceProfile={setV1DeviceProfile}
              strategy={strategy}
              onChangeStrategy={setStrategy}
              boostRareClasses={boostRareClasses}
              onChangeBoostRareClasses={setBoostRareClasses}
              numRecordsInput={numRecordsInput}
              onChangeNumRecordsInput={setNumRecordsInput}
              attackConditionType={attackConditionType}
              onChangeAttackConditionType={setAttackConditionType}
              selectedAttackCategory={selectedAttackCategory}
              onChangeSelectedAttackCategory={setSelectedAttackCategory}
              selectedRawAttack={selectedRawAttack}
              onChangeSelectedRawAttack={setSelectedRawAttack}
              applyDomainCorrection={applyDomainCorrection}
              onChangeApplyDomainCorrection={setApplyDomainCorrection}
              busy={generateBusy}
              modelAvailable={models.some((m) => m.model_id === modelId)}
              onGenerate={handleGenerate}
            />
          </div>

          {/* Right Output Column */}
          <div className="space-y-5 lg:col-span-8">
            {generateError && (
              <ErrorState
                title="Generation Failed"
                message={generateError}
                onRetry={handleGenerate}
              />
            )}

            {generateBusy && (
              <div
                role="status"
                aria-live="polite"
                className="studio-panel flex items-center gap-3 p-5 text-sm text-ink"
              >
                <Loader2 className="h-5 w-5 shrink-0 animate-spin text-brand" aria-hidden="true" />
                <div>
                  <div className="font-semibold">Generating synthetic IoT traffic...</div>
                  <p className="text-xs text-ink-secondary">
                    Sampling conditional {modelId} flows and applying domain consistency checks.
                  </p>
                </div>
              </div>
            )}

            {!generateBusy && !genResult && !generateError && (
              <div className="studio-panel p-6">
                <EmptyState
                  title="Ready to Generate"
                  description="Select an IoT device category, traffic strategy, and record count on the left, then click Generate Synthetic Data."
                />
              </div>
            )}

            {!generateBusy && genResult && (
              <>
                {/* Compact Result Summary & Export Actions */}
                <section className="studio-panel space-y-4 p-5" aria-label="Generation summary">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="space-y-1.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <StatusIndicator tone="success" label="Generation Successful" />
                        <span className="rounded-md border border-hairline bg-well px-2 py-0.5 font-mono text-[11px] font-semibold text-ink">
                          {genResult.model_id}
                        </span>
                        <span className="font-mono text-xs text-ink-secondary tabular-nums">
                          {genResult.generation_time_sec}s
                        </span>
                      </div>

                      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 tabular-nums">
                        <span className="text-xl font-bold text-ink">
                          {genResult.total_generated.toLocaleString()}{" "}
                          <span className="text-sm font-medium text-ink-secondary">
                            records
                          </span>
                        </span>
                        <span className="font-mono text-xs font-semibold text-ink-secondary">
                          {genResult.features_count} columns
                        </span>
                        {genResult.conditions_applied?.device_category && (
                          <span className="font-mono text-xs font-semibold text-signal">
                            Device: {String(genResult.conditions_applied.device_category)}
                            {genResult.conditions_applied.device_id
                              ? ` (${String(genResult.conditions_applied.device_id)})`
                              : ""}
                          </span>
                        )}
                      </div>
                    </div>

                    {genResult.dataset_id && (
                      <div className="flex flex-wrap items-center gap-2">
                        {(!genResult.exported_files || genResult.exported_files.csv) && (
                          <a
                            href={api.datasetDownloadUrl(genResult.dataset_id, "csv")}
                            download
                            className="inline-flex min-h-[38px] items-center gap-1.5 rounded-[10px] border border-[#CFD8D3] bg-surface px-3.5 py-1.5 text-xs font-semibold text-ink transition hover:border-brand/40 hover:bg-well/70"
                          >
                            <FileSpreadsheet className="h-3.5 w-3.5 text-signal" aria-hidden="true" />
                            Download CSV
                          </a>
                        )}
                        {(!genResult.exported_files || genResult.exported_files.parquet) && (
                          <a
                            href={api.datasetDownloadUrl(genResult.dataset_id, "parquet")}
                            download
                            className="inline-flex min-h-[38px] items-center gap-1.5 rounded-[10px] border border-[#CFD8D3] bg-surface px-3.5 py-1.5 text-xs font-semibold text-ink transition hover:border-brand/40 hover:bg-well/70"
                          >
                            <Package className="h-3.5 w-3.5 text-brand" aria-hidden="true" />
                            Download Parquet
                          </a>
                        )}
                      </div>
                    )}
                  </div>

                  {activeCategoryEntries.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1.5 border-t border-hairline pt-3 text-[11px]">
                      <span className="mr-1 font-semibold text-ink-secondary">
                        Class Breakdown:
                      </span>
                      {activeCategoryEntries.map(([cls, count]) => (
                        <span
                          key={cls}
                          className="rounded-md border border-hairline bg-canvas px-2 py-0.5 font-mono text-ink tabular-nums"
                        >
                          {cls}: <strong>{count.toLocaleString()}</strong>
                        </span>
                      ))}
                    </div>
                  )}
                </section>

                {/* Preview Table */}
                <FlowDataTable
                  records={genResult.records || []}
                  totalRecords={genResult.total_generated}
                  onInspectRecord={(r) => setDrawerRecord(r)}
                />

                {/* Compact Expandable Quality & Validation Checks */}
                <ValidationPanel
                  genResult={genResult}
                  evalResult={evalResult}
                  evalBusy={evalBusy}
                  evalError={evalError}
                  onRunEvaluation={handleRunEvaluation}
                />
              </>
            )}
          </div>
        </div>
      )}

      <FlowInspectorDrawer
        record={drawerRecord}
        onClose={() => setDrawerRecord(null)}
      />
    </div>
  );
}
