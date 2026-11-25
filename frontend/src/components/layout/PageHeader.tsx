"use client";

import React from "react";

export function PageHeader({
  eyebrow,
  title,
  description,
  statusSlot,
  actionSlot,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  statusSlot?: React.ReactNode;
  actionSlot?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4 border-b border-hairline pb-5">
      <div className="min-w-0 max-w-3xl space-y-1.5">
        {(eyebrow || statusSlot) && (
          <div className="flex flex-wrap items-center gap-2">
            {eyebrow && (
              <span className="font-mono text-[11px] font-bold uppercase tracking-wider text-brand">
                {eyebrow}
              </span>
            )}
            {statusSlot}
          </div>
        )}
        <h1 className="text-2xl font-bold tracking-[-0.02em] text-ink sm:text-[26px]">{title}</h1>
        <p className="text-sm leading-relaxed text-ink-secondary">{description}</p>
      </div>
      {actionSlot && (
        <div className="flex min-w-0 max-w-full flex-wrap items-center gap-2.5 lg:shrink-0">
          {actionSlot}
        </div>
      )}
    </div>
  );
}
