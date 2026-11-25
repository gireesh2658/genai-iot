export function fmtNumber(val: number | null | undefined, decimals = 0): string {
  if (typeof val !== "number" || !Number.isFinite(val)) return "--";
  return val.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function fmtMetric(val: number | null | undefined, digits = 4): string {
  if (typeof val !== "number" || !Number.isFinite(val)) return "--";
  return val.toFixed(digits);
}

export function fmtSignedDelta(val: number | null | undefined, digits = 4): string {
  if (typeof val !== "number" || !Number.isFinite(val)) return "--";
  const prefix = val > 0 ? "+" : "";
  return `${prefix}${val.toFixed(digits)}`;
}

export function fmtBytes(bytes: number | null | undefined): string {
  if (typeof bytes !== "number" || !Number.isFinite(bytes)) return "--";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function fmtTimestamp(iso: string | null | undefined): string {
  if (!iso) return "--";
  if (iso === "Baseline Reference") return iso;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function fmtClassifierName(key: string): string {
  const map: Record<string, string> = {
    random_forest: "Random Forest",
    extra_trees: "Extra Trees",
    hist_gradient_boosting: "HistGradientBoosting",
    logistic_regression: "Logistic Regression",
  };
  return map[key] || key;
}

export function fmtDeviceName(profileName: string): string {
  const map: Record<string, string> = {
    smart_camera: "Smart Camera",
    smart_thermostat: "Smart Thermostat",
    smart_bulb: "Smart Bulb",
    smart_speaker: "Smart Speaker",
    smart_plug: "Smart Plug",
    motion_sensor: "Motion Sensor",
  };
  return (
    map[profileName] ||
    profileName
      .split("_")
      .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : ""))
      .join(" ")
  );
}

export function interpretKs(ks: number | null | undefined): { label: string; tone: "good" | "warn" | "neutral" } {
  if (typeof ks !== "number") return { label: "Unavailable", tone: "neutral" };
  if (ks <= 0.15) return { label: "Tight empirical fit", tone: "good" };
  if (ks <= 0.36) return { label: "Moderate drift", tone: "neutral" };
  return { label: "High distribution shift", tone: "warn" };
}
