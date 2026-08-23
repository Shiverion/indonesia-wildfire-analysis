# ENSO Context Insight — Kalimantan Wildfire Protocol

## Scope

This report describes the openly retrieved NOAA CPC RONI climate series. It does **not** test the human-accessibility wildfire hypothesis, because no validated fire-observation, dated-accessibility, or transformation panel is present yet.

## Descriptive result

Across 2015–2025, the highest three-month RONI value was **2.25 °C** (NDJ 2015, ending 2016-01-31); the lowest was **-1.46 °C** (OND 2020, ending 2020-12-31). This confirms that the planned study window spans materially different basin-scale ENSO states.

## July–November fire-season ENSO context

| Year | Mean RONI across Aug–Nov completed seasons (°C) | Minimum | Maximum | Interpretation |
|---:|---:|---:|---:|---|
| 2015 | 1.66 | 1.27 | 2.03 | El Niño threshold |
| 2016 | -0.84 | -0.96 | -0.70 | La Niña threshold |
| 2017 | -0.53 | -0.82 | -0.23 | La Niña threshold |
| 2018 | 0.30 | 0.08 | 0.62 | neutral |
| 2019 | 0.01 | -0.12 | 0.15 | neutral |
| 2020 | -1.03 | -1.37 | -0.76 | La Niña threshold |
| 2021 | -0.85 | -1.08 | -0.60 | La Niña threshold |
| 2022 | -0.99 | -1.10 | -0.86 | La Niña threshold |
| 2023 | 0.92 | 0.54 | 1.30 | El Niño threshold |
| 2024 | -0.62 | -0.76 | -0.49 | La Niña threshold |
| 2025 | -0.68 | -0.93 | -0.41 | La Niña threshold |

## Threshold episodes overlapping the study era

| State | Start | End | Consecutive overlapping seasons | Peak anomaly (°C) |
|---|---|---|---:|---:|
| La Niña threshold | 2011-10-31 | 2012-04-30 | 7 | -1.02 |
| El Niño threshold | 2015-04-30 | 2016-05-31 | 14 | 2.25 |
| La Niña threshold | 2016-08-31 | 2017-02-28 | 7 | -0.96 |
| La Niña threshold | 2017-10-31 | 2018-05-31 | 8 | -1.14 |
| El Niño threshold | 2018-11-30 | 2019-05-31 | 7 | 0.82 |
| La Niña threshold | 2020-06-30 | 2023-04-30 | 35 | -1.46 |
| El Niño threshold | 2023-08-31 | 2024-03-31 | 8 | 1.42 |
| La Niña threshold | 2024-09-30 | 2025-05-31 | 9 | -1.10 |
| La Niña threshold | 2025-09-30 | 2026-03-31 | 7 | -1.04 |

## Interpretation and guardrail

The series supports stratifying or interacting an eventual accessibility contrast by ENSO state. It cannot itself explain spatial variation inside an exact-overpass matched risk set, because every cell in that set shares the same acquisition time and RONI value. Local rainfall, drought, VPD, and wind remain the spatially varying mechanism variables. Any claim that ENSO changed fire requires the separate complete panel and its stated temporal-block uncertainty; any claim that accessibility caused fire still requires the locked measurement and exposure gates.

## Provenance

Source: NOAA CPC ERSSTv6 RONI raw text archived under `data/raw/enso/RONI.ascii.txt`. See `outputs/quality/roni_fetch.json` for retrieval time and SHA-256. Recent values may be revised by CPC; this report is a frozen retrospective retrieval.
