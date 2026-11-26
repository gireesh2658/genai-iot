"use client";

import React, { useMemo } from "react";
import { Cpu, Sparkles } from "lucide-react";
import {
  AttackProfileSummary,
  CTGANModelSummary,
  IoTDeviceProfileSummary,
  V2DeviceCatalogResponse,
} from "@/lib/types";
import { PrimaryButton } from "@/components/ui/Button";

export type GenerationStrategy = "balanced" | "normal" | "attack" | "general";

export const ALL_TRAFFIC_CATEGORIES = [
  "Benign",
  "Brute Force",
  "Web-based",
  "Spoofing",
  "Reconnaissance",
  "Mirai",
  "DoS",
  "DDoS",
] as const;

const EVEN_WEIGHTS: Record<string, number> = {
  Benign: 150,
  "Brute Force": 40,
  "Web-based": 50,
  Spoofing: 120,
  Reconnaissance: 150,
  Mirai: 130,
  DoS: 180,
  DDoS: 180,
};

const RARE_BOOST_WEIGHTS: Record<string, number> = {
  Benign: 120,
  "Brute Force": 60,
  "Web-based": 70,
  Spoofing: 140,
  Reconnaissance: 140,
  Mirai: 90,
  DoS: 90,
  DDoS: 90,
};

/** Allocate integer category_counts summing cleanly to totalRows using largest remainder. */
export function buildCategoryQuotas(
  totalRows: number,
  boostRareClasses: boolean
): Record<string, number> {
  const weights = boostRareClasses ? RARE_BOOST_WEIGHTS : EVEN_WEIGHTS;
  const entries = ALL_TRAFFIC_CATEGORIES.map((cat) => [cat, weights[cat]] as const);
  const weightSum = entries.reduce((acc, [, w]) => acc + w, 0);

  const exact = entries.map(([cat, w]) => {
    const raw = (totalRows * w) / weightSum;
    const base = Math.floor(raw);
    return { cat, base, rem: raw - base };
  });

  let remaining = totalRows - exact.reduce((acc, x) => acc + x.base, 0);
  const byRemainder = [...exact].sort((a, b) => b.rem - a.rem);
  for (let i = 0; i < byRemainder.length && remaining > 0; i++) {
    byRemainder[i].base += 1;
    remaining -= 1;
  }

  const out: Record<string, number> = {};
  for (const item of exact) {
    if (item.base > 0) {
      out[item.cat] = item.base;
    }
  }
  return out;
}

const RECORD_PRESETS = [100, 500, 1000, 5000] as const;

