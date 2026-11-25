"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  ExternalLink,
  Layers,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { IconButton } from "@/components/ui/Button";
import { StatusIndicator } from "@/components/ui/StatusIndicator";
import { BACKEND_DOCS_URL } from "@/lib/api";

export const NAV_ROUTES = [
  {
    href: "/",
    label: "Executive Workbench",
    caption: "Architecture & telemetry status",
    icon: Layers,
  },
  {
    href: "/studio",
    label: "Synthetic Data Studio",
    caption: "CTGAN sampling, repair & vault",
    icon: Sparkles,
  },
  {
    href: "/quality",
    label: "Quality Audit",
    caption: "KS, MACE & domain validity",
    icon: BarChart3,
  },
  {
    href: "/anomaly",
    label: "Anomaly Detection Lab",
    caption: "TSTR+R benchmarks & scorer",
    icon: ShieldCheck,
  },
] as const;

export function BrandMark() {
  return (
    <svg
      viewBox="0 0 36 36"
      className="h-9 w-9 shrink-0"
      aria-hidden="true"
      fill="none"
    >
      <rect x="1" y="1" width="34" height="34" rx="9" fill="#EAF2FD" stroke="#C4DBFA" strokeWidth="1.5" />
      <path
        d="M6 19.5H10.5L13.5 11.5L17.5 24.5L21.5 14L24.5 19.5H30"
        stroke="#2A67B1"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="21.5" cy="14" r="2.2" fill="#17857B" />
    </svg>
  );
}

export function AppSidebar({
  online,
  ctganCount,
  anomalyCount,
  mobileOpen,
  onCloseMobile,
}: {
  online: boolean | null;
  ctganCount: number | null;
  anomalyCount: number | null;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}) {
  const pathname = usePathname();

  const navBody = (
    <div className="flex h-full flex-col bg-surface">
      {/* Studio Brand Header */}
      <div className="flex items-center justify-between border-b border-hairline px-5 py-4">
        <Link href="/" onClick={onCloseMobile} className="flex items-center gap-3">
          <BrandMark />
          <div>
            <div className="text-sm font-bold tracking-tight text-ink">
              IoTSynth <span className="text-brand">AI</span>
            </div>
            <div className="text-[11px] font-medium text-ink-secondary">
              Signal Intelligence Studio
            </div>
          </div>
        </Link>
        {mobileOpen && (
          <IconButton label="Close navigation menu" onClick={onCloseMobile} className="lg:hidden">
            <X className="h-5 w-5" />
          </IconButton>
        )}
      </div>

      {/* Navigation Links */}
      <nav aria-label="Primary studio modules" className="flex-1 space-y-1 px-3 py-5">
        <div className="px-2.5 pb-2 text-[10px] font-bold uppercase tracking-widest text-ink-muted">
          Studio Workspace
        </div>
        {NAV_ROUTES.map((item) => {
          const Icon = item.icon;
          const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onCloseMobile}
              aria-current={active ? "page" : undefined}
              className={`group flex min-h-[44px] items-center gap-3 rounded-xl border px-3 py-2.5 transition ${
                active
                  ? "border-[#C4DBFA] bg-brand-tint text-brand"
                  : "border-transparent text-ink-secondary hover:bg-well/70 hover:text-ink"
              }`}
            >
              <div
                className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border transition ${
                  active
                    ? "border-[#B3D1F7] bg-surface text-brand"
                    : "border-hairline bg-canvas text-ink-secondary group-hover:bg-surface group-hover:text-brand"
                }`}
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
              </div>
              <div className="min-w-0">
                <div className={`text-xs font-bold ${active ? "text-[#1E4F8A]" : "text-ink"}`}>
                  {item.label}
                </div>
                <div className="truncate text-[11px] text-ink-secondary">{item.caption}</div>
              </div>
            </Link>
          );
        })}
      </nav>

      {/* Honest Runtime Telemetry Box */}
      <div className="m-3 space-y-3 rounded-xl border border-hairline bg-well/65 p-3.5">
        <div className="flex items-center justify-between gap-2">
          <span className="flex items-center gap-1.5 text-xs font-bold text-ink">
            <Activity className="h-3.5 w-3.5 text-signal" aria-hidden="true" />
            FastAPI Engine
          </span>
          {online === null ? (
            <StatusIndicator tone="neutral" label="Checking" />
          ) : online ? (
            <StatusIndicator tone="success" label="Connected" />
          ) : (
            <StatusIndicator tone="danger" label="Offline" />
          )}
        </div>

        <div className="grid grid-cols-2 gap-2 text-center">
          <div className="rounded-lg border border-hairline bg-surface px-2 py-2">
            <div className="font-mono text-sm font-bold text-brand tabular-nums">
              {ctganCount ?? "--"}
            </div>
            <div className="text-[10px] font-medium text-ink-secondary">CTGAN Models</div>
          </div>
          <div className="rounded-lg border border-hairline bg-surface px-2 py-2">
            <div className="font-mono text-sm font-bold text-signal tabular-nums">
              {anomalyCount ?? "--"}
            </div>
            <div className="text-[10px] font-medium text-ink-secondary">ML Detectors</div>
          </div>
        </div>

        <a
          href={BACKEND_DOCS_URL}
          target="_blank"
          rel="noreferrer"
          className="flex min-h-[36px] items-center justify-between rounded-lg border border-hairline bg-surface px-3 py-1.5 text-xs font-semibold text-ink-secondary transition hover:border-brand/40 hover:text-brand"
        >
          <span>REST API Docs</span>
          <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
        </a>
      </div>
    </div>
  );

  return (
    <>
      <aside className="hidden w-[264px] shrink-0 border-r border-hairline bg-surface lg:block">
        <div className="sticky top-0 h-screen">{navBody}</div>
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden" role="dialog" aria-modal="true" aria-label="Mobile Navigation">
          <div
            className="fixed inset-0 bg-[#2B3748]/25"
            onClick={onCloseMobile}
            aria-hidden="true"
          />
          <div className="relative z-10 h-full w-72 border-r border-hairline bg-surface shadow-xl">
            {navBody}
          </div>
        </div>
      )}
    </>
  );
}
