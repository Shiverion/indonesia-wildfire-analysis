# Research Phase Log

This is an append-only implementation log. A phase is marked complete only when its stated evidence exists; a blocked phase is not treated as failed evidence about the hypothesis.

| Logged (UTC) | Phase | Status | Evidence / decision | Next gate |
|---|---|---|---|---|
| 2026-08-20 | Phase 0 — protocol and provenance | **Implemented** | Frozen study configuration, asset manifest, access/redistribution fields, ENSO ingestion, and protocol validator added. | Freeze exact provider asset IDs, download dates, and account terms before analysis. |
| 2026-08-20 13:02 | Phase 0 — open ENSO ingestion | **Complete** | NOAA CPC RONI raw source downloaded; 918 seasonal records (1950-02 through 2026-07) derived. Raw SHA-256: `3292d9f2597ee6d7fea3b76584d2357786fcd8e472f04a2e6765a3802600264d`. | Preserve this retrieval as a retrospective frozen vintage; obtain historical releases for any real-time forecasting claim. |
| 2026-08-20 | Phase 1 — measurement audit | **Started; blocked** | The open RONI source is archived. No science-quality VIIRS swaths, MapBiomas export, ERA5-Land request, or dated historical access asset is present yet. | Obtain free NASA Earthdata and CDS credentials; export licensed/frozen assets; log checksums. |
| 2026-08-20 | Phase 2 — primary Kalimantan association | **Not started** | No eligible 1 km case-overpass risk-set table exists. No coefficients or fire-association conclusion have been estimated. | Pass all Phase 1 measurement and access gates. |
| 2026-08-20 | Phase 3 — burden and event characteristics | **Not started** | No QA-valid burned-area table or event-to-scar linkage exists. | Complete event calibration and burned-area quality audit. |
| 2026-08-20 | Phase 4 — quasi-experimental modules | **Blocked by design evidence** | A dated road-opening series with construction validation is not available. OpenStreetMap edit history is not accepted as construction timing. | Secure a dated, licensed road asset and pass pre-trend/overlap gates. |
| 2026-08-20 | Phase 5 — external replication | **Not started** | No harmonized cross-border data package has been frozen. | Complete the Kalimantan measurement and association phases first. |

## Phase 0 deliverables

- `config/study.json`: locked geography, time split, model-role rules, ENSO timing, vegetation timing, and monitoring rule.
- `data/manifests/assets.json`: access classification, licence/attribution obligations, expected local asset, and readiness status.
- `scripts/research.py`: download, parse, derive, validate, and status commands.
- `outputs/quality/`: machine-readable reports produced by the executable pipeline.

## Evidence rule

The implementation may produce provenance and data-quality reports before it produces any fire result. It must not write an effect estimate, a risk ratio, or a map of apparent human-fire association unless the matching frame, observation opportunities, outcome calibration, and required pre-exposure controls have passed their corresponding gates.

## Next actions, in order

1. Run `fetch-roni` and archive its raw file and hash.
2. Create provider accounts and accept only the stated free-use terms.
3. Fill all `expected_local_path` entries in `data/manifests/assets.json` with frozen source files or exports.
4. Re-run `validate`; do not begin the matched-risk-set construction until all co-primary Phase 1 gates are `ready`.
5. Append a dated row above after each material state change.

## Execution update -- 20 August 2026

| Phase | Status | Evidence / decision |
|---|---|---|
| Auxiliary descriptive measurement | **Complete, non-primary** | NOAA CPC RONI, the anonymous GWIS 2002-2024 aggregate archive, and 323,700 validated SiPongi portal records for July-November 2015-2023 were archived with source hashes. SiPongi raw/canonical hashes, provider configuration/catalogue snapshots, and six 2024 rejected-response receipts are retained. |
| Preliminary insight | **Complete, non-confirmatory** | `outputs/insights/preliminary_synthesis.md` identifies 2015 as the largest GWIS July-November burned-area season and shows that neutral-RONI 2019 still had high aggregate burned area. It states the limited inference and does not estimate the central hypothesis. |
| Phase 1 central measurement audit | **Still blocked** | The validated descriptive sources lack the science-quality S-NPP observation denominator, forest cohort, dated exposures, and pre-event covariates. Phase 1 is not passed. |
| Phase 2 central association | **Not identifiable** | No access/transformation coefficient was fit. The correct current classification is `NI` rather than a positive, negative, or null conclusion. |

