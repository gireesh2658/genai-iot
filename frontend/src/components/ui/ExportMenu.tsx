"use client";

import React, { useEffect, useRef, useState } from "react";
import { ChevronDown, Download, FileSpreadsheet, Package } from "lucide-react";
import { api } from "@/lib/api";
import { useToast } from "./ToastProvider";

function buildCsvBlobUrl(records: Record<string, unknown>[]): string {
  if (records.length === 0) return "";
  const headers = Array.from(
    records.reduce((cols, row) => {
      Object.keys(row).forEach((k) => cols.add(k));
      return cols;
    }, new Set<string>())
  );
  const escapeCsv = (val: unknown): string => {
    const raw = val === null || val === undefined ? "" : String(val);
    if (/[",\n\r]/.test(raw)) {
      return `"${raw.replace(/"/g, '""')}"`;
    }
    return raw;
  };
  const lines = [
    headers.map(escapeCsv).join(","),
    ...records.map((row) => headers.map((h) => escapeCsv(row[h])).join(",")),
  ];
  const blob = new Blob([lines.join("\r\n")], { type: "text/csv;charset=utf-8;" });
  return URL.createObjectURL(blob);
}

export function ExportMenu({
  datasetId,
  records,
  fallbackFilename = "iot_synthetic_preview",
  availableFormats = ["csv", "parquet"],
  size = "sm",
}: {
  datasetId?: string | null;
  records?: Record<string, unknown>[];
  fallbackFilename?: string;
  availableFormats?: string[];
  size?: "sm" | "md";
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const { pushToast } = useToast();

  useEffect(() => {
    if (!open) return;
    const onDocClick = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onDocClick);
    window.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const hasServerDataset = Boolean(datasetId);
  const hasMemoryRecords = Boolean(records && records.length > 0);
  const supportsCsv =
    hasMemoryRecords ||
    (hasServerDataset &&
      (availableFormats.length === 0 || availableFormats.includes("csv") || availableFormats.includes("parquet")));
  const supportsParquet =
    hasServerDataset &&
    (availableFormats.length === 0 || availableFormats.includes("parquet") || availableFormats.includes("csv"));

  const handleCsvDownload = (e: React.MouseEvent<HTMLAnchorElement>) => {
    if (!datasetId && records && records.length > 0) {
      e.preventDefault();
      const blobUrl = buildCsvBlobUrl(records);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = `${fallbackFilename}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(blobUrl), 1500);
      setOpen(false);
      pushToast("info", "Exporting CSV", `Downloaded ${fallbackFilename}.csv from memory`);
      return;
    }
    setOpen(false);
    if (datasetId) {
      pushToast("info", "Exporting CSV", `Downloading ${datasetId}.csv`);
    }
  };

  const pad = size === "sm" ? "min-h-[34px] px-3 py-1 text-xs" : "min-h-[40px] px-3.5 py-2 text-sm";

  return (
    <div ref={rootRef} className="relative inline-block text-left">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className={`inline-flex items-center gap-1.5 rounded-[10px] border border-[#CFD8D3] bg-surface font-semibold text-ink transition hover:border-brand/40 hover:bg-well/70 ${pad}`}
      >
        <Download className="h-3.5 w-3.5 text-brand" aria-hidden="true" />
        <span>Export</span>
        <ChevronDown className="h-3.5 w-3.5 text-ink-secondary" aria-hidden="true" />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 z-30 mt-1.5 w-48 rounded-xl border border-hairline bg-surface p-1.5 shadow-lg"
        >
          {supportsCsv && (
            <a
              role="menuitem"
              href={datasetId ? api.datasetDownloadUrl(datasetId, "csv") : "#"}
              onClick={handleCsvDownload}
              className="flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs font-semibold text-ink hover:bg-well"
            >
              <FileSpreadsheet className="h-4 w-4 text-signal" aria-hidden="true" />
              <span>CSV Spreadsheet (.csv)</span>
            </a>
          )}
          {supportsParquet && datasetId && (
            <a
              role="menuitem"
              href={api.datasetDownloadUrl(datasetId, "parquet")}
              onClick={() => {
                setOpen(false);
                pushToast("info", "Exporting Parquet", `Downloading ${datasetId}.parquet`);
              }}
              className="flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs font-semibold text-ink hover:bg-well"
            >
              <Package className="h-4 w-4 text-brand" aria-hidden="true" />
              <span>Apache Parquet (.parquet)</span>
            </a>
          )}
        </div>
      )}
    </div>
  );
}
