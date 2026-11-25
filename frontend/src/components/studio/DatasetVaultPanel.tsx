"use client";

import React, { useMemo, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, Database, Eye, RefreshCw, Search, Trash2 } from "lucide-react";
import { AttackProfileSummary, DatasetItem } from "@/lib/types";
import { fmtBytes, fmtTimestamp } from "@/lib/formatters";
import { IconButton, SecondaryButton } from "@/components/ui/Button";
import { ExportMenu } from "@/components/ui/ExportMenu";
import { StatusIndicator } from "@/components/ui/StatusIndicator";

export function DatasetVaultPanel({
  datasets,
  attackProfiles,
  activeDatasetId,
  onInspectDataset,
  onRequestDeleteDataset,
  onRefresh,
}: {
  datasets: DatasetItem[];
  attackProfiles: AttackProfileSummary[];
  activeDatasetId: string | null;
  onInspectDataset: (datasetId: string) => void;
  onRequestDeleteDataset: (datasetId: string) => void;
  onRefresh: () => void;
}) {
  const [attackSearch, setAttackSearch] = useState("");

  const filteredAttacks = useMemo(() => {
    const q = attackSearch.trim().toLowerCase();
    if (!q) return attackProfiles;
    return attackProfiles.filter((a) =>
      `${a.label_raw} ${a.label_category} ${a.protocol_name}`.toLowerCase().includes(q)
    );
  }, [attackProfiles, attackSearch]);

  return (
    <div className="space-y-5">
      {/* Persisted Synthetic Dataset Vault */}
      <section className="studio-panel overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-hairline px-5 py-4">
          <div className="flex items-center gap-2">
            <Database className="h-4 w-4 text-brand" aria-hidden="true" />
            <div>
              <h3 className="text-sm font-bold text-ink">
                Generated Dataset Vault ({datasets.length})
              </h3>
              <p className="text-xs text-ink-secondary">
                Inspect saved telemetry, export CSV/Parquet, or send directly into Quality Audit and Anomaly Lab.
              </p>
            </div>
          </div>
          <SecondaryButton size="sm" onClick={onRefresh}>
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </SecondaryButton>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs tabular-nums">
            <thead className="bg-well/65 text-[11px] font-semibold uppercase tracking-wide text-ink-secondary">
              <tr>
                <th className="px-4 py-2.5">Dataset Identifier</th>
                <th className="px-4 py-2.5">Shape</th>
                <th className="px-4 py-2.5">File Size</th>
                <th className="px-4 py-2.5">Status</th>
                <th className="px-4 py-2.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-hairline bg-surface">
              {datasets.map((d) => {
                const isActive = d.dataset_id === activeDatasetId;
                return (
                  <tr
                    key={d.dataset_id}
                    className={isActive ? "bg-brand-tint/45" : "hover:bg-[#FAFBF9]"}
                  >
                    <td className="px-4 py-3">
                      <div className="font-mono font-bold text-ink">{d.dataset_id}</div>
                      <div className="mt-0.5 text-[10px] text-ink-muted">
                        Updated {fmtTimestamp(d.created_at)}
                      </div>
                    </td>
                    <td className="px-4 py-3 font-mono text-ink">
                      {d.num_records?.toLocaleString() ?? "--"} × {d.num_columns ?? "--"}
                    </td>
                    <td className="px-4 py-3 font-mono text-ink-secondary">
                      {fmtBytes(d.size_bytes)}
                    </td>
                    <td className="px-4 py-3">
                      {d.is_protected ? (
                        <StatusIndicator tone="info" label="Baseline Reference" />
                      ) : (
                        <StatusIndicator tone="synthetic" label="Generated" />
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="inline-flex flex-wrap items-center justify-end gap-1.5">
                        <SecondaryButton
                          size="sm"
                          type="button"
                          onClick={() => onInspectDataset(d.dataset_id)}
                        >
                          <Eye className="h-3.5 w-3.5" /> Inspect
                        </SecondaryButton>

                        <ExportMenu datasetId={d.dataset_id} availableFormats={d.available_formats} />

                        <Link
                          href={`/quality?dataset=${encodeURIComponent(d.dataset_id)}`}
                          className="inline-flex min-h-[34px] items-center gap-1 rounded-[10px] border border-hairline bg-well/60 px-2.5 py-1 text-xs font-semibold text-brand hover:border-[#C4DBFA] hover:bg-brand-tint"
                        >
                          Audit <ArrowUpRight className="h-3 w-3" />
                        </Link>

                        {!d.is_protected && (
                          <IconButton
                            label={`Delete dataset ${d.dataset_id}`}
                            onClick={() => onRequestDeleteDataset(d.dataset_id)}
                            className="hover:border-[#F2C3BF] hover:bg-[#FDECEC] hover:text-[#BF4840]"
                          >
                            <Trash2 className="h-4 w-4" />
                          </IconButton>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Supported Attack Profiles Reference */}
      <section className="studio-panel overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-hairline px-5 py-4">
          <div>
            <h3 className="text-sm font-bold text-ink">
              CICIoT2023 Attack Taxonomy Catalog ({attackProfiles.length} Specifications)
            </h3>
            <p className="text-xs text-ink-secondary">
              Backend specification metadata (`GET /api/v1/ctgan/attack-profiles`). Note: <code className="font-mono">UPLOADING_ATTACK</code> has 0 real samples in the training corpus.
            </p>
          </div>
          <div className="relative w-64">
            <Search
              className="pointer-events-none absolute left-3 top-2.5 h-3.5 w-3.5 text-ink-muted"
              aria-hidden="true"
            />
            <input
              aria-label="Search attack catalog"
              value={attackSearch}
              onChange={(e) => setAttackSearch(e.target.value)}
              placeholder="Search Mirai, Flood, TCP..."
              className="studio-input py-1.5 pl-8 text-xs"
            />
          </div>
        </div>

        <div className="max-h-72 overflow-auto">
          <table className="w-full text-left text-xs tabular-nums">
            <thead className="sticky top-0 bg-well/80 text-[11px] font-semibold uppercase tracking-wide text-ink-secondary">
              <tr>
                <th className="px-4 py-2">Raw Signature</th>
                <th className="px-4 py-2">Macro Category</th>
                <th className="px-4 py-2">Protocol</th>
                <th className="px-4 py-2">Packet Bounds</th>
                <th className="px-4 py-2">Expected Rate (/s)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-hairline bg-surface">
              {filteredAttacks.map((atk) => (
                <tr key={atk.attack_id} className="hover:bg-[#FAFBF9]">
                  <td className="px-4 py-2 font-mono font-bold text-ink">{atk.label_raw}</td>
                  <td className="px-4 py-2 font-semibold text-brand">{atk.label_category}</td>
                  <td className="px-4 py-2 font-mono text-ink-secondary">
                    {atk.protocol_name} ({atk.protocol_type})
                  </td>
                  <td className="px-4 py-2 font-mono text-ink-secondary">
                    {atk.packet_size_min}–{atk.packet_size_max} B
                  </td>
                  <td className="px-4 py-2 font-mono text-ink-secondary">
                    {atk.rate_min.toLocaleString()}–{atk.rate_max.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