The machine-verifiable phase ledger is `outputs/ledger/phase_ledger.jsonl`. Its entries are hash-linked; verify it with `python scripts/research.py verify-ledger`.

## Execution update -- 21 August 2026

| Phase | Status | Evidence / decision |
|---|---|---|
| Phase 0.5 -- Evidence Explorer | **Complete, auxiliary and descriptive** | `outputs/evidence-explorer/index.html` is a dependency-free offline interface backed by `outputs/evidence-explorer/evidence-explorer.json`. It embeds only pre-aggregated RONI, GWIS, and SiPongi values; it excludes SiPongi raw coordinates, local labels, timestamps, source-file identifiers, and quarantined 2024 responses. |
| Visual boundary | **Enforced** | The explorer labels the primary association `NI -- Not identifiable`, keeps legacy-four GWIS and current-five SiPongi geographies separate, defaults SiPongi to NASA-MODIS, and shows an all-platform warning. It is not a risk map or a primary-analysis substitute. |

## Execution update -- interactive-globe revision

| Phase | Status | Evidence / decision |
|---|---|---|
| Phase 0.5 -- globe interaction | **Complete, auxiliary and descriptive** | The former decorative globe and static schematic have been replaced with an offline canvas orthographic globe. It supports pointer/touch rotation, wheel/pinch zoom, click selection, reset/focus/zoom controls, keyboard rotation, and semantic province-table controls. |
| Geographic precision boundary | **Enforced** | The globe uses rounded generalized province aggregate reference anchors and simplified regional outlines solely for orientation. It does not show raw hotspots, events, density surfaces, or claimed administrative polygons. The current-five SiPongi and legacy-four GWIS anchor families remain mutually exclusive. |

## Execution update -- Next.js application

| Phase | Status | Evidence / decision |
|---|---|---|
| Phase 0.5 -- Next.js Evidence Explorer | **Complete, auxiliary and descriptive** | `apps/evidence-explorer/` is a Next.js App Router implementation of the evidence-bounded interactive globe. Its client canvas remains draggable, zoomable, keyboard operable, and paired with a semantic province table. `npm run build` performs a static export to `apps/evidence-explorer/out/`; static hosting does not make the client UI noninteractive. |
| Build-time evidence boundary | **Enforced** | The app synchronizes only `outputs/evidence-explorer/evidence-explorer.json`. It rejects sensitive raw-location field names, raw SiPongi records, quarantined 2024 SiPongi rows, a Phase 1-ready state, or loss of the `NI -- Not identifiable` conclusion, and records a local source SHA-256 receipt. |
| Verification | **Complete** | Type check and production export completed successfully. Local HTTP validation returned the expected title, globe label, `NI -- Not identifiable` guardrail, and no raw-coordinate field. |

## Execution update -- real WGS84 globe revision

| Phase | Status | Evidence / decision |
|---|---|---|
| Phase 0.5 -- real geographic globe | **Complete, auxiliary and descriptive** | The Next.js explorer replaces its custom approximate canvas globe with a CesiumJS WGS84 WebGL globe. It uses actual local GeoJSON polygons, pointer hover, click/tap selection, zoom/orbit, focus/reset/fullscreen controls, an explicit loading/fallback state, and the same semantic table alternative. |
| Frozen visual geography | **Complete** | `apps/evidence-explorer/public/geo/` contains a derived current-five and legacy-four Kalimantan geometry subset built from the commit-pinned geoBoundaries IDN ADM1 simplified source (SHA-256 `5a6be3d1484166132751fe535dd164e1491e657f2d38dced177f067a7bc00d8f`). The displayed legacy Kalimantan Timur is an explicit topological union of current East and North Kalimantan, not a historical-boundary assertion. |
| Surface and provenance boundary | **Enforced** | The globe uses a locally served NASA Blue Marble texture and no Cesium Ion token, default imagery, live tiles, raw hotspot locations, or analytic map layer. The geoBoundaries / OpenStreetMap ODbL attribution, source URLs, source hash, texture hash, and derived geometry hashes are recorded in `public/geo/manifest.json`. |

