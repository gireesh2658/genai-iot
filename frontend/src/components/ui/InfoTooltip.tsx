"use client";

import React, { useState } from "react";
import { HelpCircle } from "lucide-react";
import { TECHNICAL_GLOSSARY } from "@/lib/glossary";

export function InfoTooltip({
  term,
  customTitle,
  customText,
}: {
  term: string;
  customTitle?: string;
  customText?: string;
}) {
  const [open, setOpen] = useState(false);
  const entry = TECHNICAL_GLOSSARY[term];
  const title = customTitle || entry?.title || term;
  const text = customText || entry?.summary;

  if (!text) return null;

  return (
    <span className="relative inline-flex items-center align-middle">
      <button
        type="button"
        aria-label={`Explain ${title}`}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onBlur={() => setOpen(false)}
        className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded-full text-ink-secondary transition hover:bg-brand-tint hover:text-brand"
      >
        <HelpCircle className="h-3.5 w-3.5" />
      </button>
      {open && (
        <span
          role="tooltip"
          className="absolute bottom-full left-1/2 z-40 mb-2 w-64 -translate-x-1/2 rounded-xl border border-hairline bg-surface p-3 text-left shadow-lg"
        >
          <span className="block text-xs font-bold text-ink">{title}</span>
          <span className="mt-1 block text-[11px] font-normal leading-relaxed text-ink-secondary">
            {text}
          </span>
        </span>
      )}
    </span>
  );
}
