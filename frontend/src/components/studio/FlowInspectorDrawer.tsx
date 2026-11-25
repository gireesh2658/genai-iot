"use client";

import React from "react";
import { Drawer } from "@/components/ui/Drawer";
import { StatusIndicator } from "@/components/ui/StatusIndicator";

const ATTRIBUTE_GROUPS: Array<{ title: string; keys: string[] }> = [
  {
    title: "Device & Taxonomy Labels",
    keys: [
      "device_id",
      "device_category",
      "label_category",
      "label_raw",
      "is_attack",
      "protocol_name",
      "Protocol Type",
    ],
  },
  {
    title: "Timing, Volume & Packet Sizes",
    keys: [
      "Header_Length",
      "Time_To_Live",
      "Rate",
      "IAT",
      "Number",
      "Min",
      "Max",
      "AVG",
      "Std",
      "Variance",
      "Tot sum",
    ],
  },
  {
    title: "TCP Flag Proportions & Counts",
    keys: [
      "syn_count",
      "ack_count",
      "fin_count",
      "rst_count",
      "syn_flag_number",
      "ack_flag_number",
      "fin_flag_number",
      "rst_flag_number",
      "psh_flag_number",
      "ece_flag_number",
      "cwr_flag_number",
    ],
  },
  {
    title: "Protocol / Application Ratios",
    keys: [
      "TCP",
      "UDP",
      "ICMP",
      "HTTP",
      "HTTPS",
      "DNS",
      "SSH",
      "Telnet",
      "SMTP",
      "IRC",
      "DHCP",
      "ARP",
      "IGMP",
      "IPv",
      "LLC",
    ],
  },
];

export function FlowInspectorDrawer({
  record,
  onClose,
}: {
  record: Record<string, any> | null;
  onClose: () => void;
}) {
  if (!record) return null;

  const totalKeys = Object.keys(record).length;
  const isBenign = Number(record.is_attack) === 0;

  return (
    <Drawer
      open={Boolean(record)}
      onClose={onClose}
      title={`${record.device_id || "CICIoT2023 Flow"} Telemetry Vector`}
      subtitle={`${totalKeys} attributes · ${record.label_category} (${record.label_raw})`}
    >
      <div className="space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-hairline bg-well/60 p-3.5">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-wider text-ink-secondary">
              Classification State
            </div>
            <div className="mt-0.5 font-mono text-sm font-bold text-ink">
              {record.label_raw}
            </div>
          </div>
          <StatusIndicator
            tone={isBenign ? "success" : "danger"}
            label={isBenign ? `Benign (is_attack=0)` : `${record.label_category} (is_attack=1)`}
          />
        </div>

        {ATTRIBUTE_GROUPS.map((grp) => {
          const present = grp.keys.filter((k) => k in record);
          if (present.length === 0) return null;
          return (
            <div key={grp.title}>
              <h3 className="mb-2 text-xs font-bold uppercase tracking-wider text-ink-secondary">
                {grp.title}
              </h3>
              <div className="grid grid-cols-2 gap-2">
                {present.map((k) => {
                  const val = record[k];
                  const formatted =
                    typeof val === "number"
                      ? Number.isInteger(val)
                        ? String(val)
                        : val.toFixed(4)
                      : String(val);
                  return (
                    <div
                      key={k}
                      className="rounded-lg border border-hairline bg-canvas px-3 py-2"
                    >
                      <div className="truncate font-mono text-[10px] font-semibold text-ink-secondary">
                        {k}
                      </div>
                      <div className="mt-0.5 truncate font-mono text-xs font-bold text-ink tabular-nums">
                        {formatted}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </Drawer>
  );
}