## Execution update -- map interpretation revision

| Phase | Status | Evidence / decision |
|---|---|---|
| Phase 0.5 -- explanatory globe overlay | **Complete, auxiliary and descriptive** | The real WGS84 globe now presents its active source, period, reporting-unit system, dynamic numeric color range, and an on-map interpretation panel. Province labels identify units; hovering or selecting a polygon adds its displayed aggregate value or `unknown coverage` without cluttering adjacent reporting units. |
| Interpretation boundary | **Enforced** | The on-map guide defines `positive portal record`, `reported hectares`, `unknown coverage`, the source/platform caveat, and the legacy East-plus-North Kalimantan union. It explicitly says color is a relative, logarithmically styled aggregate within the current source/year view, never a fire-risk, causal, location, or cross-source comparison. |
| Interaction and accessibility review | **Complete** | The guide's checkered unknown-coverage key now matches Cesium's rendered checkerboard; provincial label offsets reduce overlap; value labels expand only on hover/selection; the color scale has a semantic caption; and tooltip positioning is state-driven so first hover is positioned correctly. |

## Execution update -- current-data refresh

| Phase | Status | Evidence / decision |
|---|---|---|
| Phase 0.5 -- current descriptive context | **Complete, auxiliary and descriptive** | The NOAA CPC RONI retrieval was refreshed. The latest complete three-month state is MJJ 2026 (ending 31 July 2026), `+0.98 °C`; it is explicitly marked provisional because recent CPC values may revise. |
| Completed SiPongi archive | **Extended with a registered gap** | The completed July-November archive now contains 388,435 validated aggregate portal records for 2015-2023 and 2025. The 2024 responses remain deliberately excluded after validation failure; the year control is source-year based and cannot convert this gap into a zero. |
| 2026 monitoring snapshot | **Complete, partial and non-comparable** | An immutable five-province SiPongi aggregate-only snapshot through the last closed portal-reported day, 20 August 2026, contains 104,465 positive portal records. It is excluded from the completed-season slider, annual chart, and cross-season comparison; no raw locations, timestamps, or observation denominator enter the browser bundle. |
| GWIS comparability boundary | **Enforced** | The official directly comparable Kalimantan monthly aggregate archive remains available only through 2024. No provincial 2025/2026 value was inferred, downscaled, or inserted as a false update. |
| Central research result | **Unchanged** | These freshness updates remain descriptive provenance/context only. Phase 1 is blocked and the access/transformation association remains `NI -- Not identifiable`. |

## Execution update -- global peatland/fire comparison (21 August 2026)

| Phase | Status | Evidence / decision |
|---|---|---|
| Global peatland baseline | **Complete, latest release with historical reference period** | Downloaded the 24 April 2026 CC-BY-4.0 global ensemble peatland raster at ~1 km. It is the newest release, but its mapped reference period is 2000-2020; it is not a 2026 land-cover observation. |
| Global fire comparison | **Complete, exploratory** | Matched 2024 NASA FIRMS MODIS Collection 6.1 standard detections to Natural Earth country polygons and the peat raster for 196 countries with valid FIRMS members. The metric is filtered active-fire point detections (`type=0`, confidence >=30), not unique fires, burned-area pixels, or an observation-adjusted occurrence rate. |
| Primary statistical test | **Not statistically significant** | At the prespecified >=50% peat-extent threshold, country-fixed-effects Poisson counts with log(area) offset gave RR 0.879, 95% CI 0.382-2.025, p=0.763. Threshold sensitivities >=25% and >=75% were also non-significant (p=0.899 and p=0.808; Bonferroni-adjusted p=1.000 for all three). |
| Interpretation boundary | **Enforced** | The crude pooled rate ratio (<1) is not treated as evidence of lower risk because no satellite observation-opportunity denominator exists. The result does not establish that peatland is safer or less vulnerable; it says only that this one-year, country-adjusted detection association is inconclusive. |
| Visualization | **Complete, auxiliary and descriptive** | The Next.js explorer now has a separate global peatland/fire comparison panel with an all-country scatter view, threshold-sensitivity table, model result, source/reference-period explanation, and explicit warning that coloured areas are peat exposure—not burned area. It is not merged into the Kalimantan province globe. |

