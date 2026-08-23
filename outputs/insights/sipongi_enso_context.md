# Preliminary SiPongi Portal-Record Insight -- Kalimantan

## Scope and non-substitution rule

This report counts public SiPongi positive hotspot records in the five current Kalimantan provinces for July-November 2015-2025, using portal-reported dates. A portal record is not an individual wildfire, an ignition, or a valid fire-incidence rate. The endpoint provides no processed-swath denominator, valid non-detections, forest-only cohort, or verified UTC acquisition time. It is not the primary 1 km S-NPP first-observed-onset outcome and cannot test the human-accessibility or transformation hypothesis.

## Observed sensor and climate context

The largest all-platform portal-record count was **188,180** in **2023**. The all-platform count mixes changing satellite coverage.
Over the 10 paired seasons, its unadjusted correlation with log(1 + count) and mean August-November RONI was **0.66**.
The same descriptive correlation using only NASA-MODIS records was **0.89**. Neither correlation adjusts for local weather, vegetation, peat, land use, detection opportunity, reporting structure, or time trend, so neither is a climate effect estimate.

## Fire-season portal-record table

| Year | All platform records | NASA-MODIS | S-NPP | NOAA-20 | Other/unknown | Portal-reported active dates | Mean Aug-Nov RONI (degrees C) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2015 | 53,183 | 53,183 | 0 | 0 | 0 | 151 | 1.66 |
| 2016 | 3,123 | 3,123 | 0 | 0 | 0 | 112 | -0.84 |
| 2017 | 2,995 | 2,995 | 0 | 0 | 0 | 93 | -0.53 |
| 2018 | 14,107 | 14,107 | 0 | 0 | 0 | 133 | 0.30 |
| 2019 | 38,039 | 38,039 | 0 | 0 | 0 | 150 | 0.01 |
| 2020 | 2,696 | 2,696 | 0 | 0 | 0 | 117 | -1.03 |
| 2021 | 1,649 | 1,649 | 0 | 0 | 0 | 56 | -0.85 |
| 2022 | 19,728 | 2,231 | 5,248 | 12,249 | 0 | 150 | -0.99 |
| 2023 | 188,180 | 19,991 | 85,056 | 83,133 | 0 | 153 | 0.92 |
| 2025 | 64,735 | 5,646 | 30,975 | 28,114 | 0 | 152 | -0.68 |

## Interpretation and required caution

Sensor composition is a design finding, not a nuisance detail: a raw all-platform increase after S-NPP and NOAA-20 appear cannot be interpreted as an increase in wildfire occurrence. The NASA-MODIS column is a platform-restricted descriptive sensitivity, not a correction for cloud, scan geometry, overpass timing, or platform sensitivity. SiPongi display times are labelled WIB even in eastern Kalimantan, so these data must not be used for exact-overpass matching, a 72-hour prior-negative rule, or UTC timing. Before public redistribution of record-level data, confirm the portal's licence; this implementation preserves the requested SiPongi/Kemenhut attribution but does not assume an open redistribution licence.

Excluded archive years: 2024. These are a registered provider-quality exclusion, not zero-record years and not a gap that may be imputed.

## Provenance

Raw portal responses: `data/raw/sipongi/`; standardized local table: `data/derived/sipongi/kalimantan_sipongi_jul-nov.csv`; per-request URLs, raw and canonical-content hashes, provider snapshots, and rejected-response receipts: `outputs/quality/sipongi_fetch.json`. ENSO context uses the separately archived NOAA CPC RONI file.
