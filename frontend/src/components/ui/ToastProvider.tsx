"use client";

import React, { createContext, useCallback, useContext, useState } from "react";
import { CheckCircle2, Info, X, XCircle } from "lucide-react";

type ToastType = "success" | "error" | "info";

interface ToastItem {
  id: number;
  type: ToastType;
  title: string;
  detail?: string;
}

const ToastContext = createContext<{
  pushToast: (type: ToastType, title: string, detail?: string) => void;
}>({ pushToast: () => {} });

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const pushToast = useCallback((type: ToastType, title: string, detail?: string) => {
    const id = Date.now() + Math.floor(Math.random() * 1000);
    setToasts((prev) => [...prev.slice(-3), { id, type, title, detail }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 5500);
  }, []);

  const dismiss = (id: number) => setToasts((prev) => prev.filter((t) => t.id !== id));

  return (
    <ToastContext.Provider value={{ pushToast }}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-full max-w-sm flex-col gap-2 px-4 sm:px-0"
      >
        {toasts.map((t) => {
          const isOk = t.type === "success";
          const isErr = t.type === "error";
          return (
            <div
              key={t.id}
              className={`pointer-events-auto flex items-start gap-3 rounded-xl border bg-surface p-3.5 shadow-lg ${
                isOk
                  ? "border-[#B9E4D4]"
                  : isErr
                  ? "border-[#F2C3BF]"
                  : "border-[#C4DBFA]"
              }`}
            >
              {isOk ? (
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#1A7D5E]" />
              ) : isErr ? (
                <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-[#BF4840]" />
              ) : (
                <Info className="mt-0.5 h-4 w-4 shrink-0 text-brand" />
              )}
              <div className="min-w-0 flex-1">
                <div className="text-xs font-bold text-ink">{t.title}</div>
                {t.detail && <div className="mt-0.5 text-[11px] text-ink-secondary">{t.detail}</div>}
              </div>
              <button
                type="button"
                aria-label="Dismiss notification"
                onClick={() => dismiss(t.id)}
                className="rounded p-1 text-ink-secondary hover:bg-well hover:text-ink"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}
