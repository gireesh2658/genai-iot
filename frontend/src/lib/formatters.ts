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
