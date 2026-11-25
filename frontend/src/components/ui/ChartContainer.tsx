"use client";

import React from "react";
import { EmptyState } from "./StateViews";

export function ChartContainer({
  title,
  subtitle,
  unit,
  headerAction,
  isEmpty = false,
  emptyMessage = "No telemetry records match the active scope.",
  children,
  className = "",
}: {
  title: React.ReactNode;
  subtitle?: string;
  unit?: string;
  headerAction?: React.ReactNode;
  isEmpty?: boolean;
  emptyMessage?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`studio-panel min-w-0 p-5 ${className}`}>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="flex items-center gap-1.5 text-sm font-bold text-ink">{title}</h3>
          {subtitle && <p className="mt-0.5 text-xs text-ink-secondary">{subtitle}</p>}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {unit && (
            <span className="shrink-0 whitespace-nowrap rounded-md border border-hairline bg-well px-2 py-0.5 font-mono text-[10px] font-semibold text-ink-secondary">
              {unit}
            </span>
          )}
          {headerAction}
        </div>
      </div>

      {isEmpty ? (
        <EmptyState title="No Data Plotted" description={emptyMessage} />
      ) : (
        <div className="w-full">{children}</div>
      )}
    </section>
  );
}
