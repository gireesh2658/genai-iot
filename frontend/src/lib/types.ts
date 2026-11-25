export interface HealthResponse {
  status: string;
  app_name?: string;
  version?: string;
  api_status?: string;
  timestamp?: string;
  environment?: string;
}

export interface SystemStatus {
  status: string;
  app_name: string;
  app_version: string;
  python_version: string;
  dependencies: Record<string, string>;
  storage_status: Record<string, boolean>;
}

export interface SystemModelsStatus {
  ctgan_models_count: number;
  ctgan_loaded_count: number;
  ctgan_models: Array<{
    model_id: string;
    is_loaded: boolean;
    on_disk: boolean;
    file_size_bytes: number | null;
  }>;
  anomaly_models_count: number;
  anomaly_loaded_count: number;
  anomaly_experiment_types: string[];
  anomaly_classifiers: string[];
  anomaly_models: Array<{
    model_id: string;
    classifier_name: string;
    experiment_type: string;
    augmentation_percentage: number | null;
    is_loaded: boolean;
    on_disk: boolean;
  }>;
}

export interface CTGANModelSummary {
  model_id: string;
  model_type: string;
  role?: string;
  is_primary?: boolean;
  is_fitted: boolean;
  is_loaded: boolean;
  is_custom: boolean;
  epochs: number;
  batch_size: number;
  training_rows: number | null;
  feature_columns_count?: number | null;
  discrete_columns_count?: number | null;
  cond_vector_dim?: number | null;
  training_duration_sec: number | null;
  artifact_availability: Record<string, boolean>;
  device: string;
  trained_device?: string | null;
  serving_device?: string;
  created_at: string | null;
}

export interface V2DeviceItem {
  device_id: string;
  device_name: string;
  device_category: string;
  testbed_role: string;
  train_row_count: number;
  supported_label_categories: string[];
}

export interface V2DeviceCatalogResponse {
  total_devices: number;
  device_categories: string[];
  traffic_categories: string[];
  devices: V2DeviceItem[];
}

export interface CTGANModelDetail {
  model_id: string;
  model_type: string;
  is_fitted: boolean;
  is_loaded: boolean;
  feature_columns_count: number;
  feature_columns: string[];
  discrete_columns_count: number;
  discrete_columns: string[];
  config: Record<string, any>;
  training_metadata: Record<string, any>;
  artifact_availability: Record<string, boolean>;
}

export interface IoTDeviceProfile {
  profile_name: string;
  device_category: string;
  default_protocols: string[];
  packet_size_min: number;
  packet_size_max: number;
  communication_interval: number;
  traffic_rate_min: number;
  traffic_rate_max: number;
  behavior_type: string;
  description: string;
}

export interface AttackProfileSummary {
  attack_id: string;
  label_raw: string;
  label_category: string;
  protocol_name: string;
  protocol_type: number;
  packet_size_min: number;
  packet_size_max: number;
  rate_min: number;
  rate_max: number;
}

export interface CTGANGenerateRequest {
  model_id: string;
  num_records: number;
  conditions?: Record<string, any> | null;
  category_counts?: Record<string, number> | null;
  device_profiles?: string[] | null;
  apply_device_calibration: boolean;
  apply_domain_correction: boolean;
  max_records_to_return: number;
  export_dataset: boolean;
  export_format: "parquet" | "csv" | "both";
  export_filename_prefix?: string;
}

export interface CTGANGenerateResponse {
  status: string;
  model_id: string;
  total_generated: number;
  returned_records_count: number;
  generation_time_sec: number;
  features_count: number;
  features: string[];
  conditions_applied: Record<string, any> | null;
  domain_correction_applied: boolean;
  domain_correction_summary: Record<string, number> | null;
  device_calibration_applied: boolean;
  device_distribution: Record<string, number>;
  category_distribution: Record<string, number>;
  records: Record<string, any>[];
  dataset_id: string | null;
  exported_files: Record<string, string> | null;
}

export interface CTGANTrainRequest {
  model_id: string;
  epochs: number;
  sample_size: number;
  batch_size: number;
  random_seed: number;
}

export interface CTGANTrainResponse {
  status: string;
  model_id: string;
  epochs: number;
  batch_size: number;
  training_rows: number;
  elapsed_seconds: number;
  initial_generator_loss: number | null;
  final_generator_loss: number | null;
  initial_discriminator_loss: number | null;
  final_discriminator_loss: number | null;
}

