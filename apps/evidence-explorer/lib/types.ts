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
}

export interface ProvinceAggregate {
  province: string;
  value: number | null;
  fireCount?: number | null;
  observed: number;
  expected: number;
  isUnknown: boolean;
}
