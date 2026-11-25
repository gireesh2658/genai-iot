"use client";

import React from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import {
  AnomalyModelSummary,
  DatasetItem,
  EvaluationSummaryItem,
  IoTDeviceProfile,
} from "@/lib/types";
import { fmtBytes, fmtDeviceName, fmtTimestamp } from "@/lib/formatters";
import { StatusIndicator } from "@/components/ui/StatusIndicator";

function DeviceVectorIcon({ profile }: { profile: string }) {
  const stroke = "#2A67B1";
  const accent = "#17857B";
  switch (profile) {
    case "smart_camera":
      return (
        <svg viewBox="0 0 36 36" className="h-8 w-8" fill="none" aria-hidden="true">
          <rect x="4" y="9" width="20" height="14" rx="3" stroke={stroke} strokeWidth="1.8" />
          <circle cx="14" cy="16" r="4" stroke={accent} strokeWidth="1.8" />
          <path d="M24 13L31 10V22L24 19" stroke={stroke} strokeWidth="1.8" strokeLinejoin="round" />
        </svg>
      );
    case "smart_thermostat":
      return (
        <svg viewBox="0 0 36 36" className="h-8 w-8" fill="none" aria-hidden="true">
          <circle cx="18" cy="18" r="12" stroke={stroke} strokeWidth="1.8" />
          <circle cx="18" cy="18" r="7" stroke={accent} strokeWidth="1.6" strokeDasharray="3 2" />
          <path d="M18 18L22 14" stroke={stroke} strokeWidth="2" strokeLinecap="round" />
        </svg>
      );
    case "smart_bulb":
      return (
        <svg viewBox="0 0 36 36" className="h-8 w-8" fill="none" aria-hidden="true">
          <path
            d="M12 22C10.2 20.1 9 17.6 9 15C9 10.0 13.0 6 18 6C23.0 6 27 10.0 27 15C27 17.6 25.8 20.1 24 22L23 25H13L12 22Z"
            stroke={stroke}
            strokeWidth="1.8"
          />
          <path d="M14 29H22" stroke={accent} strokeWidth="2" strokeLinecap="round" />
        </svg>
      );
    case "smart_speaker":
      return (
        <svg viewBox="0 0 36 36" className="h-8 w-8" fill="none" aria-hidden="true">
          <rect x="10" y="5" width="16" height="26" rx="6" stroke={stroke} strokeWidth="1.8" />
          <circle cx="18" cy="21" r="4" stroke={accent} strokeWidth="1.8" />
          <circle cx="18" cy="11" r="1.5" fill={accent} />
        </svg>
      );
    case "smart_plug":
      return (
        <svg viewBox="0 0 36 36" className="h-8 w-8" fill="none" aria-hidden="true">
          <rect x="7" y="7" width="22" height="22" rx="5" stroke={stroke} strokeWidth="1.8" />
          <circle cx="14" cy="16" r="1.8" fill={stroke} />
          <circle cx="22" cy="16" r="1.8" fill={stroke} />
          <path d="M18 22V25" stroke={accent} strokeWidth="2" strokeLinecap="round" />
        </svg>
      );
    default:
      return (
        <svg viewBox="0 0 36 36" className="h-8 w-8" fill="none" aria-hidden="true">
          <circle cx="18" cy="18" r="3" fill={accent} />
          <path d="M12 12C8.8 15.2 8.8 20.8 12 24" stroke={stroke} strokeWidth="1.8" strokeLinecap="round" />
          <path d="M24 12C27.2 15.2 27.2 20.8 24 24" stroke={stroke} strokeWidth="1.8" strokeLinecap="round" />
          <path d="M8 8C3.2 13.5 3.2 22.5 8 28" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" />
          <path d="M28 8C32.8 13.5 32.8 22.5 28 28" stroke={stroke} strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      );
  }
}

