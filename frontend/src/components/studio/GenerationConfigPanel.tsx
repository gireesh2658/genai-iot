"use client";

import React, { useMemo, useState } from "react";
import { ChevronDown, ChevronUp, Plus, SlidersHorizontal, Sparkles, Trash2 } from "lucide-react";
import {
  AttackProfileSummary,
  CTGANModelSummary,
  IoTDeviceProfile,
  V2DeviceCatalogResponse,
} from "@/lib/types";
import { fmtDeviceName } from "@/lib/formatters";
import { IconButton, PrimaryButton, SecondaryButton } from "@/components/ui/Button";
import { InfoTooltip } from "@/components/ui/InfoTooltip";

export type GenerationMode = "quotas" | "normal" | "attack" | "general";

export const SAFE_BALANCED_QUOTAS: Record<string, number> = {
  Benign: 150,
  "Brute Force": 40,
  "Web-based": 50,
  Spoofing: 120,
  Reconnaissance: 150,
  Mirai: 130,
  DoS: 180,
  DDoS: 180,
};

export const RARE_BOOST_QUOTAS: Record<string, number> = {
  Benign: 120,
  "Brute Force": 60,
  "Web-based": 70,
  Spoofing: 140,
  Reconnaissance: 140,
  Mirai: 90,
  DoS: 90,
  DDoS: 90,
};

const CATEGORIES = [
  "Benign",
  "Brute Force",
  "Web-based",
  "Spoofing",
  "Reconnaissance",
  "Mirai",
  "DoS",
  "DDoS",
];

const MODE_DESCRIPTIONS: Record<GenerationMode, string> = {
  quotas: "Specify exact row counts across all 8 threat categories to rebalance rare attacks cleanly.",
  normal: "Generate strictly Benign traffic (`is_attack=0`) calibrated to selected IoT devices.",
  attack: "Condition CTGAN on a chosen attack family or fine-grained raw CICIoT2023 signature.",
  general: "Sample freely from CTGAN's learned joint distribution matching CICIoT2023 class priors.",
};

