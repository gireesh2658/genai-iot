"use client";

import React from "react";

export interface TabOption<T extends string> {
  id: T;
  label: string;
  badge?: string | number;
  icon?: React.ElementType;
}

export function Tabs<T extends string>({
  items,
  activeId,
  onChange,
  className = "",
}: {
  items: TabOption<T>[];
  activeId: T;
  onChange: (id: T) => void;
  className?: string;
}) {
  return (
    <div
      role="tablist"
      className={`inline-flex max-w-full flex-wrap items-center gap-1 rounded-xl border border-hairline bg-well p-1 ${className}`}
    >
      {items.map((item) => {
        const active = item.id === activeId;
        const Icon = item.icon;
        return (
          <button
            key={item.id}
            role="tab"
            type="button"
            aria-selected={active}
            onClick={() => onChange(item.id)}
            className={`inline-flex min-h-[36px] items-center gap-1.5 rounded-[9px] px-3.5 py-1.5 text-xs font-semibold transition ${
              active
                ? "bg-surface text-brand shadow-sm ring-1 ring-hairline"
                : "text-ink-secondary hover:text-ink"
            }`}
          >
            {Icon && <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />}
            <span>{item.label}</span>
            {item.badge !== undefined && (
              <span
                className={`rounded-full px-1.5 py-0.5 font-mono text-[10px] font-bold tabular-nums ${
                  active ? "bg-brand-tint text-brand" : "bg-surface text-ink-secondary"
                }`}
              >
                {item.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
