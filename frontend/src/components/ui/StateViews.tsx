"use client";

import React from "react";
import { AlertCircle, Inbox, RefreshCw } from "lucide-react";
import { SecondaryButton } from "./Button";

export function LoadingSkeleton({
  rows = 3,
  className = "",
}: {
  rows?: number;
  className?: string;
}) {
  return (
    <div className={`studio-panel space-y-3 p-5 ${className}`} aria-busy="true" aria-label="Loading content">
      <div className="h-4 w-44 animate-pulse rounded bg-well" />
      <div className="space-y-2.5">
        {Array.from({ length: rows }).map((_, idx) => (
          <div
            key={idx}
            className="h-8 w-full animate-pulse rounded-lg bg-well/80"
            style={{ width: idx === rows - 1 ? "72%" : "100%" }}
          />
        ))}
      </div>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-[#CFD8D3] bg-surface/60 px-6 py-10 text-center">
      <div className="flex h-11 w-11 items-center justify-center rounded-full bg-well text-ink-secondary">
        <Inbox className="h-5 w-5" aria-hidden="true" />
      </div>
      <h3 className="mt-3 text-sm font-semibold text-ink">{title}</h3>
      <p className="mt-1 max-w-md text-xs leading-relaxed text-ink-secondary">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({
  title = "Backend request failed",
  message,
  onRetry,
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-[#F2C3BF] bg-[#FDECEC] px-4 py-3.5 text-[#9A332D]"
    >
      <div className="flex items-start gap-3">
        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
        <div>
          <div className="text-sm font-bold">{title}</div>
          <p className="mt-0.5 text-xs leading-relaxed">{message}</p>
        </div>
      </div>
      {onRetry && (
        <SecondaryButton size="sm" onClick={onRetry}>
          <RefreshCw className="h-3.5 w-3.5" /> Retry
        </SecondaryButton>
      )}
    </div>
  );
}