export function GenerationConfigPanel({
  models,
  devices,
  v2Catalog,
  attackProfiles,
  modelId,
  onChangeModelId,
  onOpenTrainModal,
  onRequestDeleteModel,
  selectedDevices,
  onChangeDevices,
  v2DeviceCategory,
  onChangeV2DeviceCategory,
  v2DeviceId,
  onChangeV2DeviceId,
  mode,
  onChangeMode,
  quotas,
  onChangeQuotas,
  numRecords,
  onChangeNumRecords,
  attackConditionType,
  onChangeAttackConditionType,
  selectedAttackCategory,
  onChangeSelectedAttackCategory,
  selectedRawAttack,
  onChangeSelectedRawAttack,
  applyDomainCorrection,
  onChangeApplyDomainCorrection,
  applyDeviceCalibration,
  onChangeApplyDeviceCalibration,
  exportDataset,
  onChangeExportDataset,
  exportFormat,
  onChangeExportFormat,
  exportPrefix,
  onChangeExportPrefix,
  busy,
  onGenerate,
}: {
  models: CTGANModelSummary[];
  devices: IoTDeviceProfile[];
  v2Catalog: V2DeviceCatalogResponse | null;
  attackProfiles: AttackProfileSummary[];
  modelId: string;
  onChangeModelId: (id: string) => void;
  onOpenTrainModal: () => void;
  onRequestDeleteModel: (id: string) => void;
  selectedDevices: string[];
  onChangeDevices: (devs: string[]) => void;
  v2DeviceCategory: string;
  onChangeV2DeviceCategory: (cat: string) => void;
  v2DeviceId: string;
  onChangeV2DeviceId: (id: string) => void;
  mode: GenerationMode;
  onChangeMode: (m: GenerationMode) => void;
  quotas: Record<string, number>;
  onChangeQuotas: (q: Record<string, number>) => void;
  numRecords: number;
  onChangeNumRecords: (n: number) => void;
  attackConditionType: "category" | "raw";
  onChangeAttackConditionType: (t: "category" | "raw") => void;
  selectedAttackCategory: string;
  onChangeSelectedAttackCategory: (c: string) => void;
  selectedRawAttack: string;
  onChangeSelectedRawAttack: (r: string) => void;
  applyDomainCorrection: boolean;
  onChangeApplyDomainCorrection: (b: boolean) => void;
  applyDeviceCalibration: boolean;
  onChangeApplyDeviceCalibration: (b: boolean) => void;
  exportDataset: boolean;
  onChangeExportDataset: (b: boolean) => void;
  exportFormat: "both" | "parquet" | "csv";
  onChangeExportFormat: (f: "both" | "parquet" | "csv") => void;
  exportPrefix: string;
  onChangeExportPrefix: (s: string) => void;
  busy: boolean;
  onGenerate: () => void;
}) {
  const [advancedOpen, setAdvancedOpen] = useState(false);

  const activeModel = models.find((m) => m.model_id === modelId);
  const isNativeV2Model = Boolean(
    activeModel?.is_primary ||
      modelId === "ctgan_device_aware_v2" ||
      (activeModel?.discrete_columns_count && activeModel.discrete_columns_count <= 7)
  );
  const filteredV2Devices = useMemo(() => {
    const all = v2Catalog?.devices || [];
    if (v2DeviceCategory === "ALL") return all;
    return all.filter((d) => d.device_category === v2DeviceCategory);
  }, [v2Catalog, v2DeviceCategory]);
  const selectedV2DeviceMeta = useMemo(
    () => (v2DeviceId !== "ANY" ? filteredV2Devices.find((d) => d.device_id === v2DeviceId) || null : null),
    [filteredV2Devices, v2DeviceId]
  );
  const totalQuotaRows = useMemo(
    () => Object.values(quotas).reduce((acc, v) => acc + (Number(v) || 0), 0),
    [quotas]
  );

  const effectiveCount = mode === "quotas" ? totalQuotaRows : numRecords;
  const countInvalid = effectiveCount < 1 || effectiveCount > 10000;
  const prefixInvalid =
    exportDataset && exportPrefix.trim() !== "" && !/^[a-zA-Z0-9_-]+$/.test(exportPrefix.trim());

  const toggleDevice = (name: string) => {
    onChangeDevices(
      selectedDevices.includes(name)
        ? selectedDevices.filter((x) => x !== name)
        : [...selectedDevices, name]
    );
  };

  return (
    <aside className="studio-panel space-y-5 p-5" aria-label="Synthetic generation configuration">
      {/* Section 1: CTGAN Checkpoint */}
      <div className="space-y-2">
        <div className="flex items-center justify-between gap-2">
          <label htmlFor="ctgan-model-select" className="text-xs font-bold uppercase tracking-wider text-ink-secondary">
            1. Generative Model <InfoTooltip term="CTGAN" />
          </label>
          <SecondaryButton type="button" size="sm" onClick={onOpenTrainModal}>
            <Plus className="h-3.5 w-3.5" /> Train Checkpoint
          </SecondaryButton>
        </div>

        <div className="flex items-center gap-2">
          <select
            id="ctgan-model-select"
            value={modelId}
            onChange={(e) => onChangeModelId(e.target.value)}
            className="studio-input flex-1 font-medium"
          >
            {models.map((m) => (
              <option key={m.model_id} value={m.model_id}>
                {m.model_id}{" "}
                {m.is_primary
                  ? "(Primary V2)"
                  : m.model_id === "ctgan_full_v1"
                  ? "(Baseline V1)"
                  : "(Custom)"}
                {" · "}
                {m.epochs} epochs ({m.training_rows?.toLocaleString() ?? "--"} rows)
              </option>
            ))}
          </select>
          {activeModel?.is_custom && (
            <IconButton
              label={`Delete custom checkpoint ${activeModel.model_id}`}
              onClick={() => onRequestDeleteModel(activeModel.model_id)}
              className="border-hairline hover:border-[#F2C3BF] hover:bg-[#FDECEC] hover:text-[#BF4840]"
            >
              <Trash2 className="h-4 w-4" />
            </IconButton>
          )}
        </div>

        {activeModel && (
          <p className="text-[11px] leading-snug text-ink-secondary tabular-nums">
            <span className="font-mono">
              Trained: {activeModel.device.toUpperCase()} · Serving:{" "}
              {(activeModel.serving_device || "cpu").toUpperCase()}
            </span>{" "}
            · {activeModel.feature_columns_count ?? (isNativeV2Model ? 44 : 42)} cols (
            {activeModel.discrete_columns_count ?? (isNativeV2Model ? 7 : 25)} discrete ·{" "}
            {activeModel.cond_vector_dim ?? (isNativeV2Model ? 130 : 992)}-dim cond vector)
          </p>
        )}
      </div>

      {/* Section 2: Generation Mode */}
      <div className="space-y-2.5 border-t border-hairline pt-4">
        <div className="text-xs font-bold uppercase tracking-wider text-ink-secondary">
          2. Sampling Mode <InfoTooltip term="Conditional Sampling" />
        </div>

        <div className="grid grid-cols-2 gap-1.5 rounded-xl border border-hairline bg-well p-1 text-xs font-semibold">
          {(
            [
              { id: "quotas", label: "Category Quotas" },
              { id: "normal", label: "Normal Traffic" },
              { id: "attack", label: "Attack Category" },
              { id: "general", label: "General Prior" },
            ] as const
          ).map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onChangeMode(item.id)}
              className={`min-h-[34px] rounded-lg px-2 py-1.5 text-center transition ${
                mode === item.id
                  ? "bg-surface text-brand shadow-sm ring-1 ring-hairline"
                  : "text-ink-secondary hover:text-ink"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        <p className="rounded-lg border border-[#C4DBFA] bg-[#EAF2FD]/70 px-3 py-2 text-[11px] leading-relaxed text-[#1E4F8A]">
          {MODE_DESCRIPTIONS[mode]}
        </p>

        {mode === "quotas" ? (
          <div className="studio-well space-y-3 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-[11px] font-semibold text-ink-secondary">Presets:</span>
              <div className="flex gap-1.5">
                <button
                  type="button"
                  onClick={() => onChangeQuotas(SAFE_BALANCED_QUOTAS)}
                  className="rounded-md border border-hairline bg-surface px-2 py-1 text-[11px] font-semibold text-ink hover:border-brand"
                >
                  Balanced 1,000
                </button>
                <button
                  type="button"
                  onClick={() => onChangeQuotas(RARE_BOOST_QUOTAS)}
                  className="rounded-md border border-hairline bg-surface px-2 py-1 text-[11px] font-semibold text-ink hover:border-brand"
                >
                  Rare Boost 800
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              {CATEGORIES.map((cat) => (
                <label
                  key={cat}
                  className="block rounded-lg border border-hairline bg-surface px-2.5 py-1.5 focus-within:border-brand"
                >
                  <span className="block truncate text-[11px] font-semibold text-ink-secondary">
                    {cat}
                  </span>
                  <input
                    type="number"
                    min={0}
                    max={10000}
                    step={10}
                    value={quotas[cat] ?? 0}
                    onChange={(e) =>
                      onChangeQuotas({
                        ...quotas,
                        [cat]: Math.max(0, Number(e.target.value) || 0),
                      })
                    }
                    className="mt-0.5 w-full bg-transparent font-mono text-sm font-bold text-ink focus:outline-none tabular-nums"
                  />
                </label>
              ))}
            </div>

            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-ink-secondary">Batch Total (1–10,000)</span>
              <span
                className={`font-mono font-bold tabular-nums ${
                  countInvalid ? "text-[#BF4840]" : "text-brand"
                }`}
              >
                {totalQuotaRows.toLocaleString()} flows
              </span>
            </div>
          </div>
        ) : (
          <div className="studio-well space-y-3 p-3">
            <div>
              <label htmlFor="num-records-input" className="mb-1 block text-[11px] font-semibold text-ink-secondary">
                Number of Records (1–10,000)
              </label>
              <input
                id="num-records-input"
                type="number"
                min={1}
                max={10000}
                step={50}
                value={numRecords}
                onChange={(e) => onChangeNumRecords(Number(e.target.value) || 0)}
                className="studio-input font-mono text-sm tabular-nums"
              />
            </div>

            {mode === "attack" && (
              <div className="space-y-2">
                <div className="flex gap-3 text-xs font-semibold text-ink-secondary">
                  <label className="flex cursor-pointer items-center gap-1.5">
                    <input
                      type="radio"
                      checked={attackConditionType === "category"}
                      onChange={() => onChangeAttackConditionType("category")}
                    />
                    Macro Family
                  </label>
                  <label className="flex cursor-pointer items-center gap-1.5">
                    <input
                      type="radio"
                      checked={attackConditionType === "raw"}
                      onChange={() => onChangeAttackConditionType("raw")}
                    />
                    Specific Signature
                  </label>
                </div>

                {attackConditionType === "category" ? (
                  <select
                    aria-label="Select macro attack category"
                    value={selectedAttackCategory}
                    onChange={(e) => onChangeSelectedAttackCategory(e.target.value)}
                    className="studio-input text-xs"
                  >
                    {CATEGORIES.filter((c) => c !== "Benign").map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                ) : (
                  <select
                    aria-label="Select raw CICIoT2023 attack label"
                    value={selectedRawAttack}
                    onChange={(e) => onChangeSelectedRawAttack(e.target.value)}
                    className="studio-input font-mono text-xs"
                  >
                    {attackProfiles.map((atk) => (
                      <option key={atk.attack_id} value={atk.label_raw}>
                        {atk.label_raw} ({atk.label_category})
                      </option>
                    ))}
                  </select>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Section 3: IoT Device Conditioning / Calibration */}
      {isNativeV2Model ? (
        <div className="space-y-3 border-t border-hairline pt-4">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-secondary">
              3. Native IoT Device Conditioning (V2)
            </span>
            {v2DeviceCategory !== "ALL" && (
              <button
                type="button"
                onClick={() => {
                  onChangeV2DeviceCategory("ALL");
                  onChangeV2DeviceId("ANY");
                }}
                className="text-xs font-semibold text-brand hover:underline"
              >
                Reset Filter
              </button>
            )}
          </div>

          <div className="studio-well space-y-2.5 p-3">
            <div>
              <label
                htmlFor="v2-device-category-select"
                className="mb-1 block text-[11px] font-semibold text-ink-secondary"
              >
                IoT Device Category ({v2Catalog?.device_categories?.length ?? 7} Hardware Families)
              </label>
              <select
                id="v2-device-category-select"
                value={v2DeviceCategory}
                onChange={(e) => {
                  onChangeV2DeviceCategory(e.target.value);
                  onChangeV2DeviceId("ANY");
                }}
                className="studio-input text-xs font-medium"
              >
                <option value="ALL">All 7 Hardware Categories (Natural V2 Prior)</option>
                {(v2Catalog?.device_categories || []).map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label
                htmlFor="v2-device-id-select"
                className="mb-1 block text-[11px] font-semibold text-ink-secondary"
              >
                Physical Device ID ({filteredV2Devices.length} Pseudonymized Devices)
              </label>
              <select
                id="v2-device-id-select"
                value={v2DeviceId}
                onChange={(e) => {
                  const chosen = e.target.value;
                  onChangeV2DeviceId(chosen);
                  if (chosen !== "ANY") {
                    const matched = (v2Catalog?.devices || []).find((d) => d.device_id === chosen);
                    if (matched && v2DeviceCategory === "ALL") {
                      onChangeV2DeviceCategory(matched.device_category);
                    }
                  }
                }}
                className="studio-input font-mono text-xs"
              >
                <option value="ANY">
                  {v2DeviceCategory === "ALL"
                    ? "Any Device Across Testbed (70 IDs)"
                    : `Any ${v2DeviceCategory} Device (${filteredV2Devices.length} IDs)`}
                </option>
                {filteredV2Devices.map((d) => (
                  <option key={d.device_id} value={d.device_id}>
                    {d.device_id} · {d.device_name} ({d.supported_label_categories.length}/8 classes)
                  </option>
                ))}
              </select>
            </div>

            {selectedV2DeviceMeta && (
              <div className="rounded-lg border border-[#C4DBFA] bg-[#EAF2FD]/70 px-2.5 py-2 text-[11px] text-[#1E4F8A]">
                <div className="font-semibold">
                  {selectedV2DeviceMeta.device_id} · {selectedV2DeviceMeta.device_name} (
                  {selectedV2DeviceMeta.testbed_role})
                </div>
                <div className="mt-0.5 text-[10px]">
                  Category: <strong>{selectedV2DeviceMeta.device_category}</strong> · Train rows:{" "}
                  {selectedV2DeviceMeta.train_row_count.toLocaleString()} · Classes:{" "}
                  {selectedV2DeviceMeta.supported_label_categories.join(", ")}
                </div>
              </div>
            )}
          </div>

          <p className="text-[11px] leading-snug text-ink-secondary">
            Learned natively inside CTGAN V2 from CICIoT2023 PCAPs (zero raw MAC/IP exposure).
            Category-level selection supports all 8 classes in every sampling mode.
          </p>
        </div>
      ) : (
        <div className="space-y-2 border-t border-hairline pt-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-secondary">
              3. IoT Device Profiles (V1 Post-Hoc Calibration)
            </span>
            <button
              type="button"
              onClick={() =>
                onChangeDevices(
                  selectedDevices.length === devices.length
                    ? []
                    : devices.map((d) => d.profile_name)
                )
              }
              className="text-xs font-semibold text-brand hover:underline"
            >
              {selectedDevices.length === devices.length
                ? "Clear All"
                : `Select All (${devices.length})`}
            </button>
          </div>

          <div className="grid grid-cols-2 gap-2">
            {devices.map((dev) => {
              const checked = selectedDevices.includes(dev.profile_name);
              return (
                <button
                  key={dev.profile_name}
                  type="button"
                  aria-pressed={checked}
                  disabled={!applyDeviceCalibration}
                  onClick={() => toggleDevice(dev.profile_name)}
                  className={`rounded-xl border p-2.5 text-left transition disabled:opacity-50 ${
                    checked && applyDeviceCalibration
                      ? "border-brand bg-brand-tint/60"
                      : "border-hairline bg-surface hover:border-[#B8C4BE]"
                  }`}
                >
                  <div className="flex items-center justify-between gap-1">
                    <span className="truncate text-xs font-bold text-ink">
                      {fmtDeviceName(dev.profile_name)}
                    </span>
                    <span
                      className={`h-2 w-2 shrink-0 rounded-full ${
                        checked && applyDeviceCalibration ? "bg-brand" : "bg-[#CBD5DF]"
                      }`}
                    />
                  </div>
                  <div className="mt-0.5 font-mono text-[10px] text-ink-secondary tabular-nums">
                    {dev.packet_size_min}–{dev.packet_size_max}B · {dev.traffic_rate_min}–
                    {dev.traffic_rate_max}/s
                  </div>
                </button>
              );
            })}
          </div>
          <p className="text-[11px] leading-snug text-ink-secondary">
            Applies post-hoc hardware bounds on benign sensor flows and assigns node IDs (`_01..03`).
          </p>
        </div>
      )}

      {/* Section 4: Collapsible Advanced Settings */}
      <div className="border-t border-hairline pt-3">
        <button
          type="button"
          aria-expanded={advancedOpen}
          onClick={() => setAdvancedOpen((v) => !v)}
          className="flex min-h-[36px] w-full items-center justify-between rounded-lg px-1 py-1 text-xs font-bold text-ink-secondary hover:text-ink"
        >
          <span className="flex items-center gap-1.5">
            <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden="true" />
            Advanced Calibration &amp; Export Settings
          </span>
          {advancedOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>

        {advancedOpen && (
          <div className="mt-2.5 space-y-2.5 rounded-xl border border-hairline bg-well/60 p-3 text-xs">
            <label className="flex cursor-pointer items-start gap-2">
              <input
                type="checkbox"
                checked={applyDomainCorrection}
                onChange={(e) => onChangeApplyDomainCorrection(e.target.checked)}
                className="mt-0.5"
              />
              <span>
                <strong className="text-ink">Enforce Domain Repair</strong>
                <span className="block text-[11px] text-ink-secondary">
                  Aligns label hierarchy, IANA protocol names &amp; Std = sqrt(Variance)
                </span>
              </span>
            </label>

            <label className="flex cursor-pointer items-start gap-2">
              <input
                type="checkbox"
                checked={isNativeV2Model ? false : applyDeviceCalibration}
                disabled={isNativeV2Model}
                onChange={(e) => onChangeApplyDeviceCalibration(e.target.checked)}
                className="mt-0.5"
              />
              <span>
                <strong className="text-ink">
                  Post-Hoc IoT Device Calibration ({isNativeV2Model ? "V1 Only" : "44 Cols"})
                </strong>
                <span className="block text-[11px] text-ink-secondary">
                  {isNativeV2Model
                    ? "Skipped automatically because V2 generates native 44-col device IDs & categories inside CTGAN"
                    : "Uncheck to output raw 42-col CICIoT2023 feature schema only"}
                </span>
              </span>
            </label>

            <div className="space-y-2 border-t border-hairline pt-2">
              <label className="flex cursor-pointer items-center gap-2 font-semibold text-ink">
                <input
                  type="checkbox"
                  checked={exportDataset}
                  onChange={(e) => onChangeExportDataset(e.target.checked)}
                />
                Save dataset to Vault (`datasets/generated/`)
              </label>

              {exportDataset && (
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label htmlFor="export-format" className="mb-1 block text-[10px] font-semibold text-ink-secondary">
                      Export Format
                    </label>
                    <select
                      id="export-format"
                      value={exportFormat}
                      onChange={(e) => onChangeExportFormat(e.target.value as any)}
                      className="studio-input py-1.5 text-xs"
                    >
                      <option value="both">Parquet + CSV</option>
                      <option value="parquet">Parquet Only</option>
                      <option value="csv">CSV Only</option>
                    </select>
                  </div>
                  <div>
                    <label htmlFor="export-prefix" className="mb-1 block text-[10px] font-semibold text-ink-secondary">
                      Filename Prefix
                    </label>
                    <input
                      id="export-prefix"
                      value={exportPrefix}
                      onChange={(e) => onChangeExportPrefix(e.target.value)}
                      className="studio-input py-1.5 font-mono text-xs"
                    />
                  </div>
                </div>
              )}
              {prefixInvalid && (
                <p className="text-[11px] font-semibold text-[#BF4840]">
                  Prefix may only use letters, digits, hyphens, and underscores.
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Inline Validation Message & ONE Primary Generate Action */}
      {countInvalid && (
        <p role="alert" className="text-xs font-semibold text-[#BF4840]">
          Total sample count must be between 1 and 10,000 flows.
        </p>
      )}

      <PrimaryButton
        type="button"
        loading={busy}
        disabled={countInvalid || prefixInvalid || models.length === 0}
        onClick={onGenerate}
        className="w-full"
      >
        <Sparkles className="h-4 w-4" />
        {busy
          ? "Synthesizing CTGAN Telemetry..."
          : `Synthesize ${effectiveCount.toLocaleString()} Flows`}
      </PrimaryButton>
    </aside>
  );
}
