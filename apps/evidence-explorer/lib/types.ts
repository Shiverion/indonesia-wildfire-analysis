export type EvidenceMode = "sipongi" | "gwis";

export interface RoniAnnual {
  year: number;
  mean_aug_nov_c: number;
}

export interface LatestRoni {
  season: string;
  season_year: number;
  end_date: string;
  anomaly_c: number;
  provisional: boolean;
}

export interface GwisAnnual {
  year: number;
  burned_area_ha: number;
  fire_count: number;
  observed_province_month_rows: number;
  expected_province_month_rows: number;
  roni_aug_nov_c: number | null;
}

export interface GwisProvince {
  year: number;
  gid_1: string;
  province: string;
  burned_area_ha: number;
  fire_count: number;
  observed_months: number;
  expected_months: number;
}

export interface SipongiAnnual {
  year: number;
  province: string;
  platform: string;
  record_count: number;
}

export interface SipongiMonthly {
  year: number;
  month: number;
  province: string;
  platform: string;
  record_count: number;
}

export interface SipongiSnapshotCount {
  province: string;
  platform: string;
  record_count: number;
}

export interface SipongiCurrentSnapshot {
  snapshot_id: string;
  status: "validated_partial";
  season: {
    year: number;
    start_date: string;
    end_date: string;
    complete: false;
  };
  through_date: string;
  retrieved_at_utc: string;
  time_basis: string;
  metric: "positive portal records";
  comparison_guardrail: {
    included_in_annual_archive: false;
    eligible_for_year_slider: false;
    eligible_for_annual_chart: false;
    comparable_to_completed_jul_nov_seasons: false;
  };
  validation: {
    expected_province_responses: number;
    validated_province_responses: number;
    raw_inventory_sha256: string;
    provider_configuration_sha256: string;
    province_catalogue_sha256: string;
    raw_records_embedded: false;
    has_observation_denominator: false;
  };
  total_record_count: number;
  province_platform_counts: SipongiSnapshotCount[];
}

export interface PeatFireCountry {
  country_id: string;
  country: string;
  land_area_km2: number;
  peat_share_percent: number;
  peat_area_km2: number;
  nonpeat_area_km2: number;
  peat_detection_count: number;
  nonpeat_detection_count: number;
  peat_detection_rate_per_1000_km2: number | null;
  nonpeat_detection_rate_per_1000_km2: number | null;
  total_detection_rate_per_1000_km2: number;
}

export interface PeatFireThreshold {
  threshold_percent: number;
  definition: string;
  matched_country_count: number;
  crude_rate_ratio: number | null;
  fixed_effect_rate_ratio: number | null;
  fixed_effect_ci95: [number, number] | null;
  fixed_effect_p_two_sided: number | null;
  bonferroni_p_three_thresholds: number | null;
}

export interface PeatFireComparison {
  schema_version: string;
  status: "exploratory_association_not_causal";
  analysis_year: number;
  analysis_retrieved_at_utc?: string;
  peat_release_date: string;
  peat_reference_period: string;
  primary_threshold_percent: number;
  fire_metric: string;
  fire_filter: string;
  matched_country_count: number;
  primary_global_rate_ratio: number | null;
  primary_fixed_effect_model: {
    status: string;
    threshold: number;
    matched_countries: number;
    model: string;
    rate_ratio: number | null;
    ci95: [number, number] | null;
    p_two_sided: number | null;
    p_two_sided_bonferroni_three_thresholds?: number | null;
  };
  threshold_sensitivity: PeatFireThreshold[];
  countries: PeatFireCountry[];
  interpretation_guardrails: string[];
  source_links: { peat?: string; fire?: string; boundaries?: string };
}

export interface LatestGlobalFireCountry {
  country_id: string;
  country: string;
  positive_detection_count: number;
  modis_count: number;
  viirs_noaa20_count: number;
  viirs_noaa21_count: number;
  viirs_snpp_count: number;
  status: "positive_detection_records" | "zero_returned_positive_detection" | string;
}

