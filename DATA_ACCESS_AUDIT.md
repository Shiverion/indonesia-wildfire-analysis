# Data Access and Licensing Audit

**Audit date:** 20 August 2026  
**Scope:** Kalimantan wildfire research pipeline

No: the entire primary study is not yet anonymous open access. The sources below separate no-account public data, free-account data, and genuinely unresolved/blocked assets. A source being no-cost does not by itself establish redistribution rights or make it valid for the primary estimand.

| Input | Access state | Current pipeline state | Permitted role / hard limit |
|---|---|---|---|
| [NOAA CPC RONI](https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt) | Anonymous public download | Ready and hashed | ENSO context/panel sensitivity. RONI main effect is conditioned out of exact-overpass risk sets. |
| [GWIS aggregate archive](https://gwis.jrc.ec.europa.eu/apps/country.profile/downloads) | Anonymous public download | Ready and hashed | Aggregate burned-area/count context through 2024 only; not events, onsets, or 2025 coverage. |
| [SiPongi portal](https://sipongi.gakkum.kehutanan.go.id/sebaran-titik-panas) | Public anonymous portal; explicit reusable licence not established | Validated 2015-2023 context only | Positive hotspot records only. Attribute SiPongi/Kemenhut; confirm terms before redistributing record-level data. |
| [CHIRPS daily](https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY) | Anonymous public source; Earth Engine account used for computation | Registered 1/7/30/90-day pre-event sums are being linked for 2015-2025 without downloading the full raster archive | Daily antecedent rainfall at native support, sampled to analysis cells without claiming 1-km rainfall measurement. The partial local COG archive is a reproducibility/sensitivity cache. |
| [ERA5-Land](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-timeseries?tab=overview) | Free CDS account and licence acceptance | 2015-2025 monthly window complete and content/provenance validated | Wind components, VPD, soil water, weather support at native grid, not fabricated 1 km weather. Event-cutoff lag extraction remains pending. |
| [MapBiomas Indonesia C4.1](https://landy.mapbiomas.id/en/faq) | Public CC-BY-SA terms, free registered GEE access required | Phase 3 compact transition extraction and registered model complete; 18,664 unique cells × 307 coordinate-free fields validated | Annual maps cover 1990-2024. The 2014 raster is baseline only. One-year outcomes cover fire years through 2023; 2024-2025 events lack complete follow-up in this collection. |
| [MOD13Q1.061 EVI](https://doi.org/10.5067/MODIS/MOD13Q1.061) | NASA data; Earthdata workflow | 144 payloads present for 2014-2015; SDS QA extraction validated for a clipped 2015 tile/composite summary, but event cutoff linkage and 2016-2025 coverage remain absent | Primary QA-valid prefire vegetation/fuel proxy. It remains a Phase 1B gate input. |
| HLSL30/HLSS30 NDMI | NASA data; Earthdata workflow | Not yet ingested | 30 m prefire live-fuel moisture sensitivity, never a post-fire predictor. |
| [Global peatland extent ensemble](https://zenodo.org/records/19731872) | Anonymous CC-BY-4.0 | Frozen local 1-km 2000-2020 reference-period raster with SHA-256 receipt | Fixed 25/50/75% peat-extent strata only; not field-grade boundary/depth truth, drainage state, or 2026 peat condition. |
| [Dadap et al. canal map](https://purl.stanford.edu/yj761xk5815) | Anonymous CC-BY 3.0 download | Candidate, not frozen locally | Static map from 2017 imagery; post-2017 mediator/sensitivity only, not a 2014 baseline or construction series. |
| [Geofabrik historical OSM snapshots](https://download.geofabrik.de/asia/indonesia.html) | Anonymous ODbL download | Candidate, not frozen locally | Historical *mapped* network sensitivity, never evidence of opening/construction date. |
| [WSF Evolution](https://web.geoservice.dlr.de/web/datasets/wsf) | Anonymous CC-BY data service | Candidate, not frozen locally | Settlement-detection timing through 2015; not population or transport access. |
| [NASA VNP14A1.002 daily FireMask](https://developers.google.com/earth-engine/datasets/catalog/NASA_VIIRS_002_VNP14A1) | NASA open data; Earth Engine registered computation | All 1,683 registered July-November calendar days for 2015-2025 have receipts; missing event days are explicitly marked no-observation | Environmental-condition onset/valid-land opportunity frame. Daily support is not an exact overpass time and cannot be used to claim ignition time. |
| [NASA MOD14A1.061 and MYD14A1.061 daily FireMask](https://developers.google.com/earth-engine/datasets/tags/fire) | NASA open data; Earth Engine registered computation | Available for every confirmed VNP14A1 lookback-gap date | History-only fallback amendment: preserves prior-fire and processed-land checks when VNP14A1 history is absent. It cannot create the primary event-day outcome. |
| NASA VNP14IMG + VNP03IMG swaths | Free Earthdata Login required | 60 paired 2015 swaths screened | Exact-overpass measurement sensitivity only in the environmental track; still required if the original exact-overpass human-access track is revived. |
| Indonesian official Kalimantan peat map | Token/terms gate | Blocked | More authoritative layer; do not bypass the provider access control. |
| Verified road-opening series | No validated open source identified | Blocked by evidence | Required before any road-opening causal module. |

## Vegetation is in the protocol

Vegetation appears in the executable design as:

- **Baseline forest / transformation:** MapBiomas Indonesia C4.1, lagged before the fire year.
- **Prefire greenness:** MOD13Q1.061 EVI with a QA-approved 16-day composite ending before the qualifying prior-negative observation.
- **Live-fuel moisture sensitivity:** HLS NDMI over prior clear observations.
- **Detectability audit:** MOD44B canopy/uncertainty strata, not automatically an adjustment variable.

The modeling role changes with the estimand: dynamic EVI/NDMI is included in predictive or mediator-adjusted models, but excluded from the total-accessibility and current-transformation association models because it can lie on the pathway from access or transformation to fire.

## Practical implication

The open stack can produce climate and descriptive fire context now. It cannot legitimately produce the primary human-accessibility association until the free-account and dated-exposure assets are obtained, pinned, checked, and passed through the Phase 1 validator.

## Zero-budget decision (26 August 2026)

The environmental module uses Earth Engine as computation, not cloud storage: it requests only daily case/control candidate rows and pre-event CHIRPS/MOD13Q1 values, then joins the already validated local ERA5-Land, MapBiomas, and peat inputs. This avoids purchasing object storage and avoids downloading complete VIIRS geolocation, CHIRPS, and MOD13Q1 archives. The derived local footprint observed in smoke tests is tens of kilobytes per processed day rather than tens of gigabytes of source imagery. A final receipt must still cover every registered day; API availability is not treated as evidence of completeness.

Phase 3 follows the same zero-budget rule. The registered `susenas-project` passed an authenticated Earth Engine probe on 28 August 2026, the official MapBiomas asset exposed all 35 annual bands for 1990-2024, and the former project-permission gate was cleared. `analysis/export_phase3_earthengine.py` sent only the 18,664 locked 1-km polygons transiently, reduced 24 pre/post annual pairs to transition histograms in 38 restart-safe chunks, and expanded them into 307 registered coordinate-free fractions. The final table passed row, column, uniqueness, missingness, and SHA-256 checks; all 38 temporary private Earth Engine assets were deleted after local download. Coordinates remain Git-ignored and are never bundled into the dashboard. No credential value was recorded and no paid object storage or national raster-stack download was used.
