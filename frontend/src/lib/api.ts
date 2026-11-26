import type {
  AttackProfileSummary,
  CTGANGenerateRequest,
  CTGANGenerateResponse,
  CTGANModelSummary,
  EvaluationRunResponse,
  IoTDeviceProfileSummary,
  V2DeviceCatalogResponse,
} from "./types";

export const BACKEND_URL = (process.env.NEXT_PUBLIC_BACKEND_URL || "")
  .trim()
  .replace(/\/$/, "");
const API_BASE = BACKEND_URL ? `${BACKEND_URL}/api/v1` : "/api/v1";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  const text = await res.text();
  let parsed: any = {};
  try {
    parsed = text ? JSON.parse(text) : {};
  } catch {
    parsed = { message: text };
  }
  if (!res.ok) {
    throw new Error(
      parsed?.message || parsed?.detail || `Request failed (${res.status})`
    );
  }
  return parsed as T;
}

export const api = {
  listCtganModels: () =>
    fetchJson<{ total_models: number; models: CTGANModelSummary[] }>("/ctgan/models"),
  listV2Devices: () => fetchJson<V2DeviceCatalogResponse>("/ctgan/v2-devices"),
  listDeviceProfiles: () =>
    fetchJson<IoTDeviceProfileSummary[]>("/ctgan/device-profiles"),
  listAttackProfiles: () =>
    fetchJson<AttackProfileSummary[]>("/ctgan/attack-profiles"),
  generateCtganTraffic: (payload: CTGANGenerateRequest) =>
    fetchJson<CTGANGenerateResponse>("/ctgan/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  datasetDownloadUrl: (datasetId: string, format: "csv" | "parquet") =>
    `${API_BASE}/datasets/${encodeURIComponent(datasetId)}/download?format=${format}`,
  runEvaluation: (payload: {
    reference_dataset_id: string;
    synthetic_dataset_id: string;
    generate_plots?: boolean;
    generate_corrected_dataset?: boolean;
    test_conditional_sampling?: boolean;
  }) =>
    fetchJson<EvaluationRunResponse>("/evaluation/run", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
