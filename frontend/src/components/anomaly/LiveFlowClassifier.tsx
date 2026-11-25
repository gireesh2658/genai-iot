"use client";

import React, { useState } from "react";
import { Play, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import {
  AnomalyModelSummary,
  PredictBatchResponse,
  PredictSingleResponse,
} from "@/lib/types";
import { PrimaryButton, SecondaryButton } from "@/components/ui/Button";
import { StatusIndicator } from "@/components/ui/StatusIndicator";
import { useToast } from "@/components/ui/ToastProvider";

const FEATURE_GROUPS: Array<{ title: string; keys: string[] }> = [
  {
    title: "Flow Rate & Timing (6 Features)",
    keys: ["Protocol Type", "Header_Length", "Time_To_Live", "Rate", "IAT", "Number"],
  },
  {
    title: "Packet Size & Dispersion (6 Features)",
    keys: ["Min", "Max", "AVG", "Std", "Variance", "Tot sum"],
  },
  {
    title: "TCP Flags & Counts (11 Features)",
    keys: [
      "syn_count",
      "ack_count",
      "fin_count",
      "rst_count",
      "syn_flag_number",
      "ack_flag_number",
      "fin_flag_number",
      "rst_flag_number",
      "psh_flag_number",
      "ece_flag_number",
      "cwr_flag_number",
    ],
  },
  {
    title: "Protocol / Application Ratios [0–1] (15 Features)",
    keys: [
      "TCP",
      "UDP",
      "ICMP",
      "HTTP",
      "HTTPS",
      "DNS",
      "SSH",
      "Telnet",
      "SMTP",
      "IRC",
      "DHCP",
      "ARP",
      "IGMP",
      "IPv",
      "LLC",
    ],
  },
];

const ZERO_FEATURES: Record<string, number> = {
  "Protocol Type": 6,
  Header_Length: 20,
  Time_To_Live: 64,
  Rate: 100,
  IAT: 0.01,
  Number: 10,
  Min: 60,
  Max: 60,
  AVG: 60,
  Std: 0,
  Variance: 0,
  "Tot sum": 600,
  fin_flag_number: 0,
  syn_flag_number: 0,
  rst_flag_number: 0,
  psh_flag_number: 0,
  ack_flag_number: 0,
  ece_flag_number: 0,
  cwr_flag_number: 0,
  syn_count: 0,
  ack_count: 0,
  fin_count: 0,
  rst_count: 0,
  HTTP: 0,
  HTTPS: 0,
  DNS: 0,
  Telnet: 0,
  SMTP: 0,
  SSH: 0,
  IRC: 0,
  TCP: 0,
  UDP: 0,
  DHCP: 0,
  ARP: 0,
  ICMP: 0,
  IGMP: 0,
  IPv: 1,
  LLC: 1,
};

const PRESETS: Record<string, Record<string, number>> = {
  Benign: {
    ...ZERO_FEATURES,
    Time_To_Live: 62,
    Rate: 102.56,
    IAT: 0.009938,
    Min: 60,
    Max: 1514,
    AVG: 442.5,
    Std: 617.83,
    Variance: 381710.5,
    "Tot sum": 4425,
    psh_flag_number: 0.2,
    ack_flag_number: 0.5,
    ack_count: 5,
    HTTPS: 0.5,
    TCP: 0.5,
    UDP: 0.5,
  },
  DDoS: {
    ...ZERO_FEATURES,
    Header_Length: 19.92,
    Time_To_Live: 63.36,
    Rate: 25893.96,
    IAT: 0.000039,
    Number: 100,
    "Tot sum": 6000,
    syn_flag_number: 1,
    syn_count: 100,
    TCP: 1,
  },
  Mirai: {
    ...ZERO_FEATURES,
    "Protocol Type": 17,
    Header_Length: 8,
    Rate: 18500,
    IAT: 0.000054,
    Number: 100,
    Min: 554,
    Max: 554,
    AVG: 554,
    "Tot sum": 55400,
    UDP: 1,
  },
  Spoofing: {
    ...ZERO_FEATURES,
    "Protocol Type": 0,
    Header_Length: 0,
    Rate: 24.5,
    IAT: 0.0408,
    Number: 12,
    Min: 42,
    Max: 60,
    AVG: 48,
    Std: 8.5,
    Variance: 72.25,
    "Tot sum": 576,
    ARP: 1,
  },
  "Brute Force": {
    ...ZERO_FEATURES,
    Rate: 640,
    IAT: 0.00156,
    Number: 18,
    Min: 66,
    Max: 142,
    AVG: 92,
    Std: 28,
    Variance: 784,
    "Tot sum": 1656,
    syn_flag_number: 0.3,
    psh_flag_number: 0.4,
    ack_flag_number: 0.8,
    syn_count: 4,
    ack_count: 14,
    SSH: 1,
    TCP: 1,
  },
};

export function LiveFlowClassifier({
  models,
  selectedModelId,
  onChangeModelId,
}: {
  models: AnomalyModelSummary[];
  selectedModelId: string;
  onChangeModelId: (id: string) => void;
}) {
  const { pushToast } = useToast();

  const [features, setFeatures] = useState<Record<string, number>>(PRESETS.Benign);
  const [singleRes, setSingleRes] = useState<PredictSingleResponse | null>(null);
  const [batchJson, setBatchJson] = useState(
    JSON.stringify([PRESETS.Benign, PRESETS.DDoS], null, 2)
  );
  const [batchRes, setBatchRes] = useState<PredictBatchResponse | null>(null);
  const [singleBusy, setSingleBusy] = useState(false);
  const [batchBusy, setBatchBusy] = useState(false);

  const handlePredictSingle = async () => {
    setSingleBusy(true);
    try {
      const payloadFeatures: Record<string, number> = {};
      for (const grp of FEATURE_GROUPS) {
        for (const k of grp.keys) {
          const val = Number(features[k]);
          if (!Number.isFinite(val)) {
            throw new Error(`Feature '${k}' must be a valid finite number.`);
          }
          payloadFeatures[k] = val;
        }
      }
      const res = await api.predictSingle({ model_id: selectedModelId, features: payloadFeatures });
      setSingleRes(res);
    } catch (e: any) {
      pushToast("error", "Flow classification failed", e.message);
    } finally {
      setSingleBusy(false);
    }
  };

  const handlePredictBatch = async () => {
    setBatchBusy(true);
    try {
      const parsed = JSON.parse(batchJson);
      if (!Array.isArray(parsed)) {
        throw new Error("Batch JSON must be an array of flow feature objects.");
      }
      const res = await api.predictBatch({ model_id: selectedModelId, records: parsed });
      setBatchRes(res);
      pushToast("success", "Batch inference finished", `Scored ${res.total_records} records in ${res.latency_ms} ms`);
    } catch (e: any) {
      pushToast("error", "Batch classification failed", e.message);
    } finally {
      setBatchBusy(false);
    }
  };

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
      {/* Left 38-feature Editor */}
      <section className="studio-panel space-y-4 p-5 lg:col-span-8">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-bold text-ink">
              Single Flow Feature Vector (38 Model Inputs)
            </h2>
            <p className="text-xs text-ink-secondary">
              Preset example vectors or adjust numeric attributes to query <code className="font-mono">{selectedModelId}</code>.
            </p>
          </div>
          <select
            aria-label="Detector model for inference"
            value={selectedModelId}
            onChange={(e) => onChangeModelId(e.target.value)}
            className="studio-input w-56 py-1.5 font-mono text-xs"
          >
            {models.map((m) => (
              <option key={m.model_id} value={m.model_id}>
                {m.model_id}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs font-semibold text-ink-secondary">Sample Presets:</span>
          {Object.keys(PRESETS).map((key) => (
            <SecondaryButton
              key={key}
              type="button"
              size="sm"
              onClick={() => setFeatures(PRESETS[key])}
            >
              {key}
            </SecondaryButton>
          ))}
        </div>

        <div className="space-y-4">
          {FEATURE_GROUPS.map((grp) => (
            <div key={grp.title} className="studio-well p-3.5">
              <h3 className="mb-2 text-xs font-bold text-ink">{grp.title}</h3>
              <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
                {grp.keys.map((k) => (
                  <label key={k} className="block">
                    <span className="mb-0.5 block truncate font-mono text-[10px] font-semibold text-ink-secondary">
                      {k}
                    </span>
                    <input
                      type="number"
                      step="any"
                      value={features[k] ?? 0}
                      onChange={(e) =>
                        setFeatures({ ...features, [k]: Number(e.target.value) })
                      }
                      className="studio-input py-1 font-mono text-xs tabular-nums"
                    />
                  </label>
                ))}
              </div>
            </div>
          ))}
        </div>

        <PrimaryButton type="button" loading={singleBusy} onClick={handlePredictSingle}>
          <Play className="h-4 w-4" />
          Classify Single Flow
        </PrimaryButton>
      </section>

      {/* Right API Verdict & Batch */}
      <div className="space-y-5 lg:col-span-4">
        <section className="studio-panel space-y-4 p-5">
          <div className="flex items-center justify-between">
            <h3 className="flex items-center gap-1.5 text-sm font-bold text-ink">
              <ShieldAlert className="h-4 w-4 text-brand" aria-hidden="true" />
              API Prediction Output
            </h3>
            {singleRes && (
              <span className="font-mono text-[11px] font-semibold text-ink-secondary">
                {singleRes.latency_ms} ms
              </span>
            )}
          </div>

          {singleRes ? (
            <div className="space-y-4">
              <div
                className={`rounded-xl border p-4 ${
                  singleRes.is_attack === 0
                    ? "border-[#B9E4D4] bg-[#DDF3EA] text-[#145C46]"
                    : "border-[#F2C3BF] bg-[#FDECEC] text-[#9A332D]"
                }`}
              >
                <div className="text-[11px] font-bold uppercase tracking-wider">
                  Predicted Traffic Class
                </div>
                <div className="mt-1 text-2xl font-bold">{singleRes.predicted_category}</div>
                <div className="mt-1 font-mono text-xs tabular-nums">
                  Top Score: <strong>{(singleRes.confidence * 100).toFixed(2)}%</strong> ·{" "}
                  is_attack={singleRes.is_attack}
                </div>
              </div>

              {singleRes.probabilities && (
                <div className="space-y-2">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-ink-secondary">
                    Returned Class Probabilities
                  </div>
                  {Object.entries(singleRes.probabilities)
                    .sort((a, b) => b[1] - a[1])
                    .map(([cls, p]) => (
                      <div key={cls} className="text-xs">
                        <div className="mb-1 flex justify-between font-medium text-ink">
                          <span>{cls}</span>
                          <span className="font-mono tabular-nums">{(p * 100).toFixed(2)}%</span>
                        </div>
                        <div className="h-1.5 w-full overflow-hidden rounded-full bg-well">
                          <div
                            className="h-full rounded-full bg-brand"
                            style={{ width: `${Math.max(1, p * 100)}%` }}
                          />
                        </div>
                      </div>
                    ))}
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-[#CFD8D3] px-4 py-8 text-center text-xs text-ink-secondary">
              Submit the 38-feature vector to inspect the model&apos;s predicted category and returned probabilities.
            </div>
          )}
        </section>

        <section className="studio-panel space-y-3 p-5">
          <h3 className="text-sm font-bold text-ink">Batch JSON Scorer</h3>
          <textarea
            aria-label="Batch JSON feature records"
            rows={5}
            value={batchJson}
            onChange={(e) => setBatchJson(e.target.value)}
            className="studio-input font-mono text-[11px]"
          />
          <SecondaryButton
            type="button"
            size="sm"
            loading={batchBusy}
            onClick={handlePredictBatch}
            className="w-full"
          >
            Score Batch Payload
          </SecondaryButton>

          {batchRes && (
            <div className="space-y-2 pt-1 text-xs">
              <div className="flex items-center justify-between text-[11px] text-ink-secondary tabular-nums">
                <span>
                  {batchRes.attack_count} attack · {batchRes.benign_count} benign
                </span>
                <span className="font-mono">{batchRes.latency_ms} ms</span>
              </div>
              {batchRes.predictions.map((p) => (
                <div
                  key={p.index}
                  className="flex items-center justify-between rounded-lg border border-hairline bg-canvas px-3 py-1.5"
                >
                  <span className="font-mono text-ink-secondary">#{p.index}</span>
                  <StatusIndicator
                    tone={p.is_attack === 0 ? "success" : "danger"}
                    label={p.predicted_category}
                  />
                  <span className="font-mono font-bold text-ink tabular-nums">
                    {(p.confidence * 100).toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
