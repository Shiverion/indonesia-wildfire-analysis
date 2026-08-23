# Evidence-Bounded Preliminary Insight -- Kalimantan Fire Research

## Bottom line

**Central human-accessibility / transformation conclusion: NI -- Not identifiable.** The primary matched-overpass analysis has not been substituted with a hotspot-count regression. Consequently, this project currently has no estimate of an accessibility effect, no estimate of a transformation effect, and no causal attribution to people, sectors, companies, or land uses.

## What the open evidence does show

The independent GWIS aggregate archive reports its largest July-November Kalimantan burned area in **2015** (423,577 ha). The top three reported seasons are **2015: 423,577 ha; 2019: 381,962 ha; 2023: 237,229 ha**. The NOAA CPC RONI mean for August-November was **1.66 degrees C** in 2015; that year is the strongest RONI condition in the shared GWIS span.

A deliberately countervailing observation is **2019**: RONI was near neutral (**0.01 degrees C**) while GWIS still reported **381,962 ha** in July-November. This supports a limited inference: an oceanic ENSO index alone is not a sufficient description of Kalimantan fire-season burden. It does not identify which local mechanisms account for the difference, and it is not evidence that accessibility caused fire.

The validated SiPongi descriptive archive spans 2015-2025 excluding 2024. It contains **388,435** portal records; its all-platform maximum is **2023** (188,180 records), while the matched NASA-MODIS subtotal is only **19,991**. That disparity is direct evidence of changing sensor composition in the portal series, so all-platform count changes must not be called changes in wildfire occurrence.

## What cannot yet be claimed

- No exact S-NPP VIIRS observation-opportunity denominator or 72-hour prior-negative frame exists locally.
- No frozen MapBiomas Indonesia 4.1 baseline/lagged transformation export or QA-valid prefire EVI exists locally; vegetation and fuel cannot be omitted from the primary model.
- No validated dated road-opening / settlement accessibility series exists; dated OSM mapping is only a sensitivity, not construction timing.
- No ERA5-Land request is frozen, so wind, VPD, soil water, and other local-weather adjustment are unavailable.
- SiPongi is a positive-record portal source and GWIS is an aggregate burned-area archive. Neither can replace the specified primary outcome.

## Data-quality decision

The SiPongi 2024 all-platform requests exposed a provider integrity failure: a Kalimantan Barat request repeatedly returned Alor records. Those responses were quarantined and excluded. The archive therefore leaves 2024 absent rather than using an incorrect response, treating it as zero, or silently filling it from another provider.

## Evidence sources and next gate

- [NOAA CPC RONI](https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt): archived locally with retrieval hash; retrospective climate context only.
- [GWIS country-profile downloads](https://gwis.jrc.ec.europa.eu/apps/country.profile/downloads): aggregate monthly burned-area context through 2024, not event geometries or 2025 data.
- [SiPongi hotspot portal](https://sipongi.gakkum.kehutanan.go.id/sebaran-titik-panas): portal-record context with preserved sensor labels and provider-quality receipts.

The next legitimate step is to resolve all Phase 1 assets: viirs_snpp_active_fire_and_geolocation, era5_land, chirps_v3, mapbiomas_indonesia_collection_4_1, mod13q1_061, historical_access_assets, peat_and_drainage_assets. Only then may the pipeline construct risk sets, lock the 2024-2025 test inputs, and estimate the two central adjusted associations.

Shared descriptive years used for cross-source context: 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023.