## Execution update -- conditional peat vulnerability framing (21 August 2026)

| Phase | Status | Evidence / decision |
|---|---|---|
| Hypothesis refinement | **Complete, design pending condition data** | The unconditional “peatland is more vulnerable” question was replaced with a condition-effect question: peat × low soil moisture, peat × drainage/canal proximity, peat × low pre-fire NDMI/EVI, and peat × fire-weather anomaly. |
| Estimand | **Specified** | The target is an interaction rate ratio, such as `exp(beta_peat×dry)`, in a count model with country/region effects, season terms, and a satellite observation-opportunity offset. It is not a main-effect claim that all peatland is dangerous. |
| Evidence boundary | **Enforced** | HLS NDMI/EVI, ERA5-Land or equivalent hydrology/weather, and a temporally valid drainage layer are not yet all locally frozen and Phase 1-ready. The UI labels the condition panel “Not estimated yet”; no unsupported interaction estimate is shown. |

## Execution update -- condition-phase audit (21 August 2026)

| Phase | Status | Evidence / decision |
|---|---|---|
| Local audit | **Complete, blocked** | `python scripts/research.py condition-audit` now writes `outputs/quality/condition_phase_audit.json` and distinguishes missing inputs from sensitivity-only inputs. Structural validation is not conflated with readiness. |
| Peat baseline | **Ready for sensitivity** | The 24 April 2026 global ensemble raster is present, valid EPSG:4326, uint8, nodata 255, ~1 km, and explicitly marked as a 2000-2020 reference—not 2026 land cover. |
| Drainage | **Usable sensitivity only** | Dadap et al. canal archive downloaded and hashed (`d1771dd46e440a74d7f9f8f557856238a0acc3fed27618f213d5cf6f288f56a9`); it is based on 2017 imagery and is not a 2014 construction-time series. |
| Remaining condition gates | **Blocked** | VIIRS outcome/opportunity, ERA5-Land, CHIRPS, and pre-fire vegetation are still absent locally; the condition interaction model cannot yet be estimated. Dated access remains blocked for the original hypothesis. |
| Explorer status | **Visible and gated** | The browser bundle now includes only the condition-audit statuses; it reports how many input groups remain blocked and cannot unlock the condition model from a static sensitivity layer. |

## Execution update -- parallel Phase 1 refresh (22 August 2026)

| Phase | Status | Evidence / decision |
|---|---|---|
| Input expansion | **In progress, resumable** | ERA5-Land 2015 currently has January-August files; the CDS process is continuing for September-December. Existing files are reused and the final manifest will be rebuilt after the request completes. |
| VIIRS measurement preparation | **Complete locally, gate still blocked** | The local archive contains 60 VNP14IMG/VNP03IMG acquisition-key pairs with 0 unpaired or ambiguous keys. `data/derived/viirs/viirs_pair_index.csv` and `outputs/quality/viirs_pair_index.json` record the pairing; a valid processed/non-detection opportunity frame has not been inferred. |
| Local integrity audit | **Complete, blocked** | `outputs/quality/phase1_local_audit.json` records 153 contiguous CHIRPS July-November dates plus one explicitly labelled January smoke-test file, 144 valid MOD13Q1 HDF payloads across 24 composites, readable peat/drainage sensitivity inputs, and the known manifest-scope reconciliation. |
| Descriptive reports | **Refreshed** | ENSO, GWIS, SiPongi, and preliminary synthesis Markdown reports were regenerated from the current local aggregates. They remain descriptive and do not estimate accessibility, transformation, or causal effects. |
| Next.js dashboard | **Refreshed and built** | The aggregate bundle was rebuilt, synchronized into `apps/evidence-explorer/data/evidence-explorer.json`, type-checked, and statically exported to `apps/evidence-explorer/out/`. The `NI -- Not identifiable` and Phase 1 guardrails remain enforced. |
| Phase log and decision | **Hash-valid, still locked** | The machine ledger is at sequence 30 and verifies successfully. Phase 2 model fitting remains blocked until ERA5 completion, VIIRS observation-opportunity construction, vegetation QA/timing, MapBiomas 2014, dated access, and frozen provenance pass. |