export interface LatestIndonesiaProvince {
  province_id: string;
  province: string;
  positive_detection_count: number;
  modis_count: number;
  viirs_noaa20_count: number;
  viirs_noaa21_count: number;
  viirs_snpp_count: number;
  status: "positive_detection_records" | "zero_returned_positive_detection" | string;
}

export interface LatestGlobalFireSnapshot {
  schema_version: string;
  status: "validated_closed_day_aggregate";
  snapshot_date: string;
  retrieved_at_utc: string;
  aggregation_completed_at_utc?: string;
  date_basis: string;
  metric: string;
  source_url: string;
  raw_record_count: number;
  matched_point_count: number;
  unmatched_point_count: number;
  positive_country_count: number;
  country_count: number;
  sensor_record_counts: Record<string, number>;
  country_geometry: { path?: string; sha256?: string; feature_count?: number };
  indonesia_province_geometry?: { path?: string; sha256?: string; feature_count?: number; boundary_year_represented?: number };
  indonesia_matched_point_count?: number;
  derived_sha256?: string;
  raw_records_embedded: false;
  has_observation_denominator: false;
  interpretation: string;
  countries: LatestGlobalFireCountry[];
  indonesia_provinces: LatestIndonesiaProvince[];
}

export interface ConditionPhaseAudit {
  schema_version: "condition-phase-audit/v1";
  status: string;
  condition_phase_ready: false;
  assets: Record<string, string>;
  temporal_support?: {
    status: string;
    phase_1_unlock: boolean;
    assets: Record<string, string>;
  };
  required_interactions: string[];
}

export interface Phase1BReadiness {
  schema_version: "phase1b-readiness/v1" | "phase1b-readiness/v2";
  status: string;
  phase_1b_ready: boolean;
  phase_2_unlock: boolean;
  selected_track?: string;
  human_access_confirmatory_track_ready?: boolean;
  progress?: {
    completed_days: number;
    registered_days: number;
    percent: number;
  };
  workstreams: Record<string, {
    status: string;
    gate_ready: boolean;
    required_for_environmental_track?: boolean;
    next_action: string;
  }>;
}

export interface Phase2EnvironmentalSummary {
  schema_version: "environmental-phase2-results/v1";
  created_at_utc: string;
  status: "completed_environmental_association";
  scope: string;
  human_access_confirmatory_track_status: string;
  data_summary: {
    row_count: number;
    case_count: number;
    control_count: number;
    matched_set_count: number;
    history_fallback_row_count: number;
  };
  pre_fit_excluded_matched_set_count: number;
  primary: {
    label: string;
    odds_ratio: number;
    ci95: [number, number];
    p_two_sided: number;
    classification: string;
    interpretation: string;
    mixed_peat_matched_set_count: number;
  };
  sensitivities: Array<{
    label: string;
    odds_ratio: number;
    ci95: [number, number];
    p_two_sided: number;
  }>;
  secondary_conditions: Array<{
    label: string;
    odds_ratio: number;
    ci95: [number, number];
    p_holm: number;
  }>;
  locked_test_prediction: {
    conditional_log_loss: number;
    uniform_log_loss: number;
    top1_recall: number;
    mean_reciprocal_rank: number;
  };
  interpretation_guardrails: string[];
}

export interface AlphaEarthPredictionSummary {
  schema_version: "ppe-alphaearth-dashboard/v1";
  status: "locked_test_complete";
  title: string;
  source: {
    name: string;
    collection: string;
    documentation: string;
    license: string;
    attribution: string;
  };
  design: {
    embedding_year_rule: string;
    embedding_years: string;
    development_years: string;
    rehearsal_years: string;
    locked_test_years: string;
    locked_test_matched_sets: number;
    feature_gate_passed: boolean;
    same_year_embedding_rejected: boolean;
    postfire_features_rejected: boolean;
  };
  models: Array<{
    label: string;
    conditional_log_loss: number;
    top1_recall: number;
    mean_reciprocal_rank: number;
  }>;
  combined_improvement: {
    conditional_log_loss: number;
    ci95: [number, number];
    bootstrap_replicates: number;
  };
  interpretation: string;
  guardrail: string;
}

