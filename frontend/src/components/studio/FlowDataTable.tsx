"use client";

import React, { useMemo, useState } from "react";
import { Eye, Filter, Search } from "lucide-react";
import { Pagination } from "@/components/ui/Pagination";
import { StatusIndicator } from "@/components/ui/StatusIndicator";
import { EmptyState } from "@/components/ui/StateViews";

const CATEGORIES = [
  "Benign",
  "Brute Force",
  "Web-based",
  "Spoofing",
  "Reconnaissance",
  "Mirai",
  "DoS",
  "DDoS",
];

export function FlowDataTable({
  records,
  totalRecords,
  onInspectRecord,
}: {
  records: Record<string, any>[];
  totalRecords: number;
  onInspectRecord: (row: Record<string, any>) => void;
}) {
  const [query, setQuery] = useState("");
  const [catFilter, setCatFilter] = useState("All");
  const [devFilter, setDevFilter] = useState("All");
  const [page, setPage] = useState(1);
  const pageSize = 15;

  const uniqueDevices = useMemo(() => {
    const s = new Set<string>();
    records.forEach((r) => r.device_category && s.add(String(r.device_category)));
    return Array.from(s);
  }, [records]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return records.filter((r) => {
      if (catFilter !== "All" && String(r.label_category) !== catFilter) return false;
      if (devFilter !== "All" && String(r.device_category || "") !== devFilter) return false;
      if (q) {
        const hay = `${r.device_id || ""} ${r.device_category || ""} ${r.label_raw || ""} ${
          r.label_category || ""
        } ${r.protocol_name || ""}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [records, query, catFilter, devFilter]);

  const paged = useMemo(() => {
    const start = (page - 1) * pageSize;
    return filtered.slice(start, start + pageSize);
  }, [filtered, page]);

  if (records.length === 0) {
    return (
      <EmptyState
        title="No Flow Records Loaded"
        description="Synthesize traffic with CTGAN or inspect a saved dataset from the Vault to explore generated packets."
      />
    );
  }

  return (
    <div className="studio-panel overflow-hidden">
      {/* Scope Transparency Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-hairline bg-well/65 px-4 py-3 text-xs">
        <div className="text-ink-secondary">
          Loaded <strong className="font-mono text-ink">{records.length}</strong> preview records
          {totalRecords > records.length && (
            <span>
              {" "}
              (first {records.length} of{" "}
              <strong className="font-mono text-ink">{totalRecords.toLocaleString()}</strong> total
              saved flows)
            </span>
          )}
        </div>
        <div className="font-mono text-[11px] font-semibold text-ink-secondary tabular-nums">
          {filtered.length} matching filter
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-2.5 border-b border-hairline px-4 py-3">
        <div className="relative min-w-[210px] flex-1">
          <Search
            className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-ink-muted"
            aria-hidden="true"
          />
          <input
            aria-label="Filter preview flows"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setPage(1);
            }}
            placeholder="Search device ID, attack label, or protocol..."
            className="studio-input py-1.5 pl-9 text-xs"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Filter className="h-3.5 w-3.5 text-ink-muted" aria-hidden="true" />
          <select
            aria-label="Filter by threat category"
            value={catFilter}
            onChange={(e) => {
              setCatFilter(e.target.value);
              setPage(1);
            }}
            className="studio-input w-40 py-1.5 text-xs"
          >
            <option value="All">All Categories</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>

          {uniqueDevices.length > 0 && (
            <select
              aria-label="Filter by device category"
              value={devFilter}
              onChange={(e) => {
                setDevFilter(e.target.value);
                setPage(1);
              }}
              className="studio-input w-44 py-1.5 text-xs"
            >
              <option value="All">All IoT Devices</option>
              {uniqueDevices.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      {/* Horizontal-scroll isolated table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs tabular-nums">
          <thead className="bg-well/60 text-[11px] font-semibold uppercase tracking-wide text-ink-secondary">
            <tr>
              <th className="px-3.5 py-2.5">Device ID</th>
              <th className="px-3.5 py-2.5">Protocol</th>
              <th className="px-3.5 py-2.5 text-right">Rate (/s)</th>
              <th className="px-3.5 py-2.5 text-right">AVG (B)</th>
              <th className="px-3.5 py-2.5 text-right">Std (B)</th>
              <th className="px-3.5 py-2.5">Category</th>
              <th className="px-3.5 py-2.5">Raw Signature</th>
              <th className="px-3.5 py-2.5 text-right">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-hairline bg-surface">
            {paged.map((r, i) => (
              <tr key={i} className="transition hover:bg-[#FAFBF9]">
                <td className="px-3.5 py-2 font-mono text-[11px] font-semibold text-ink">
                  <div>{r.device_id || "raw_ciciot"}</div>
                  {r.device_category && (
                    <div className="font-sans text-[10px] font-medium text-ink-secondary">
                      {String(r.device_category)}
                    </div>
                  )}
                </td>
                <td className="px-3.5 py-2 font-mono text-ink-secondary">{r.protocol_name}</td>
                <td className="px-3.5 py-2 text-right font-mono text-ink">
                  {Number(r.Rate).toFixed(1)}
                </td>
                <td className="px-3.5 py-2 text-right font-mono text-ink">
                  {Number(r.AVG).toFixed(1)}
                </td>
                <td className="px-3.5 py-2 text-right font-mono text-ink-secondary">
                  {Number(r.Std).toFixed(2)}
                </td>
                <td className="px-3.5 py-2">
                  <StatusIndicator
                    tone={Number(r.is_attack) === 0 ? "success" : "danger"}
                    label={String(r.label_category)}
                  />
                </td>
                <td className="px-3.5 py-2 font-mono text-[11px] text-ink-secondary">
                  {r.label_raw}
                </td>
                <td className="px-3.5 py-2 text-right">
                  <button
                    type="button"
                    onClick={() => onInspectRecord(r)}
                    className="inline-flex min-h-[30px] items-center gap-1 rounded-lg px-2 py-1 font-semibold text-brand hover:bg-brand-tint"
                  >
                    <Eye className="h-3.5 w-3.5" aria-hidden="true" />
                    Inspect
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Pagination
        page={page}
        totalItems={filtered.length}
        pageSize={pageSize}
        onPageChange={setPage}
      />
    </div>
  );
}