## Execution update -- report and dashboard refresh (22 August 2026)

| Phase | Status | Evidence / decision |
|---|---|---|
| Markdown reports | **Regenerated** | `outputs/insights/enso_context.md`, `gwis_enso_context.md`, `sipongi_enso_context.md`, and `preliminary_synthesis.md` were rebuilt from the current local aggregate inputs. |
| Next.js Evidence Explorer | **Built successfully** | The bundle was synchronized into `apps/evidence-explorer/data/evidence-explorer.json`; TypeScript checking and the static export to `apps/evidence-explorer/out/` both passed. |
| Guardrail | **Enforced** | The refreshed dashboard still shows `NI - Not identifiable`, `phase_1_ready=false`, aggregate-only evidence, and no causal/accessibility result. |
| Ledger | **Hash-valid** | Sequence 31 records this refresh; `python scripts/research.py verify-ledger` reports 31 valid entries. |

## Execution update -- ERA5 2015 completion and final refresh (22 August 2026)

| Phase | Status | Evidence / decision |
|---|---|---|
| ERA5-Land calibration year | **Complete** | All 12 monthly 2015 NetCDF files are present and hashed in `data/raw/era5_land/download_manifest.json`. No additional year has been downloaded yet. |
| Validation refresh | **Complete structurally, blocked scientifically** | Condition audit and protocol validation were rerun. Structural validation passes with zero errors, but `phase_1_ready=false` because valid VIIRS non-detection opportunities, vegetation QA/timing, MapBiomas 2014, dated access, and frozen provenance remain unresolved. |
| Reports and dashboard | **Refreshed** | The descriptive Markdown reports and aggregate Evidence Explorer were regenerated from the completed local inputs; the Next.js bundle was synchronized and its static export completed successfully. |
| Decision boundary | **Unchanged** | 2015 is calibration evidence only. No Phase 2 association estimate or causal conclusion is released. The hash-linked ledger is at sequence 32 and verifies successfully. |

## Execution update -- VIIRS geolocation and swath QA (22 August 2026)

| Phase | Status | Evidence / decision |
|---|---|---|
| Paired-swath screening | **Complete locally** | All 60 paired VNP14IMG/VNP03IMG swaths were read successfully after repairing one corrupt VNP03 granule. The summary contains 2,486,272,000 finite geolocation pixels and 253,981,209 pixels inside the study bounding box. |
| Opportunity denominator | **Not ready** | These counts are screening diagnostics only. No pixel was labelled a negative observation or a valid opportunity; the 2014 forest intersection, cloud/water/quality rules, grid overlap, and coverage thresholds remain to be applied. |
| Repaired input | **Quarantined and receipted** | The unreadable granule was moved to `data/raw/viirs/_rejected/` and replaced from the authenticated LAADS URL. Its old and new hashes are recorded in `outputs/quality/viirs_repair_2015002_0712.json`; the canonical overwritten download manifest was not fabricated. |
| Verification | **Complete, gated** | New swath QA tests plus the existing suite pass (31 tests). Reports and the Next.js static bundle were refreshed. Phase 1 remains blocked and the central conclusion remains `NI -- Not identifiable`. |

## Execution update -- global world globe and source attribution (22 August 2026)

| Phase | Status | Evidence / decision |
|---|---|---|
| Kalimantan evidence globe | **Kept source-bound** | The SiPongi current-five and GWIS legacy-four WGS84 globe remains restricted to its approved province reporting systems. Those polygons are not merged with country data and are not fire locations. |
| Global comparison globe | **Complete, exploratory** | Added a separate interactive WGS84 world globe using 242 frozen Natural Earth Admin-0 display geometries and a join to the 196 matched peat/fire country aggregates. Users can orbit, zoom, hover, click, switch peat-share versus detection-rate coloring, and select every matched country from an accessible picker. |
| Map interpretation | **Explained in UI** | The global legend and detail drawer state that color is a country aggregate, not the area burned; unknown geometries/values use a checkerboard rather than zero; the map contains no raw hotspot points or interpolated risk. |
| Source attribution | **Complete** | Header now contains a “Data taken from” strip with local NASA, NOAA, MapBiomas Indonesia, Global Forest Watch/WRI, GWIS/JRC, and SiPongi/Kemenhut logo assets plus source links and a logo provenance manifest. CHIRPS remains a named text source because no verified local logo asset was required for this view. |
| Verification | **Complete** | `npm run check` and `npm run build` pass. The static export is in `apps/evidence-explorer/out/`; serve it over HTTP rather than opening `index.html` via `file://`. Ledger sequence 34 records this UI phase and verifies hash-valid. |