export interface Phase3StatusSummary {
  schema_version: "phase3-dashboard-status/v1";
  created_at_utc: string;
  status: string;
  phase3_ready: boolean;
  phase3_model_run: boolean;
  scope: {
    geography: "Kalimantan";
    country_context: "Indonesia";
    indonesia_map_role: "descriptive_context_only";
    inference_generalization: string;
  };
  matched_set_count: number;
  unique_cell_count: number;
  private_cell_count: number;
  mapbiomas_available_years: [number, number];
  local_full_raster_years: number[];
  eligible_event_years_primary: number[];
  blockers: string[];
  primary_result: null | {
    status: string;
    flow?: { included_matched_set_count?: number };
    model?: {
      matched_set_count: number;
      unique_cell_count: number;
      outcome_variation_matched_set_count: number;
      unadjusted: {
        fire_positive_risk: number;
        fire_negative_risk: number;
        risk_difference: number;
        risk_ratio: number | null;
      };
      primary_term: {
        estimate: number;
        ci95: [number, number];
        p_two_sided: number;
      };
    };
  };
  sensitivity_results: Array<{
    label: string;
    status: string;
    matched_set_count?: number;
    estimate?: number;
    ci95?: [number, number];
    p_two_sided?: number;
    p_holm?: number | null;
    variation_matched_set_count?: number | null;
  }>;
  destination_results: Array<{
    label: string;
    status: string;
    matched_set_count?: number;
    estimate?: number;
    ci95?: [number, number];
    p_two_sided?: number;
    p_holm?: number | null;
    variation_matched_set_count?: number | null;
  }>;
  publication_robustness?: {
    status: "complete";
    attrition: {
      candidate_matched_set_count: number;
      included_matched_set_count: number;
      excluded_share: number;
      maximum_absolute_standardized_mean_difference: number;
    };
    negative_control: {
      matched_set_count: number;
      estimate: number;
      ci95: [number, number];
      p_two_sided: number;
    };
    common_support_post_minus_pre: {
      matched_set_count: number;
      estimate: number;
      ci95: [number, number];
      p_two_sided: number;
    };
    interpretation: string;
  };
  earth_engine_export?: {
    status: string;
    updated_at_utc?: string | null;
    algorithm_revision?: string | null;
    chunk_count: number;
    state_counts: Record<string, number>;
  };
  plain_language: string;
  claim_boundary: string[];
}

export interface ProvenanceItem {
  id: string;
  label: string;
  source_url: string;
  retrieved_at_utc: string;
  raw_sha256: string;
  derived_path: string;
  derived_sha256: string;
  record_count: number | string;
  distribution: string;
  access_note: string;
  analysis_limit: string;
}

export interface ExplorerData {
  schema_version: string;
  generated_at_utc: string;
  title: string;
  display_status: {
    label: string;
    primary_association: string;
    phase_1_ready: boolean;
    blocked_assets: string[];
  };
  scope: {
    fire_season_months: number[];
    roni_context_months: number[];
    gwis_years: [number, number];
    sipongi_years: [number, number];
  };
  limitations: string[];
  provenance: ProvenanceItem[];
  ledger: { valid: boolean; entry_count: number; latest_entry_sha256?: string };
  quality: {
    sipongi: {
      record_count: number;
      quarantined_request_count: number;
      excluded_years?: number[];
      raw_records_embedded: boolean;
    };
  };
  roni_annual: RoniAnnual[];
  latest_roni: LatestRoni;
  gwis_annual: GwisAnnual[];
  gwis_province: GwisProvince[];
  sipongi_annual: SipongiAnnual[];
  sipongi_monthly: SipongiMonthly[];
  sipongi_platforms: string[];
  sipongi_current_snapshot: SipongiCurrentSnapshot | null;
  peat_fire_comparison?: PeatFireComparison | null;
  latest_global_fire?: LatestGlobalFireSnapshot | null;
  condition_phase_audit?: ConditionPhaseAudit | null;
  phase1b_readiness?: Phase1BReadiness | null;
}

export interface ProvinceAggregate {
  province: string;
  value: number | null;
  fireCount?: number | null;
  observed: number;
  expected: number;
  isUnknown: boolean;
}
