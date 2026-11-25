"use client";

import React from "react";
import { Loader2 } from "lucide-react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  loading?: boolean;
  size?: "sm" | "md";
}

export function PrimaryButton({
  children,
  className = "",
  loading = false,
  disabled,
  size = "md",
  ...props
}: ButtonProps) {
  const pad = size === "sm" ? "min-h-[38px] px-3.5 py-1.5 text-xs" : "min-h-[42px] px-4 py-2.5 text-sm";
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 rounded-[10px] bg-brand font-semibold text-white shadow-sm transition hover:bg-brand-hover active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-55 ${pad} ${className}`}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
      {children}
    </button>
  );
}

export const SecondaryButton = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ children, className = "", loading = false, disabled, size = "md", ...props }, ref) => {
    const pad =
      size === "sm" ? "min-h-[36px] px-3 py-1.5 text-xs" : "min-h-[40px] px-3.5 py-2 text-sm";
    return (
      <button
        ref={ref}
        {...props}
        disabled={disabled || loading}
        className={`inline-flex items-center justify-center gap-2 rounded-[10px] border border-[#CFD8D3] bg-surface font-semibold text-ink transition hover:border-brand/40 hover:bg-well/70 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-55 ${pad} ${className}`}
      >
        {loading && <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />}
        {children}
      </button>
    );
  }
);
SecondaryButton.displayName = "SecondaryButton";

export function DangerButton({
  children,
  className = "",
  loading = false,
  disabled,
  size = "md",
  ...props
}: ButtonProps) {
  const pad = size === "sm" ? "min-h-[36px] px-3 py-1.5 text-xs" : "min-h-[40px] px-3.5 py-2 text-sm";
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 rounded-[10px] bg-[#BF4840] font-semibold text-white transition hover:bg-[#A63A33] disabled:cursor-not-allowed disabled:opacity-55 ${pad} ${className}`}
    >
      {loading && <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />}
      {children}
    </button>
  );
}

export function TextButton({
  children,
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className={`inline-flex min-h-[34px] items-center gap-1.5 rounded-lg px-2 py-1 text-xs font-semibold text-brand transition hover:bg-brand-tint hover:text-brand-hover disabled:opacity-50 ${className}`}
    >
      {children}
    </button>
  );
}

export function IconButton({
  children,
  label,
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { label: string }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      {...props}
      className={`inline-flex min-h-[36px] min-w-[36px] items-center justify-center rounded-lg border border-transparent p-1.5 text-ink-secondary transition hover:border-hairline hover:bg-well hover:text-ink disabled:opacity-45 sm:min-h-[32px] sm:min-w-[32px] ${className}`}
    >
      {children}
    </button>
  );
}
