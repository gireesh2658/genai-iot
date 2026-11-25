"use client";

import React, { useEffect, useRef } from "react";
import { AlertTriangle, X } from "lucide-react";
import { DangerButton, IconButton, SecondaryButton } from "./Button";

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Confirm Delete",
  busy = false,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const cancelRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (!open) return;
    cancelRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
    >
      <div
        className="fixed inset-0 bg-[#2B3748]/25 backdrop-blur-[1px]"
        onClick={onCancel}
        aria-hidden="true"
      />
      <div className="relative z-10 w-full max-w-md rounded-2xl border border-hairline bg-surface p-6 shadow-xl">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#FDECEC] text-[#BF4840]">
              <AlertTriangle className="h-5 w-5" aria-hidden="true" />
            </div>
            <h2 id="confirm-dialog-title" className="text-base font-bold text-ink">
              {title}
            </h2>
          </div>
          <IconButton label="Close confirmation" onClick={onCancel}>
            <X className="h-4 w-4" />
          </IconButton>
        </div>

        <p className="mt-3 text-sm leading-relaxed text-ink-secondary">{description}</p>

        <div className="mt-5 flex flex-wrap justify-end gap-2.5">
          <SecondaryButton ref={cancelRef} type="button" onClick={onCancel}>
            Cancel
          </SecondaryButton>
          <DangerButton type="button" loading={busy} onClick={onConfirm}>
            {confirmLabel}
          </DangerButton>
        </div>
      </div>
    </div>
  );
}
