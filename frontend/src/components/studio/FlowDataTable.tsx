"use client";

import React, { useEffect, useMemo, useState } from "react";
import { Eye, Search } from "lucide-react";
import { Pagination } from "@/components/ui/Pagination";
import { StatusIndicator } from "@/components/ui/StatusIndicator";
import { EmptyState } from "@/components/ui/StateViews";

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
  const [page, setPage] = useState(1);
  const pageSize = 10;

  useEffect(() => {
    setPage(1);
    setQuery("");
    setCatFilter("All");
  }, [records]);

  const categories = useMemo(() => {
    const s = new Set<string>();
    records.forEach((r) => {
      if (r.label_category) s.add(String(r.label_category));
    });
    return Array.from(s);
  }, [records]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return records.filter((r) => {
      if (catFilter !== "All" && String(r.label_category) !== catFilter) return false;
      if (q) {
        const hay = `${r.device_id || ""} ${r.device_category || ""} ${
          r.label_raw || ""
        } ${r.label_category || ""} ${r.protocol_name || ""}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [records, query, catFilter]);

  const paged = useMemo(() => {
    const start = (page - 1) * pageSize;
    return filtered.slice(start, start + pageSize);
  }, [filtered, page]);

  if (records.length === 0) {
    return (
      <EmptyState
        title="No Preview Rows Available"
        description="Generate synthetic traffic to inspect sample records."
      />
    );
  }

  return (
    <section className="studio-panel overflow-hidden" aria-label="Dataset preview">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-hairline px-4 py-3">
        <div className="text-xs text-ink-secondary">
          Showing preview of{" "}
          <strong className="font-mono text-ink">{records.length}</strong> sample rows
          {totalRecords > records.length && (
            <span>
              {" "}
              (from{" "}
              <strong className="font-mono text-ink">
                {totalRecords.toLocaleString()}
              </strong>{" "}
              total generated)
            </span>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:flex-nowrap">
          <div className="relative w-full sm:w-56">
            <Search
              className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-muted"
              aria-hidden="true"
            />
            <input
              id="preview-filter-query"
              name="previewFilterQuery"
              aria-label="Filter preview flows"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(1);
              }}
              placeholder="Filter device, attack, protocol..."
              className="studio-input py-1 pl-8 text-xs"
            />
          </div>

          {categories.length > 1 && (
            <select
              id="preview-category-filter"
              name="previewCategoryFilter"
              aria-label="Filter by traffic category"
              value={catFilter}
              onChange={(e) => {
                setCatFilter(e.target.value);
                setPage(1);
              }}
              className="studio-input w-full sm:w-36 py-1 text-xs"
            >
              <option value="All">All Classes</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs tabular-nums">
          <thead className="bg-well/65 text-[11px] font-semibold uppercase tracking-wide text-ink-secondary">
            <tr>
              <th className="px-3.5 py-2.5">Device</th>
              <th className="px-3.5 py-2.5">Protocol</th>
              <th className="px-3.5 py-2.5 text-right">Rate (/s)</th>
              <th className="px-3.5 py-2.5 text-right">AVG (B)</th>
              <th className="px-3.5 py-2.5 text-right">Std (B)</th>
              <th className="px-3.5 py-2.5">Category</th>
              <th className="px-3.5 py-2.5">Label</th>
              <th className="px-3.5 py-2.5 text-right">Inspect</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-hairline bg-surface">
            {paged.map((r, i) => (
              <tr
                key={`${r.device_id || "row"}-${(page - 1) * pageSize + i}`}
                className="transition hover:bg-[#FAFBF9]"
              >
                <td className="px-3.5 py-2 font-mono text-[11px] font-semibold text-ink">
                  <div>{r.device_id || "--"}</div>
                  {r.device_category && (
                    <div className="font-sans text-[10px] font-medium text-ink-secondary">
                      {String(r.device_category)}
                    </div>
                  )}
                </td>
                <td className="px-3.5 py-2 font-mono text-ink-secondary">
                  {r.protocol_name || "--"}
                </td>
                <td className="px-3.5 py-2 text-right font-mono text-ink">
                  {Number.isFinite(Number(r.Rate)) ? Number(r.Rate).toFixed(1) : "--"}
                </td>
                <td className="px-3.5 py-2 text-right font-mono text-ink">
                  {Number.isFinite(Number(r.AVG)) ? Number(r.AVG).toFixed(1) : "--"}
                </td>
                <td className="px-3.5 py-2 text-right font-mono text-ink-secondary">
                  {Number.isFinite(Number(r.Std)) ? Number(r.Std).toFixed(2) : "--"}
                </td>
                <td className="px-3.5 py-2">
                  <StatusIndicator
                    tone={Number(r.is_attack) === 0 ? "success" : "danger"}
                    label={String(r.label_category || "Unknown")}
                  />
                </td>
                <td className="px-3.5 py-2 font-mono text-[11px] text-ink-secondary">
                  {r.label_raw || "--"}
                </td>
                <td className="px-3.5 py-2 text-right">
                  <button
                    type="button"
                    onClick={() => onInspectRecord(r)}
                    className="inline-flex min-h-[30px] items-center gap-1 rounded-lg px-2 py-1 font-semibold text-brand hover:bg-brand-tint"
                  >
                    <Eye className="h-3.5 w-3.5" aria-hidden="true" />
                    Row
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
    </section>
  );
}