## Execution update -- Phase 1A temporal support and opportunity QA (23 August 2026)

| Phase | Status | Evidence / decision |
|---|---|---|
| Temporal QA implementation | **Complete, local-only** | Added `src/wildfire_research/temporal_qa.py`, `scripts/validate_phase1_temporal.py`, and the `python scripts/research.py temporal-qa` command. The QA reports date/year coverage and refuses to unlock inputs from file presence alone. |
| ERA5-Land | **Calibration year only** | All 12 months of 2015 are present with the declared wind, temperature, rainfall, and soil-water variables. Years 2016-2025 are absent; event-level UTC lagging remains unvalidated. |
| CHIRPS v3 | **2015 support window complete** | July 1-November 30, 2015 has 153 unique final/RNL dates. The January 1 smoke-test file is recorded as an extra date and not included in the study window; antecedent lag extraction is not yet run. |
| MOD13Q1 vegetation | **Inventory only** | 144 HDF payloads cover 24 composites across 2014-2015 and six tiles. QA SDS extraction and event-specific pre-fire support are still unvalidated; no EVI value enters a model. |
| VIIRS opportunity | **Swath screening only** | 60 paired 2015 VNP14/VNP03 swaths screen successfully, but no pixel is labelled a negative observation or valid denominator opportunity. The 2014 forest intersection, quality/cloud rules, and coverage threshold remain required. |
| Dashboard/report refresh | **Complete, still gated** | Condition audit now exposes the temporal QA status in the dashboard. `python -m pytest -q` passes 35 tests; Next.js static build passes. Phase 1 remains `phase_1_ready=false`, and ledger sequence 37 verifies hash-valid. |

## Execution update -- Phase 1A ERA5 study-window acquisition (23 August 2026)

| Phase | Status | Evidence / decision |
|---|---|---|
| ERA5 manifest handling | **Fixed** | `scripts/download_era5_land.py` now merges the existing manifest by `(year, month)` instead of overwriting prior years when a resumed request completes. |
| ERA5 2016-2025 acquisition | **In progress** | A hidden, sequential, resumable process is running with the registered CDS credentials. Existing 2015 files are reused; progress is recorded in `outputs/quality/era5_study_window.stdout.log` and `.stderr.log`. |
| Gate policy | **Unchanged** | Download completion alone will not unlock Phase 1. Each month still needs timestamp/variable/bounds validation, and VIIRS needs a processed negative opportunity frame. Ledger sequence 38 records the acquisition start and verifies hash-valid. |

## Execution update -- latest global FIRMS default and all-country globe (23 August 2026)

| Phase | Status | Evidence / decision |
|---|---|---|
| Global latest snapshot | **Complete, closed-day aggregate** | Downloaded the official NASA FIRMS NRT global MODIS + NOAA-20 + NOAA-21 + Suomi-NPP files for the latest closed UTC day, 22 August 2026. The 23 August portal day was not used because it was still intraday. |
| Country aggregation | **Complete, aggregate-only** | 394,627 positive satellite detection records were parsed; 392,696 matched the frozen 242-feature Natural Earth country geometry and 1,931 remained unmatched. The derived country table contains no coordinates or raw records and has no observation denominator. |
| Dashboard default | **Complete** | The global WGS84 globe is now shown before the Kalimantan local layer and defaults to the 22 August 2026 NRT metric. Completed 2024 MODIS and peatland-share views remain explicit comparison modes. All 242 country geometries are available; color is a country aggregate, not burned area. |
| Validation | **Complete, still scientifically gated** | `python -m pytest -q` passes 35 tests; `npm run check` and `npm run build` pass. Phase 1 remains `phase_1_ready=false`; the latest snapshot is descriptive monitoring evidence, not a fire rate, risk surface, or causal result. |
