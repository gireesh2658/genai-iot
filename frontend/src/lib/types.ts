export interface CTGANModelSummary {
  model_id: string;
  model_type: string;
  role?: string;
  is_primary?: boolean;
  is_fitted: boolean;
  is_loaded: boolean;
  epochs: number;
  training_rows: number | null;
  feature_columns_count?: number | null;
  discrete_columns_count?: number | null;
  cond_vector_dim?: number | null;
  trained_device?: string | null;
  serving_device?: string;
}

export interface IoTDeviceProfileSummary {
  profile_name: string;
  device_category: string;
  default_protocols: string[];
  behavior_type: string;
  description: string;
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

export interface AttackProfileSummary {
  attack_id: string;
  label_raw: string;
  label_category: string;
  protocol_name: string;
  protocol_type: number;
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

export interface EvaluationRunResponse {
  evaluation_id: string;
  status: string;
  timestamp: string;
  reference_dataset_id: string;
  synthetic_dataset_id: string;
  summary_metrics: {
    average_ks_statistic_vs_train?: number | null;
    average_wasserstein_distance_vs_train?: number | null;
    average_normalized_wasserstein_distance_vs_train?: number | null;
    average_jensen_shannon_distance_vs_train?: number | null;
    pearson_mace?: number | null;
    spearman_mace?: number | null;
    exact_duplicate_rows_in_train?: number | null;
    min_nearest_neighbor_distance?: number | null;
    median_nearest_neighbor_distance?: number | null;
  };
  reports: {
    data_validity?: Record<string, any>;
    [key: string]: any;
  };
  isolated_reports_dir: string;
}
