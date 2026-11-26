"use client";

import React from "react";
import Link from "next/link";

function BrandMark() {
  return (
    <svg
      viewBox="0 0 36 36"
      className="h-8 w-8 shrink-0"
      aria-hidden="true"
      fill="none"
    >
      <rect
        x="1"
        y="1"
        width="34"
        height="34"
        rx="9"
        fill="#EAF2FD"
        stroke="#C4DBFA"
        strokeWidth="1.5"
      />
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

export function AppHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-hairline bg-surface/95 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-[1360px] items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <Link href="/studio" className="flex items-center gap-2.5">
          <BrandMark />
          <div className="leading-tight">
            <span className="block text-sm font-bold tracking-tight text-ink">
              IoTSynth <span className="text-brand">AI</span>
            </span>
            <span className="block text-[11px] font-medium text-ink-secondary">
              Synthetic IoT Traffic Generator
            </span>
          </div>
        </Link>
      </div>
    </header>
  );
}
