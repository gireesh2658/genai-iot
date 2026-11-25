"use client";

import React from "react";
import { AlertTriangle, CheckCircle2, Info, Sparkles, XCircle } from "lucide-react";

type Tone = "success" | "warning" | "danger" | "info" | "synthetic" | "neutral";

const TONE_MAP: Record<Tone, { classes: string; Icon: React.ElementType }> = {
  success: {
    classes: "border-[#B9E4D4] bg-[#DDF3EA] text-[#145C46]",
    Icon: CheckCircle2,
  },
  warning: {
    classes: "border-[#F1D5A6] bg-[#FEF5E7] text-[#844F0C]",
    Icon: AlertTriangle,
  },
  danger: {
    classes: "border-[#F2C3BF] bg-[#FDECEC] text-[#9A332D]",
    Icon: XCircle,
  },
  info: {
    classes: "border-[#C4DBFA] bg-[#EAF2FD] text-[#1E4F8A]",
    Icon: Info,
  },
  synthetic: {
    classes: "border-[#BBE5DF] bg-[#E7F7F5] text-[#12625B]",
    Icon: Sparkles,
  },
  neutral: {
    classes: "border-hairline bg-well text-ink-secondary",
    Icon: Info,
  },
};

export function StatusIndicator({
  tone = "neutral",
  label,
  className = "",
}: {
  tone?: Tone;
  label: string;
  className?: string;
}) {
  const { classes, Icon } = TONE_MAP[tone];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${classes} ${className}`}
    >
      <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      <span>{label}</span>
    </span>
  );
}