export function DeviceFleetGrid({
  devices,
  datasets,
  evaluations,
  customModels,
}: {
  devices: IoTDeviceProfile[];
  datasets: DatasetItem[];
  evaluations: EvaluationSummaryItem[];
  customModels: AnomalyModelSummary[];
}) {
  return (
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
      {/* Device Profiles Ecosystem */}
      <section className="studio-panel p-5 sm:p-6 xl:col-span-8">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-bold text-ink">
              IoT Hardware Profiles ({devices.length})
            </h2>
            <p className="mt-0.5 text-xs text-ink-secondary">
              Post-hoc calibration constrains benign sensor packet bounds &amp; Popoviciu variance per hardware profile. Select any device to pre-configure the generator.
            </p>
          </div>
          <Link
            href="/studio"
            className="text-xs font-bold text-brand hover:underline"
          >
            All Profiles in Studio →
          </Link>
        </div>

        <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
          {devices.map((dev) => (
            <div
              key={dev.profile_name}
              className="flex flex-col justify-between rounded-xl border border-hairline bg-surface p-4 transition hover:border-[#B3D1F7] hover:bg-[#FAFBF9]"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <DeviceVectorIcon profile={dev.profile_name} />
                  <span className="rounded-md border border-hairline bg-well px-2 py-0.5 font-mono text-[10px] font-semibold text-ink-secondary">
                    {dev.behavior_type}
                  </span>
                </div>

                <h3 className="mt-3 text-sm font-bold text-ink">
                  {fmtDeviceName(dev.profile_name)}
                </h3>
                <div className="font-mono text-[11px] text-ink-muted">
                  {dev.device_category} · {dev.profile_name}
                </div>
                <p className="mt-1.5 line-clamp-2 text-xs leading-relaxed text-ink-secondary">
                  {dev.description}
                </p>
              </div>

              <div className="mt-3 space-y-2.5 border-t border-hairline pt-2.5">
                <div className="flex items-center justify-between text-[11px] tabular-nums">
                  <span className="text-ink-secondary">MTU Envelope</span>
                  <span className="font-mono font-semibold text-ink">
                    {dev.packet_size_min}–{dev.packet_size_max} B
                  </span>
                </div>
                <div className="flex items-center justify-between text-[11px] tabular-nums">
                  <span className="text-ink-secondary">Benign Rate</span>
                  <span className="font-mono font-semibold text-ink">
                    {dev.traffic_rate_min}–{dev.traffic_rate_max} /s
                  </span>
                </div>
                <Link
                  href={`/studio?device=${encodeURIComponent(dev.profile_name)}`}
                  className="inline-flex min-h-[36px] w-full items-center justify-between rounded-lg border border-hairline bg-well/60 px-3 py-1.5 text-xs font-semibold text-brand transition hover:border-[#C4DBFA] hover:bg-brand-tint"
                >
                  <span>Pre-select in Studio</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Authentic Activity Ledger (Zero Fabricated Entries) */}
      <section className="studio-panel flex flex-col justify-between p-5 sm:p-6 xl:col-span-4">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-ink">Persisted Repository Activity</h2>
            <StatusIndicator tone="neutral" label="Verified Disk State" />
          </div>

          <div className="space-y-2">
            <div className="text-[11px] font-bold uppercase tracking-wider text-ink-muted">
              Generated Datasets ({datasets.length})
            </div>
            {datasets.slice(0, 4).map((d) => (
              <Link
                key={d.dataset_id}
                href={`/quality?dataset=${encodeURIComponent(d.dataset_id)}`}
                className="flex items-center justify-between gap-2 rounded-xl border border-hairline bg-canvas px-3 py-2.5 text-xs transition hover:border-[#C4DBFA] hover:bg-surface"
              >
                <div className="min-w-0">
                  <div className="truncate font-mono font-bold text-ink">{d.dataset_id}</div>
                  <div className="mt-0.5 text-[11px] text-ink-secondary tabular-nums">
                    {d.num_records?.toLocaleString() ?? "--"} × {d.num_columns ?? "--"} ·{" "}
                    {fmtBytes(d.size_bytes)}
                  </div>
                </div>
                <span className="shrink-0 font-mono text-[10px] text-ink-muted">
                  {fmtTimestamp(d.created_at)}
                </span>
              </Link>
            ))}
          </div>

          <div className="space-y-2 pt-2">
            <div className="text-[11px] font-bold uppercase tracking-wider text-ink-muted">
              Evaluation Audits ({evaluations.length})
            </div>
            {evaluations.slice(0, 3).map((ev) => (
              <Link
                key={ev.evaluation_id}
                href="/quality"
                className="flex items-center justify-between gap-2 rounded-xl border border-hairline bg-canvas px-3 py-2 text-xs transition hover:border-[#C4DBFA] hover:bg-surface"
              >
                <div className="min-w-0">
                  <div className="truncate font-semibold text-ink">{ev.title}</div>
                  <div className="truncate font-mono text-[10px] text-ink-secondary">
                    {ev.evaluation_id}
                  </div>
                </div>
                <span className="shrink-0 font-mono text-[10px] text-ink-muted">
                  {fmtTimestamp(ev.created_at)}
                </span>
              </Link>
            ))}
          </div>

          {customModels.length > 0 && (
            <div className="space-y-2 pt-2">
              <div className="text-[11px] font-bold uppercase tracking-wider text-ink-muted">
                Custom Trained Detectors ({customModels.length})
              </div>
              {customModels.slice(0, 3).map((cm) => (
                <Link
                  key={cm.model_id}
                  href="/anomaly"
                  className="flex items-center justify-between gap-2 rounded-xl border border-hairline bg-canvas px-3 py-2 text-xs transition hover:border-[#C4DBFA] hover:bg-surface"
                >
                  <span className="truncate font-mono font-semibold text-ink">{cm.model_id}</span>
                  <span className="font-mono font-bold text-brand tabular-nums">
                    F1 {cm.macro_f1?.toFixed(4) ?? "--"}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