export interface DatasetItem {
  dataset_id: string;
  filename: string;
  format: string;
  available_formats: string[];
  size_bytes: number;
  created_at: string;
  has_metadata: boolean;
  is_protected: boolean;
  num_records: number | null;
  num_columns: number | null;
}

export interface DatasetDetail {
  dataset_id: string;
  primary_filename: string;
  available_formats: string[];
  num_records: number | null;
  num_columns: number | null;
  columns: string[];
  files: Record<string, { filename: string; size_bytes: number }>;
  metadata: Record<string, any> | null;
  preview_records: Record<string, any>[];
}

export interface EvaluationStatusResponse {
  engine_available: boolean;
  engine_class: string;
  available_reference_datasets: string[];
  available_synthetic_datasets: string[];
  capabilities: string[];
}

export interface EvaluationSummaryItem {
  evaluation_id: string;
  title: string;
  source: string;
  created_at: string | null;
  available_reports: string[];
}

export interface EvaluationDetailResponse {
  evaluation_id: string;
  source: string;
  data_validity: Record<string, any> | null;
  statistical_similarity: Record<string, any> | null;
  feature_correlation: Record<string, any> | null;
  class_distribution: Record<string, any> | null;
  diversity_and_memorization: Record<string, any> | null;
  three_candidate_comparison: Record<string, any> | null;
}

export interface EvaluationRunResponse {
  evaluation_id: string;
  status: string;
  timestamp: string;
  reference_dataset_id: string;
  synthetic_dataset_id: string;
  summary_metrics: Record<string, any>;
  reports: Record<string, any>;
  isolated_reports_dir: string;
}

export interface AnomalyModelSummary {
  model_id: string;
  classifier_name: string;
  experiment_type: string;
  augmentation_percentage: number | null;
  is_loaded: boolean;
  is_custom: boolean;
  synthetic_source: string | null;
  train_records: number | null;
  supported_capabilities: string[];
  macro_f1: number | null;
  balanced_accuracy: number | null;
}

export interface AnomalyModelDetail {
  model_id: string;
  classifier_name: string;
  experiment_type: string;
  augmentation_percentage: number | null;
  is_loaded: boolean;
  features_count: number;
  target_column: string;
  classes: string[];
  pipeline_steps: string[];
  train_records: number | null;
  val_records: number | null;
  model_file_sha256: string | null;
  overall_metrics: Record<string, any> | null;
  per_class_metrics: Record<
    string,
    { precision: number; recall: number; f1_score: number; support: number }
  > | null;
  confusion_matrix: Record<string, Record<string, number>> | null;
  hyperparameters: Record<string, any> | null;
  provenance_info: Record<string, any> | null;
  is_custom: boolean;
}

export interface AnomalyTrainResponse {
  status: string;
  model_id: string;
  classifier_name: string;
  experiment_type: string;
  synthetic_dataset_id: string | null;
  train_records: number;
  synthetic_records_used: number;
  val_records: number;
  fit_duration_seconds: number;
  overall_metrics: Record<string, any>;
  per_class_metrics: Record<string, any>;
  trtr_baseline_macro_f1: number | null;
  macro_f1_delta_vs_trtr: number | null;
  balanced_accuracy_delta_vs_trtr: number | null;
  per_class_f1_deltas_vs_trtr: Record<string, number>;
  confusion_matrix: Record<string, Record<string, number>>;
  quality_warnings: string[];
}

export interface ExperimentComparisonRecord {
  Model: string;
  Experiment: string;
  "Augmentation Level": string;
  "Train Records": number;
  "Synthetic Records": number;
  "Macro F1": number;
  "Balanced Accuracy": number;
  Accuracy: number;
  "Weighted F1": number;
  "Abs Macro F1 Diff": number;
  "Rel Macro F1 Diff (%)": number;
  [key: string]: any;
}

export interface PredictSingleResponse {
  model_id: string;
  predicted_category: string;
  is_attack: number;
  confidence: number;
  probabilities: Record<string, number>;
  latency_ms: number;
}

export interface PredictBatchResponse {
  model_id: string;
  total_records: number;
  attack_count: number;
  benign_count: number;
  predictions: Array<{
    index: number;
    predicted_category: string;
    is_attack: number;
    confidence: number;
    probabilities: Record<string, number>;
  }>;
  latency_ms: number;
}
