"use client";

import React, { useState } from "react";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { EmptyState } from "@/components/ui/StateViews";

function corrColor(val: number): { bg: string; fg: string } {
  const clamped = Math.max(-1, Math.min(1, val));
  const abs = Math.abs(clamped);
  if (clamped >= 0) {
    return {
      bg: `rgba(42, 103, 177, ${0.06 + abs * 0.62})`,
      fg: abs > 0.55 ? "#FFFFFF" : "#2B3748",
    };
  }
  return {
    bg: `rgba(191, 72, 64, ${0.06 + abs * 0.62})`,
    fg: abs > 0.55 ? "#FFFFFF" : "#2B3748",
  };
}

function deltaColor(absVal: number): { bg: string; fg: string } {
  const clamped = Math.max(0, Math.min(1, absVal));
  return {
    bg: `rgba(100, 89, 186, ${0.06 + clamped * 0.72})`,
    fg: clamped > 0.5 ? "#FFFFFF" : "#2B3748",
  };
}

function MatrixGrid({
  title,
  features,
  matrix,
  isDelta = false,
  onSelectCell,
}: {
  title: string;
  features: string[];
  matrix: Record<string, Record<string, number>>;
  isDelta?: boolean;
  onSelectCell: (f1: string, f2: string) => void;
}) {
  return (
    <div className="min-w-0">
      <div className="mb-2 text-xs font-bold text-ink">{title}</div>
      <div className="overflow-x-auto rounded-xl border border-hairline">
        <table className="w-full border-collapse text-center text-[10px] tabular-nums">
          <thead>
            <tr className="bg-well/75 text-ink-secondary">
              <th className="sticky left-0 z-10 bg-well px-2 py-1.5 text-left font-bold">Feat</th>
              {features.map((f) => (
                <th key={f} title={f} className="px-1.5 py-1.5 font-mono font-semibold">
                  {f.slice(0, 5)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {features.map((rowF) => (
              <tr key={rowF}>
                <th
                  scope="row"
                  title={rowF}
                  className="sticky left-0 z-10 border-t border-hairline bg-well/65 px-2 py-1 text-left font-mono font-semibold text-ink"
                >
                  {rowF.slice(0, 10)}
                </th>
                {features.map((colF) => {
                  const val = Number(matrix?.[rowF]?.[colF] ?? 0);
                  const colors = isDelta ? deltaColor(Math.abs(val)) : corrColor(val);
                  return (
                    <td
                      key={colF}
                      style={{ backgroundColor: colors.bg, color: colors.fg }}
                      className="border-t border-l border-hairline/70 p-0"
                    >
                      <button
                        type="button"
                        onMouseEnter={() => onSelectCell(rowF, colF)}
                        onFocus={() => onSelectCell(rowF, colF)}
                        onClick={() => onSelectCell(rowF, colF)}
                        aria-label={`${rowF} vs ${colF}: ${val.toFixed(2)}`}
                        className="block h-7 w-full px-1 font-mono text-[10px] font-medium hover:ring-1 hover:ring-inset hover:ring-ink"
                      >
                        {val.toFixed(2)}
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function CorrelationHeatmaps({
  correlationReport,
}: {
  correlationReport: Record<string, any> | null;
}) {
  const [method, setMethod] = useState<"pearson" | "spearman">("pearson");
  const [view, setView] = useState<"pair" | "delta">("pair");
  const [hoverPair, setHoverPair] = useState<{ f1: string; f2: string } | null>(null);

  const activeBlock = correlationReport?.[method];
  const features: string[] = activeBlock?.features || [];
  const realMat = activeBlock?.real_correlation_matrix || {};
  const synthMat = activeBlock?.synthetic_correlation_matrix || {};
  const diffMat = activeBlock?.difference_matrix || {};

  if (!activeBlock || features.length === 0) {
    return (
      <section className="studio-panel p-5">
        <EmptyState
          title="Correlation Matrices Unavailable"
          description="Select phase6_approved or run an evaluation audit to inspect real vs synthetic 13×13 correlation heatmaps."
        />
      </section>
    );
  }

  const f1 = hoverPair?.f1 || features[0];
  const f2 = hoverPair?.f2 || features[Math.min(1, features.length - 1)];
  const rVal = Number(realMat?.[f1]?.[f2] ?? 0);
  const sVal = Number(synthMat?.[f1]?.[f2] ?? 0);
  const dVal = Number(diffMat?.[f1]?.[f2] ?? 0);

  return (
    <section className="studio-panel space-y-5 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="flex items-center text-sm font-bold text-ink">
            Multivariate Correlation Comparison (13×13 Features)
            <InfoTooltip term="Pearson MACE" />
          </h3>
          <p className="mt-0.5 text-xs text-ink-secondary">
            Hover or focus any cell to inspect pairwise correlation fidelity. MACE:{" "}
            <strong className="font-mono text-ink">
              {Number(activeBlock.mean_absolute_correlation_error).toFixed(4)}
            </strong>{" "}
            · Frobenius:{" "}
            <strong className="font-mono text-ink">
              {Number(activeBlock.frobenius_norm).toFixed(4)}
            </strong>
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="inline-flex rounded-lg border border-hairline bg-well p-0.5 text-xs font-semibold">
            <button
              type="button"
              onClick={() => setMethod("pearson")}
              className={`rounded-md px-2.5 py-1 ${
                method === "pearson" ? "bg-surface text-brand shadow-sm" : "text-ink-secondary"
              }`}
            >
              Pearson
            </button>
            <button
              type="button"
              onClick={() => setMethod("spearman")}
              className={`rounded-md px-2.5 py-1 ${
                method === "spearman" ? "bg-surface text-brand shadow-sm" : "text-ink-secondary"
              }`}
            >
              Spearman
            </button>
          </div>

          <div className="inline-flex rounded-lg border border-hairline bg-well p-0.5 text-xs font-semibold">
            <button
              type="button"
              onClick={() => setView("pair")}
              className={`rounded-md px-2.5 py-1 ${
                view === "pair" ? "bg-surface text-brand shadow-sm" : "text-ink-secondary"
              }`}
            >
              Real vs Synthetic
            </button>
            <button
              type="button"
              onClick={() => setView("delta")}
              className={`rounded-md px-2.5 py-1 ${
                view === "delta" ? "bg-surface text-signal-lavender shadow-sm" : "text-ink-secondary"
              }`}
            >
              Error Matrix (Δr)
            </button>
          </div>
        </div>
      </div>

      {/* Live Inspected Cell Bar + Color Scale Legend */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-hairline bg-well/65 px-4 py-2.5 text-xs">
        <div className="font-mono">
          Inspecting: <strong className="text-ink">{f1}</strong> ×{" "}
          <strong className="text-ink">{f2}</strong> → Real:{" "}
          <strong className="text-brand">{rVal.toFixed(4)}</strong> | Synth:{" "}
          <strong className="text-signal">{sVal.toFixed(4)}</strong> | Delta:{" "}
          <strong className="text-signal-lavender">{dVal.toFixed(4)}</strong>
        </div>
        <div className="flex items-center gap-3 text-[11px] font-medium text-ink-secondary">
          <span className="flex items-center gap-1">
            <span className="h-2.5 w-2.5 rounded bg-[#2A67B1]/75" /> Positive (+1)
          </span>
          <span className="flex items-center gap-1">
            <span className="h-2.5 w-2.5 rounded bg-[#BF4840]/75" /> Negative (-1)
          </span>
          <span className="flex items-center gap-1">
            <span className="h-2.5 w-2.5 rounded bg-[#6459BA]/75" /> |Δr| Divergence
          </span>
        </div>
      </div>

      {view === "pair" ? (
        <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
          <MatrixGrid
            title="Real CICIoT2023 Training Matrix"
            features={features}
            matrix={realMat}
            onSelectCell={(a, b) => setHoverPair({ f1: a, f2: b })}
          />
          <MatrixGrid
            title="Synthetic CTGAN Matrix"
            features={features}
            matrix={synthMat}
            onSelectCell={(a, b) => setHoverPair({ f1: a, f2: b })}
          />
        </div>
      ) : (
        <MatrixGrid
          title="Difference Matrix (Synthetic − Real)"
          features={features}
          matrix={diffMat}
          isDelta
          onSelectCell={(a, b) => setHoverPair({ f1: a, f2: b })}
        />
      )}
    </section>
  );
}