export function GenerationConfigPanel({
  models,
  modelId,
  onChangeModelId,
  isV2DeviceModel,
  v2Catalog,
  v1DeviceProfiles,
  attackProfiles,
  v2DeviceCategory,
  onChangeV2DeviceCategory,
  v2DeviceId,
  onChangeV2DeviceId,
  v1CalibrateDevices,
  onChangeV1CalibrateDevices,
  v1DeviceProfile,
  onChangeV1DeviceProfile,
  strategy,
  onChangeStrategy,
  boostRareClasses,
  onChangeBoostRareClasses,
  numRecordsInput,
  onChangeNumRecordsInput,
  attackConditionType,
  onChangeAttackConditionType,
  selectedAttackCategory,
  onChangeSelectedAttackCategory,
  selectedRawAttack,
  onChangeSelectedRawAttack,
  applyDomainCorrection,
  onChangeApplyDomainCorrection,
  busy,
  modelAvailable,
  onGenerate,
}: {
  models: CTGANModelSummary[];
  modelId: string;
  onChangeModelId: (id: string) => void;
  isV2DeviceModel: boolean;
  v2Catalog: V2DeviceCatalogResponse | null;
  v1DeviceProfiles: IoTDeviceProfileSummary[];
  attackProfiles: AttackProfileSummary[];
  v2DeviceCategory: string;
  onChangeV2DeviceCategory: (cat: string) => void;
  v2DeviceId: string;
  onChangeV2DeviceId: (id: string) => void;
  v1CalibrateDevices: boolean;
  onChangeV1CalibrateDevices: (b: boolean) => void;
  v1DeviceProfile: string;
  onChangeV1DeviceProfile: (p: string) => void;
  strategy: GenerationStrategy;
  onChangeStrategy: (s: GenerationStrategy) => void;
  boostRareClasses: boolean;
  onChangeBoostRareClasses: (b: boolean) => void;
  numRecordsInput: string;
  onChangeNumRecordsInput: (val: string) => void;
  attackConditionType: "category" | "raw";
  onChangeAttackConditionType: (t: "category" | "raw") => void;
  selectedAttackCategory: string;
  onChangeSelectedAttackCategory: (c: string) => void;
  selectedRawAttack: string;
  onChangeSelectedRawAttack: (r: string) => void;
  applyDomainCorrection: boolean;
  onChangeApplyDomainCorrection: (b: boolean) => void;
  busy: boolean;
  modelAvailable: boolean;
  onGenerate: () => void;
}) {
  const orderedModels = useMemo(() => {
    const rank = (m: CTGANModelSummary) =>
      m.model_id === "ctgan_device_aware_v2"
        ? 0
        : m.model_id === "ctgan_full_v1"
        ? 1
        : 2;
    return [...models].sort((a, b) => rank(a) - rank(b));
  }, [models]);

  const filteredDevices = useMemo(() => {
    const all = v2Catalog?.devices || [];
    if (v2DeviceCategory === "ALL") return all;
    return all.filter((d) => d.device_category === v2DeviceCategory);
  }, [v2Catalog, v2DeviceCategory]);

  const selectedDeviceMeta = useMemo(
    () =>
      isV2DeviceModel && v2DeviceId !== "ANY"
        ? (v2Catalog?.devices || []).find((d) => d.device_id === v2DeviceId) || null
        : null,
    [isV2DeviceModel, v2Catalog, v2DeviceId]
  );

  const supportsNormal =
    !selectedDeviceMeta ||
    selectedDeviceMeta.supported_label_categories.includes("Benign");

  const supportedAttackCategories = useMemo(() => {
    const allAttacks = ALL_TRAFFIC_CATEGORIES.filter((c) => c !== "Benign");
    if (!selectedDeviceMeta) return allAttacks;
    return allAttacks.filter((c) =>
      selectedDeviceMeta.supported_label_categories.includes(c)
    );
  }, [selectedDeviceMeta]);

  const supportedAttackSignatures = useMemo(() => {
    return attackProfiles.filter((atk) => {
      if (atk.label_raw === "UPLOADING_ATTACK") return false;
      if (!selectedDeviceMeta) return true;
      return selectedDeviceMeta.supported_label_categories.includes(atk.label_category);
    });
  }, [attackProfiles, selectedDeviceMeta]);

  const parsedCount = Number(numRecordsInput);
  const countValid =
    numRecordsInput.trim() !== "" &&
    Number.isInteger(parsedCount) &&
    parsedCount >= 1 &&
    parsedCount <= 10000;

  const quotaPreview = useMemo(() => {
    if (strategy !== "balanced" || !countValid) return null;
    return buildCategoryQuotas(parsedCount, boostRareClasses);
  }, [strategy, countValid, parsedCount, boostRareClasses]);

  const isSingleDevice = isV2DeviceModel && v2DeviceId !== "ANY";

  return (
    <aside
      className="studio-panel space-y-5 p-5"
      aria-label="Synthetic IoT traffic generation configuration"
    >
      <div>
        <h2 className="text-base font-bold text-ink">Generation Configuration</h2>
        <p className="mt-0.5 text-xs text-ink-secondary">
          Select a trained CTGAN model, conditioning mode, traffic strategy, and batch size.
        </p>
      </div>

      {/* 0. Model Selection */}
      <div className="space-y-2 border-t border-hairline pt-4">
        <div className="flex items-center justify-between gap-2 text-xs font-semibold text-ink-secondary">
          <span className="inline-flex items-center gap-1.5">
            <Cpu className="h-3.5 w-3.5 text-brand" aria-hidden="true" />
            Generative Model Checkpoint
          </span>
          <span className="font-mono text-[10px] text-ink-muted">
            {orderedModels.length} available
          </span>
        </div>

        <div
          role="radiogroup"
          aria-label="Select trained CTGAN model"
          className="space-y-1.5"
        >
          {orderedModels.map((m) => {
            const active = m.model_id === modelId;
            const title =
              m.model_id === "ctgan_device_aware_v2"
                ? "CTGAN V2 (Device-Aware)"
                : m.model_id === "ctgan_full_v1"
                ? "CTGAN V1 (Baseline)"
                : m.model_id;
            const badge =
              m.model_id === "ctgan_device_aware_v2"
                ? "Primary"
                : m.model_id === "ctgan_full_v1"
                ? "Baseline"
                : "Custom";
            const spec = `${m.feature_columns_count ?? 42} cols · ${
              m.training_rows ? m.training_rows.toLocaleString() : "?"
            } train flows · ${m.epochs} epochs`;

            return (
              <button
                key={m.model_id}
                type="button"
                role="radio"
                aria-checked={active}
                disabled={busy}
                onClick={() => onChangeModelId(m.model_id)}
                className={`w-full rounded-xl border px-3 py-2 text-left transition disabled:cursor-not-allowed disabled:opacity-50 ${
                  active
                    ? "border-brand bg-brand-tint/60 shadow-sm ring-1 ring-brand/25"
                    : "border-hairline bg-surface hover:border-brand/40 hover:bg-well/40"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-bold text-ink">{title}</span>
                  <span
                    className={`rounded-full px-2 py-0.5 font-mono text-[10px] font-semibold ${
                      active
                        ? "bg-brand text-white"
                        : "border border-hairline bg-well text-ink-secondary"
                    }`}
                  >
                    {badge}
                  </span>
                </div>
                <div className="mt-0.5 font-mono text-[10px] text-ink-secondary tabular-nums">
                  {spec}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* 1 & 2. Device Conditioning (V2 native vs V1 heuristic calibration) */}
      {isV2DeviceModel ? (
        <div className="space-y-3 border-t border-hairline pt-4">
          <div>
            <label
              htmlFor="device-category-select"
              className="mb-1 block text-xs font-semibold text-ink-secondary"
            >
              1. IoT Device Category
            </label>
            <select
              id="device-category-select"
              value={v2DeviceCategory}
              disabled={busy}
              onChange={(e) => {
                onChangeV2DeviceCategory(e.target.value);
                onChangeV2DeviceId("ANY");
              }}
              className="studio-input text-xs font-medium"
            >
              <option value="ALL">All Hardware Categories (7 families)</option>
              {(v2Catalog?.device_categories || []).map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          {/* 2. Specific Device (Optional) */}
          <div>
            <label
              htmlFor="device-id-select"
              className="mb-1 block text-xs font-semibold text-ink-secondary"
            >
              2. Specific Device (Optional)
            </label>
            <select
              id="device-id-select"
              value={v2DeviceId}
              disabled={busy}
              onChange={(e) => onChangeV2DeviceId(e.target.value)}
              className="studio-input font-mono text-xs"
            >
              <option value="ANY">
                {v2DeviceCategory === "ALL"
                  ? `Any Device (${v2Catalog?.total_devices ?? 70} devices)`
                  : `Any ${v2DeviceCategory} Device (${filteredDevices.length} devices)`}
              </option>
              {filteredDevices.map((d) => (
                <option key={d.device_id} value={d.device_id}>
                  {d.device_id} · {d.device_name}
                </option>
              ))}
            </select>
          </div>

          {selectedDeviceMeta && (
            <p className="rounded-lg border border-[#C4DBFA] bg-[#EAF2FD]/70 px-3 py-2 text-[11px] leading-relaxed text-[#1E4F8A]">
              <strong>{selectedDeviceMeta.device_id}</strong> ({selectedDeviceMeta.device_category}):{" "}
              supports {selectedDeviceMeta.supported_label_categories.join(", ")}.
            </p>
          )}
        </div>
      ) : (
        <div className="space-y-2.5 border-t border-hairline pt-4">
          <div className="text-xs font-semibold text-ink-secondary">
            1. Baseline Flow Schema &amp; Calibration (V1)
          </div>
          <p className="rounded-lg border border-hairline bg-well/60 px-3 py-2 text-[11px] leading-relaxed text-ink-secondary">
            <strong>{modelId}</strong> generates 42-column anonymized CICIoT2023 flows without native MAC-attributed hardware IDs.
          </p>
          <label className="flex cursor-pointer items-start gap-2 rounded-lg border border-hairline bg-well/50 px-3 py-2 text-xs">
            <input
              type="checkbox"
              checked={v1CalibrateDevices}
              disabled={busy}
              onChange={(e) => onChangeV1CalibrateDevices(e.target.checked)}
              className="mt-0.5"
            />
            <span>
              <strong className="text-ink">Attach Heuristic IoT Device Profiles</strong>
              <span className="block text-[11px] text-ink-secondary">
                Adds simulated device_id/device_category and scales benign flow bounds.
              </span>
            </span>
          </label>
          {v1CalibrateDevices && (
            <select
              aria-label="Select V1 device profile"
              value={v1DeviceProfile}
              disabled={busy}
              onChange={(e) => onChangeV1DeviceProfile(e.target.value)}
              className="studio-input text-xs font-medium"
            >
              <option value="ALL">
                All Simulated IoT Profiles ({v1DeviceProfiles.length || 6} profiles)
              </option>
              {v1DeviceProfiles.map((p) => (
                <option key={p.profile_name} value={p.profile_name}>
                  {p.profile_name} ({p.device_category})
                </option>
              ))}
            </select>
          )}
        </div>
      )}

      {/* 3. Generation Strategy */}
      <div className="space-y-3 border-t border-hairline pt-4">
        <div className="text-xs font-semibold text-ink-secondary">
          3. Traffic Generation Strategy
        </div>

        <div className="grid grid-cols-2 gap-1.5 rounded-xl border border-hairline bg-well p-1 text-xs font-semibold">
          <button
            type="button"
            disabled={busy || isSingleDevice}
            title={
              isSingleDevice
                ? "Switch Specific Device to Any Device to balance all 8 traffic classes."
                : "Generate balanced traffic across all 8 categories."
            }
            onClick={() => onChangeStrategy("balanced")}
            className={`min-h-[36px] rounded-lg px-2 py-1.5 text-center transition disabled:cursor-not-allowed disabled:opacity-45 ${
              strategy === "balanced"
                ? "bg-surface text-brand shadow-sm ring-1 ring-hairline"
                : "text-ink-secondary hover:text-ink"
            }`}
          >
            Balanced Mix
          </button>

          <button
            type="button"
            disabled={busy || !supportsNormal}
            onClick={() => onChangeStrategy("normal")}
            className={`min-h-[36px] rounded-lg px-2 py-1.5 text-center transition disabled:cursor-not-allowed disabled:opacity-45 ${
              strategy === "normal"
                ? "bg-surface text-brand shadow-sm ring-1 ring-hairline"
                : "text-ink-secondary hover:text-ink"
            }`}
          >
            Normal Traffic
          </button>

          <button
            type="button"
            disabled={busy || supportedAttackCategories.length === 0}
            onClick={() => onChangeStrategy("attack")}
            className={`min-h-[36px] rounded-lg px-2 py-1.5 text-center transition disabled:cursor-not-allowed disabled:opacity-45 ${
              strategy === "attack"
                ? "bg-surface text-brand shadow-sm ring-1 ring-hairline"
                : "text-ink-secondary hover:text-ink"
            }`}
          >
            Attack Scenario
          </button>

          <button
            type="button"
            disabled={busy}
            onClick={() => onChangeStrategy("general")}
            className={`min-h-[36px] rounded-lg px-2 py-1.5 text-center transition disabled:cursor-not-allowed disabled:opacity-45 ${
              strategy === "general"
                ? "bg-surface text-brand shadow-sm ring-1 ring-hairline"
                : "text-ink-secondary hover:text-ink"
            }`}
          >
            Natural Prior
          </button>
        </div>

        {isSingleDevice && (
          <p className="text-[11px] text-ink-secondary">
            Multi-class balancing runs at category level; single-device selection supports Normal, Attack Scenario, or Natural Prior.
          </p>
        )}

        {/* Strategy Sub-options */}
        {strategy === "balanced" && (
          <div className="studio-well space-y-2.5 p-3">
            <label className="flex cursor-pointer items-start gap-2 text-xs">
              <input
                type="checkbox"
                checked={boostRareClasses}
                disabled={busy}
                onChange={(e) => onChangeBoostRareClasses(e.target.checked)}
                className="mt-0.5"
              />
              <span>
                <strong className="text-ink">Boost rare attack classes</strong>
                <span className="block text-[11px] text-ink-secondary">
                  Increases minority shares (Brute Force, Web-based, Spoofing) within your total record count.
                </span>
              </span>
            </label>

            {quotaPreview && (
              <div className="border-t border-hairline pt-2 text-[11px] text-ink-secondary tabular-nums">
                Target split:{" "}
                <span className="font-mono text-ink">
                  {Object.entries(quotaPreview)
                    .map(([k, v]) => `${k} ${v}`)
                    .join(" · ")}
                </span>
              </div>
            )}
          </div>
        )}

        {strategy === "attack" && (
          <div className="studio-well space-y-2.5 p-3">
            <div className="flex gap-4 text-xs font-semibold text-ink-secondary">
              <label className="flex cursor-pointer items-center gap-1.5">
                <input
                  type="radio"
                  name="attack-condition-type"
                  checked={attackConditionType === "category"}
                  disabled={busy}
                  onChange={() => onChangeAttackConditionType("category")}
                />
                Attack Category
              </label>
              <label className="flex cursor-pointer items-center gap-1.5">
                <input
                  type="radio"
                  name="attack-condition-type"
                  checked={attackConditionType === "raw"}
                  disabled={busy}
                  onChange={() => onChangeAttackConditionType("raw")}
                />
                Attack Signature
              </label>
            </div>

            {attackConditionType === "category" ? (
              <select
                aria-label="Select attack category"
                value={selectedAttackCategory}
                disabled={busy}
                onChange={(e) => onChangeSelectedAttackCategory(e.target.value)}
                className="studio-input text-xs"
              >
                {supportedAttackCategories.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            ) : (
              <select
                aria-label="Select attack signature"
                value={selectedRawAttack}
                disabled={busy}
                onChange={(e) => onChangeSelectedRawAttack(e.target.value)}
                className="studio-input font-mono text-xs"
              >
                {supportedAttackSignatures.map((atk) => (
                  <option key={atk.attack_id} value={atk.label_raw}>
                    {atk.label_raw} ({atk.label_category})
                  </option>
                ))}
              </select>
            )}
          </div>
        )}
      </div>

      {/* 4. Record Count & Domain Repair */}
      <div className="space-y-3 border-t border-hairline pt-4">
        <div>
          <div className="mb-1 flex items-center justify-between gap-2">
            <label
              htmlFor="num-records-input"
              className="text-xs font-semibold text-ink-secondary"
            >
              4. Number of Records (1–10,000)
            </label>
            <div className="flex gap-1">
              {RECORD_PRESETS.map((preset) => (
                <button
                  key={preset}
                  type="button"
                  disabled={busy}
                  onClick={() => onChangeNumRecordsInput(String(preset))}
                  className={`rounded border px-1.5 py-0.5 font-mono text-[10px] font-semibold transition ${
                    parsedCount === preset
                      ? "border-brand bg-brand-tint text-brand"
                      : "border-hairline bg-surface text-ink-secondary hover:border-brand/50"
                  }`}
                >
                  {preset.toLocaleString()}
                </button>
              ))}
            </div>
          </div>

          <input
            id="num-records-input"
            type="number"
            min={1}
            max={10000}
            step={1}
            disabled={busy}
            value={numRecordsInput}
            onChange={(e) => onChangeNumRecordsInput(e.target.value)}
            className="studio-input font-mono text-sm tabular-nums"
          />
          {!countValid && (
            <p role="alert" className="mt-1 text-xs font-semibold text-[#BF4840]">
              Enter a whole number between 1 and 10,000.
            </p>
          )}
        </div>

        <label className="flex cursor-pointer items-start gap-2 rounded-lg border border-hairline bg-well/50 px-3 py-2.5 text-xs">
          <input
            type="checkbox"
            checked={applyDomainCorrection}
            disabled={busy}
            onChange={(e) => onChangeApplyDomainCorrection(e.target.checked)}
            className="mt-0.5"
          />
          <span>
            <strong className="text-ink">Enforce Domain Consistency</strong>
            <span className="block text-[11px] text-ink-secondary">
              Repairs label hierarchy, IANA protocol names, and Std dispersion invariants.
            </span>
          </span>
        </label>
      </div>

      {/* Primary Action */}
      <PrimaryButton
        type="button"
        loading={busy}
        disabled={!countValid || !modelAvailable}
        onClick={onGenerate}
        className="w-full"
      >
        <Sparkles className="h-4 w-4" aria-hidden="true" />
        {busy ? "Generating Synthetic Data..." : "Generate Synthetic Data"}
      </PrimaryButton>
    </aside>
  );
}
