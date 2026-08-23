# Preliminary Aggregate Burned-Area Insight -- Kalimantan

## Scope and non-substitution rule

This is a descriptive aggregation of GWIS/GLOBFIRE monthly admin-1 burned-area rows for the historic four-province Kalimantan coding. It is not the primary 1 km S-NPP first-observed-onset outcome; it has no observation-opportunity denominator, no forest-only cohort, no dated accessibility exposure, and no 2025 data. It must not be used to decide the central accessibility or transformation hypothesis.

## Observed climate-context pattern

For the 10 shared fire seasons from 2015 through 2024, the largest reported July-November burned area occurred in **2015** at **423,577 ha**. That was **33.1x** the median reported area across those seasons. The unadjusted Pearson correlation between mean August-November RONI and log(1 + reported July-November burned area) was **0.88** (n = 10). This is a descriptive climate-context association, not a causal estimate and not a test of the human-accessibility hypothesis.

## Fire-season table

| Year | Reported July-Nov burned area (ha) | Reported fire count | Province-month rows present / 20 | Mean Aug-Nov RONI (degrees C) |
|---:|---:|---:|---:|---:|
| 2015 | 423,577 | 2,449 | 19 / 20 | 1.66 |
| 2016 | 9,090 | 68 | 8 / 20 | -0.84 |
| 2017 | 10,520 | 64 | 12 / 20 | -0.53 |
| 2018 | 113,914 | 517 | 17 / 20 | 0.30 |
| 2019 | 381,962 | 1,910 | 20 / 20 | 0.01 |
| 2020 | 1,322 | 15 | 4 / 20 | -1.03 |
| 2021 | 2,156 | 18 | 9 / 20 | -0.85 |
| 2022 | 1,430 | 12 | 4 / 20 | -0.99 |
| 2023 | 237,229 | 1,048 | 19 / 20 | 0.92 |
| 2024 | 15,106 | 76 | 10 / 20 | -0.62 |

## Interpretation and required caution

The open data provide a useful plausibility check: the study period contains both strong El Nino and La Nina conditions and substantial variation in aggregate reported burning. The association is vulnerable to unmeasured local weather, vegetation, peat, land conversion, boundary changes, reporting structure, and time trends. Missing province-month rows are displayed rather than automatically treated as observed zero fire. The historic GADM coding has four Kalimantan units; its Kalimantan Timur unit includes territory now represented by Kalimantan Utara. Therefore, this report supports data planning and descriptive triangulation only.

## Provenance

GWIS archive: `data/raw/gwis/GLOBFIRE_burned_area_full_dataset_2002_2024.zip`; filtered table: `data/derived/gwis/kalimantan_monthly_burned_area.csv`; retrieval/hash record: `outputs/quality/gwis_fetch.json`. ENSO context uses the separately archived NOAA CPC RONI file.
