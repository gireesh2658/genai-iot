import type {
  AnomalyModelDetail,
  AnomalyModelSummary,
  AnomalyTrainResponse,
  AttackProfileSummary,
  CTGANGenerateRequest,
  CTGANGenerateResponse,
  CTGANModelDetail,
  CTGANModelSummary,
  CTGANTrainRequest,
  CTGANTrainResponse,
  DatasetDetail,
  DatasetItem,
  EvaluationDetailResponse,
  EvaluationRunResponse,
  EvaluationStatusResponse,
  EvaluationSummaryItem,
  ExperimentComparisonRecord,
  HealthResponse,
  IoTDeviceProfile,
  PredictBatchResponse,
  PredictSingleResponse,
  SystemModelsStatus,
  SystemStatus,
  V2DeviceCatalogResponse,
} from "./types";

export const BACKEND_URL = (process.env.NEXT_PUBLIC_BACKEND_URL || "").trim().replace(/\/$/, "");
const API_BASE = BACKEND_URL ? `${BACKEND_URL}/api/v1` : "/api/v1";
export const BACKEND_DOCS_URL = BACKEND_URL ? `${BACKEND_URL}/docs` : "/api/v1/docs";

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
    throw new Error(parsed?.message || parsed?.detail || `Request failed (${res.status})`);
  }
  return parsed as T;
}

export const api = {
  getHealth: () => fetchJson<HealthResponse>("/health"),
  getSystemStatus: () => fetchJson<SystemStatus>("/system/status"),
  getSystemModelsStatus: () => fetchJson<SystemModelsStatus>("/system/models-status"),

  // CTGAN Synthesizer
  listCtganModels: () =>
    fetchJson<{ total_models: number; models: CTGANModelSummary[] }>("/ctgan/models"),
  getCtganModelDetail: (modelId: string) =>
    fetchJson<CTGANModelDetail>(`/ctgan/models/${encodeURIComponent(modelId)}`),
  listDeviceProfiles: () => fetchJson<IoTDeviceProfile[]>("/ctgan/device-profiles"),
  listV2Devices: () => fetchJson<V2DeviceCatalogResponse>("/ctgan/v2-devices"),
  listAttackProfiles: () => fetchJson<AttackProfileSummary[]>("/ctgan/attack-profiles"),
  generateCtganTraffic: (payload: CTGANGenerateRequest) =>
    fetchJson<CTGANGenerateResponse>("/ctgan/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  trainCtganModel: (payload: CTGANTrainRequest) =>
    fetchJson<CTGANTrainResponse>("/ctgan/train", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deleteCtganModel: (modelId: string) =>
    fetchJson<{ status: string; model_id: string }>(
      `/ctgan/models/${encodeURIComponent(modelId)}`,
      { method: "DELETE" }
    ),

  // Generated Dataset Vault
  listDatasets: () =>
    fetchJson<{ total_datasets: number; datasets: DatasetItem[] }>("/datasets"),
  getDatasetDetail: (datasetId: string, previewLimit = 80) =>
    fetchJson<DatasetDetail>(
      `/datasets/${encodeURIComponent(datasetId)}?preview_limit=${previewLimit}`
    ),
  deleteDataset: (datasetId: string) =>
    fetchJson<{ status: string; dataset_id: string }>(
      `/datasets/${encodeURIComponent(datasetId)}`,
      { method: "DELETE" }
    ),
  datasetDownloadUrl: (datasetId: string, format: "csv" | "parquet" = "csv") =>
    `${API_BASE}/datasets/${encodeURIComponent(datasetId)}/download?format=${format}`,

  // Quality Audit
  getEvaluationStatus: () => fetchJson<EvaluationStatusResponse>("/evaluation/status"),
  listEvaluationResults: () =>
    fetchJson<{ total_results: number; results: EvaluationSummaryItem[] }>("/evaluation/results"),
  getEvaluationDetail: (evaluationId: string) =>
    fetchJson<EvaluationDetailResponse>(
      `/evaluation/results/${encodeURIComponent(evaluationId)}`
    ),
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

  // Anomaly Detection Lab
  listAnomalyModels: () =>
    fetchJson<{
      total_models: number;
      loaded_models_count: number;
      models: AnomalyModelSummary[];
    }>("/anomaly/models"),
  getAnomalyModelDetail: (modelId: string) =>
    fetchJson<AnomalyModelDetail>(`/anomaly/models/${encodeURIComponent(modelId)}`),
  listAnomalyExperiments: () =>
    fetchJson<{
      experiments: string[];
      available_classifiers: string[];
      augmentation_levels: string[];
      total_models: number;
      quality_warnings: string[];
    }>("/anomaly/experiments"),
  compareAnomalyExperiments: () =>
    fetchJson<{
      total_comparisons: number;
      comparisons: ExperimentComparisonRecord[];
      trtr_vs_tstr_summary?: Record<string, any>[];
      quality_warnings: string[];
    }>("/anomaly/experiments/compare"),
  trainAnomalyModel: (payload: {
    classifier_name: string;
    experiment_type: string;
    synthetic_dataset_id: string | null;
    augmentation_fraction: number;
    balance_minority_classes: boolean;
    model_tag: string | null;
    random_seed: number;
  }) =>
    fetchJson<AnomalyTrainResponse>("/anomaly/train", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deleteCustomModel: (modelId: string) =>
    fetchJson<{ status: string; model_id: string }>(
      `/anomaly/models/${encodeURIComponent(modelId)}`,
      { method: "DELETE" }
    ),
  predictSingle: (payload: { model_id: string; features: Record<string, number> }) =>
    fetchJson<PredictSingleResponse>("/anomaly/predict", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  predictBatch: (payload: { model_id: string; records: Record<string, number>[] }) =>
    fetchJson<PredictBatchResponse>("/anomaly/predict/batch", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
