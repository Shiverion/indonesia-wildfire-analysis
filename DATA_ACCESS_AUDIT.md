# Data Access and Licensing Audit

**Audit date:** 20 August 2026  
**Scope:** Kalimantan wildfire research pipeline

No: the entire primary study is not yet anonymous open access. The sources below separate no-account public data, free-account data, and genuinely unresolved/blocked assets. A source being no-cost does not by itself establish redistribution rights or make it valid for the primary estimand.

| Input | Access state | Current pipeline state | Permitted role / hard limit |
|---|---|---|---|
| [NOAA CPC RONI](https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt) | Anonymous public download | Ready and hashed | ENSO context/panel sensitivity. RONI main effect is conditioned out of exact-overpass risk sets. |
| [GWIS aggregate archive](https://gwis.jrc.ec.europa.eu/apps/country.profile/downloads) | Anonymous public download | Ready and hashed | Aggregate burned-area/count context through 2024 only; not events, onsets, or 2025 coverage. |
| [SiPongi portal](https://sipongi.gakkum.kehutanan.go.id/sebaran-titik-panas) | Public anonymous portal; explicit reusable licence not established | Validated 2015-2023 context only | Positive hotspot records only. Attribute SiPongi/Kemenhut; confirm terms before redistributing record-level data. |
| [CHIRPS v3 FINAL COGs](https://data.chc.ucsb.edu/products/CHIRPS/v3.0/README-CHIRPSv3.0.txt) | Anonymous public download | Not yet ingested | Daily antecedent rainfall/drought at native 0.05-degree support, not 1 km wind. |
| [ERA5-Land](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-timeseries?tab=overview) | Free CDS account and licence acceptance | Blocked pending account/request | Wind components, VPD, soil water, weather support at native grid, not fabricated 1 km weather. |
| [MapBiomas Indonesia C4.1](https://landy.mapbiomas.id/en/faq) | Public CC-BY-SA terms, free registered GEE access required | Blocked pending frozen export/crosswalk | 2014 baseline forest and lagged transformation. Same-year annual cover is not a prefire covariate. |
| [MOD13Q1.061 EVI](https://doi.org/10.5067/MODIS/MOD13Q1.061) | NASA data; Earthdata workflow | Blocked pending files | Primary QA-valid prefire vegetation/fuel proxy. It is intentionally in the Phase 1 gate. |
| HLSL30/HLSS30 NDMI | NASA data; Earthdata workflow | Not yet ingested | 30 m prefire live-fuel moisture sensitivity, never a post-fire predictor. |
| [GFW Global Peatlands](https://services2.arcgis.com/g8WusZB13b9OegfU/arcgis/rest/services/Global_Peatlands/FeatureServer/0) | Anonymous public service | Candidate, not frozen locally | Fixed peat/non-peat stratum or sensitivity; not field-grade boundary/depth truth. |
| [Dadap et al. canal map](https://purl.stanford.edu/yj761xk5815) | Anonymous CC-BY 3.0 download | Candidate, not frozen locally | Static map from 2017 imagery; post-2017 mediator/sensitivity only, not a 2014 baseline or construction series. |
| [Geofabrik historical OSM snapshots](https://download.geofabrik.de/asia/indonesia.html) | Anonymous ODbL download | Candidate, not frozen locally | Historical *mapped* network sensitivity, never evidence of opening/construction date. |
| [WSF Evolution](https://web.geoservice.dlr.de/web/datasets/wsf) | Anonymous CC-BY data service | Candidate, not frozen locally | Settlement-detection timing through 2015; not population or transport access. |
| NASA VNP14IMG + VNP03IMG swaths | Free Earthdata Login required | Blocked pending account/files | Required primary S-NPP event and processed-observation frame. No point source replaces it. |
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
