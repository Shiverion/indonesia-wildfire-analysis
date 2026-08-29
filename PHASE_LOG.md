# Research Phase Log

This is an append-only implementation log. A phase is marked complete only when its stated evidence exists; a blocked phase is not treated as failed evidence about the hypothesis.

## Execution update -- zero-budget scope and raw archive inventory (25 August 2026)

| Item | Status | Decision |
|---|---|---|
| Full CHIRPS/MOD13Q1/VIIRS acquisition | **Stopped** | No paid storage or cloud compute will be used. Existing payloads are retained; no new full-archive retry is allowed for the pilot. |
| Raw inventory | **Complete** | `scripts/inventory_raw_sources.py` writes `outputs/quality/raw_source_inventory.json`; the three source folders total about 47.10 GiB. |
| Pilot configuration | **Frozen** | `config/zero_budget_pilot_2015.json` limits the next executable analysis to 2015 event-level summaries in Kalimantan. |
| Scientific claim boundary | **Explicit** | The pilot can estimate environmental associations, but not a 2015–2025 trend, global generalisation, or causal actor attribution. |
| Raw storage relocation | **Complete** | The repository `data/raw` path is a verified junction to `D:\projects\Indonesia Wildfire Analysis\data\raw` (6,456 files; 58.53 GiB). The temporary C: duplicate was moved to the Recycle Bin after byte verification. |

## Execution update -- local 2015 pilot event table (26 August 2026)

| Item | Status | Evidence / boundary |
|---|---|---|
| Junction-aware validation | **Fixed** | Validators now preserve logical `data/raw/...` paths when the physical payload is on D:. ERA5 content QA passes after installing the small `netCDF4` reader dependency. |
| Pilot event table | **Complete, descriptive only** | `data/derived/pilot/pilot_event_level_2015.csv` contains 50 local diagnostic overpass-events (28 positive, 22 negative); 43 have complete 72-hour ERA5 support. |
| Pilot statistics | **Complete, exploratory only** | `outputs/quality/pilot_2015_descriptive_stats.json` and `outputs/insights/pilot_2015_environment.md` report medians and screening tests. No Phase 2 coefficient is released. |
| Missing joins | **Explicit** | CHIRPS and peat are not spatially linked; MOD13Q1 is a tile summary; VIIRS remains a diagnostic subset rather than the canonical 2015–2025 opportunity frame. |

## Execution update -- recovery after laptop restart (26 August 2026)

| Item | Status | Evidence / boundary |
|---|---|---|
| Download recovery check | **Complete** | No downloader is active. Existing raw payloads remain intact on D:; the old CHIRPS watchdog log records exhausted retries and was not restarted because the zero-budget policy forbids a new multi-year archive run. |
| Local checkpoint refresh | **Complete** | Raw inventory rechecked at 6,188 files / 47.11 GiB; the 2015 pilot was regenerated with the same 50 events and 43 complete-weather events. |
| Gate revalidation | **Complete, still blocked** | Phase 1B remains `phase_1b_ready=false`, Phase 2 remains `phase_2_unlock=false`, and the condition audit remains blocked because spatial event linkage and the canonical VIIRS opportunity denominator are absent. |
| Regression tests | **Passed** | Python unittest discovery: 28 tests passed after restart. |

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
| Phase 0.5 -- Next.js Evidence Explorer | **Complete, auxiliary and descriptive** | `apps/evidence-explorer/` is a Next.js App Router implementation of the evidence-bounded interactive globe. Its client canvas remains draggable, zoomable, keyboard operable, and paired with a semantic province table. `npm run build` creates a server-capable production application because the accountable assistant uses a server-side API route. |
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
| Interaction and accessibility review | **Complete** | The guide's checkered unknown-coverage key now matches Cesium's rendered checkerboard; provincial label offsets reduce overlap; value labels expand only on hover/selection; the color scale has a semantic caption; and tooltip positioning is state-driven so first hover is positioned correctly. Drag release now re-picks the geometry under the cursor and restores the pointer/tooltip state on both globes, while canvas exit clears any interrupted drag. |

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

## Execution update -- Indonesia province view (23 August 2026)

| Phase | Status | Evidence / decision |
|---|---|---|
| Global country view | **Kept** | The world-country mode remains a country aggregate view; Indonesia is intentionally one country polygon there. It must not be read as a province map. |
| Indonesia ADM1 view | **Complete, descriptive** | Added a separate switch using 34 frozen geoBoundaries Indonesia ADM1 display units (reference year 2017). The layer loads `/geo/indonesia-adm1.geojson` and does not merge it into the country geometry. |
| Latest provincial counts | **Complete, aggregate-only** | The 22 August 2026 FIRMS NRT snapshot contains 22,788 matched positive detection records inside the 34 Indonesia ADM1 units. The browser exposes province aggregates only; no coordinates, raw detections, or observation denominator are included. |
| Interpretation | **Guarded** | The province mode is a display of source-boundary units and positive detection records, not a current legal boundary map, fire-rate surface, burned-area map, or causal result. |

## Execution update -- Phase 1B closure gate (23 August 2026)

| Workstream | Status | Evidence / decision |
|---|---|---|
| Phase 1B implementation | **Complete, gate blocked** | Added `src/wildfire_research/phase1b.py`, the `phase1b-audit` command, and tests. The report is written to `outputs/quality/phase1b_readiness.json`; it never unlocks Phase 2 by file presence alone. |
| ERA5-Land temporal support | **In progress** | The current local audit sees 69 of 132 registered 2015-2025 monthly payloads (complete through 2019 and through September 2020). NetCDF variable, hourly-time, and study-bounding-box checks are now enforced for each available file; the active resumable download remains untouched. |
| VIIRS observation denominator | **Blocked** | The required `data/derived/viirs/opportunity_frame.csv` does not exist. Swath screening remains a diagnostic, not a valid negative-observation denominator. The new validator requires both positive and valid-negative rows and rejects coordinate-bearing browser-style payloads. |
| Climate and vegetation lags | **Blocked** | CHIRPS 1/7/30/90-day lag tables and QA/timed MOD13Q1 EVI/NDMI tables have not been built; no values enter a model. |
| Baseline/exposure provenance | **Blocked** | Frozen MapBiomas 2014, peat/drainage timing, and the dated-access sensitivity remain unresolved in the manifest. |
| Phase 2 decision | **Locked** | `phase_1b_ready=false` and `phase_2_unlock=false`. `lock-test` now also enforces the Phase 1B gate and refuses to create the 2024-2025 input archive. Ledger sequence 40 records this closeout enforcement; run `python scripts/research.py phase1b-audit` after the ERA5 process finishes. |

## Execution update -- parallel Phase 1B preparation (24 August 2026)

| Workstream | Status | Evidence / decision |
|---|---|---|
| Prefire covariate utilities | **Implemented, not yet applied to model rows** | Added pure, tested helpers for VPD, wind speed, complete 1/7/30/90-day daily lag sums, and pre-fire interval checks. Missing support or look-ahead fails closed; no imputation was introduced. |
| Peat/drainage provenance | **Frozen for sensitivity** | `outputs/quality/peat_sensitivity_provenance.json` records byte hashes, source links, licenses, and the 2000-2020 peat / 2017 drainage limitations. These inputs remain sensitivity-only and do not unlock Phase 1 or Phase 2. |
| Phase 1B dashboard status | **Visible, locked** | The browser bundle now carries compact Phase 1B workstream statuses and the conditional-peat panel reports the gate, next actions, and the no-model-release rule. No raw paths, coordinates, or provider rows are embedded. |
| Validation | **Pass with gate blocked** | Python test suite: 41 passed. Phase 1B audit remains `blocked_phase1b_workstreams` with `phase_1b_ready=false` and `phase_2_unlock=false`. Next.js type-check and static build pass. |

## Execution update -- live ERA5 acquisition checkpoint (24 August 2026)

| Workstream | Status | Evidence / decision |
|---|---|---|
| ERA5-Land study window | **In progress, resumable** | The registered process remains active (PID 668). The latest read-only inventory contains 76 complete monthly NetCDF files, covering 2015 through April 2021, approximately 6.20 GiB. |
| Phase 1B audit refresh | **Blocked, current** | `outputs/quality/phase1b_readiness.json` now reflects the 76-file inventory, but the gate remains blocked until all 132 months pass content/timing QA and downstream lag extraction is complete. |
| Dashboard refresh | **Complete, still gated** | The aggregate bundle and static Next.js export were rebuilt from the refreshed readiness artifact; the browser still states `phase_1b_ready=false` and `phase_2_unlock=false`. |

## Execution update -- research-module roadmap (24 August 2026)

| Module | Existing phase | Status / next action |
|---|---|---|
| Environmental conditions | Phase 1B → Phase 2 | Highest priority. Complete ERA5/CHIRPS/vegetation temporal support and the VIIRS opportunity denominator before estimating peat × dryness interactions. |
| Fire followed by land-cover change | Phase 3 | Next feasible extension. Prepare lagged forest-loss/land-cover change, but do not label it palm expansion or intentional burning without dated plantation evidence. |
| Governance and actor attribution | Phase 4 | Postponed. Requires dated intervention, permit, ownership, enforcement, budget, and restoration records plus a defensible comparison design. |
| Global replication | Phase 5; descriptive preparation in Phase 0.5 | Current globe remains descriptive. Standardize outcome, period, sensor, area offset, and observation denominator before inferential cross-country modelling. |

The full mapping and ordering are documented in `ENHANCED_RESEARCH_METHOD.md` and `outputs/insights/preliminary_synthesis.md`.

## Execution update -- registered zero-budget daily environmental track (26 August 2026)

| Workstream | Status | Evidence / decision |
|---|---|---|
| Daily observation denominator | **Implemented; full extraction running** | Registered `NASA/VIIRS/002/VNP14A1` daily FireMask for July-November 2015-2025: class 5 negatives, classes 7-9 positives, three-day prior-negative/coverage rule, and seven-day refractory period. Three resumable workers cover 1,683 days. |
| Matched controls | **Smoke test passed** | A 1 October 2015 test reduced 9,448 Earth Engine candidates to 33 complete baseline-forest cases and exactly 132 controls within 25 km. A 1 October 2025 test also passed. Controls are selected deterministically at 4:1; incomplete sets fail closed. |
| Environmental covariates | **Implemented** | Earth Engine supplies pre-event CHIRPS 1/7/30/90-day rainfall and SummaryQA=0 MOD13Q1 EVI; local processing supplies MapBiomas forest fraction, frozen peat extent, and exact pre-event ERA5-Land 24/72-hour metrics. |
| Coastal ERA5 support | **Fail-closed rule frozen** | Use only the nearest fully valid native ERA5-Land cell within 25 km and record distance; otherwise exclude the whole matched set. No ocean/no-data cell is converted to zero. |
| Phase gate logic | **Corrected** | Removed permanent `gate_ready=false` placeholders. The environmental track can pass on complete receipts and a valid immutable lock, while the human-access/intent/governance track remains independently blocked by missing dated exposure. |
| Cost/storage | **Zero paid storage** | Full source archives are not required for CHIRPS/MOD13Q1/VNP14A1. Only analysis-ready risk-set chunks are stored locally; existing swaths remain sensitivity evidence. |
| Verification | **Passed so far** | Two cross-year Earth Engine smoke tests passed; the full Python suite passes 59 tests. No Phase 2 model has been fitted. |

## Execution update -- ERA5-Land study window complete and Phase 1B re-audit (25 August 2026)

| Workstream | Status | Evidence / decision |
|---|---|---|
| ERA5-Land acquisition | **Complete** | All 132 monthly NetCDF payloads for 2015–2025 are present (about 10.8 GiB), with no `.part` files remaining. The downloader's manifest contains a SHA-256 receipt for every month. |
| ERA5 content QA | **Passed** | `scripts/research.py phase1b-audit` checked all 132 files for the eight required variables, hourly timestamp length/bounds, and the registered Kalimantan bounding box; no content errors or missing months were found. |
| Phase 1B gate | **Still blocked** | ERA5 is now `ready_for_lag_derivation`, but CHIRPS 1/7/30/90-day features, QA/timed pre-fire MOD13Q1 vegetation, the VIIRS valid-negative opportunity frame, and exposure/provenance remain blocked. Phase 2 is not unlocked. |
| Dashboard/report refresh | **Complete** | Temporal QA, Phase 1B readiness, aggregate bundle, and the static Next.js build were regenerated. The UI now reports the complete ERA5 window while preserving the scientific lock. |
| Verification | **Passed** | Python test suite: 44 passed. Next.js type-check and production build passed. |

The next executable work is Phase 1B lag/denominator closure—not Phase 2 model fitting. `outputs/quality/phase1b_readiness.json` is the current gate artifact.

## Execution update -- MOD13Q1 QA extraction and Phase 1B re-audit (25 August 2026)

| Workstream | Status | Evidence / decision |
|---|---|---|
| MOD13Q1 HDF4 extraction | **QA validated, summary only** | Added `scripts/build_mod13q1_prefire_features.py` using the official `MOD13Q1.061` EVI and VI Quality SDSs. All 144 local HDF payloads were clipped to the registered WGS84 bbox and hashed in `data/derived/mod13q1/mod13q1_2015_tile_summary.csv`. |
| Frozen QA rule | **Recorded** | Retained MODLAND QA=good, VI usefulness ≤1, no adjacent/mixed cloud, land-only flag, no snow, no shadow, and EVI valid range −2000..10000 scaled by 1/10000. Receipt: `outputs/quality/mod13q1_2015_prefire_qa.json`. |
| 2015 coverage | **Partial** | The local archive contains 23 2015 composites across four intersecting tiles; 47,963,168 pixels pass the conservative QA rule. This is a tile/composite summary, not an event-level pre-fire table. |
| Phase 1B gate | **Still blocked, correctly** | `prefire_vegetation=qa_validated_summary_only`; 2016–2025 composites, cutoff linkage, complete CHIRPS years, and the canonical VIIRS opportunity denominator remain absent. `phase_1b_ready=false` and `phase_2_unlock=false`. |
| Verification | **Passed** | Python test suite: 54 passed. Temporal QA and Phase 1B readiness reports were regenerated after the extraction. |

## Execution update -- resilient acquisition fallback (25 August 2026)

| Workstream | Status | Evidence / decision |
|---|---|---|
| CHIRPS retry | **Installed** | Each daily request now retries up to five times with exponential backoff, writes to an exact `.part` file, validates non-empty output, and atomically renames it to the final COG. Existing non-empty COGs remain resumable. |
| Earthdata retry | **Installed** | MOD13Q1 and VNP14 Earthdata downloads now use bounded batches with five retry attempts; VNP03 LAADS downloads retry with the same backoff and atomic `.part` handling. Existing payloads are skipped. |
| Automatic watchdog | **Running** | `scripts/download_supervisor.py` is watching the three active PIDs and will restart an incomplete job automatically, up to 20 attempts, using the patched downloaders. Logs are kept under `outputs/download_logs/` (ignored by Git). |
| Safety | **Preserved** | No raw payloads were deleted. A job is considered complete only when its 2015–2025 manifest is refreshed and contains no recorded transient download errors. |

## Execution update -- CHIRPS source-grid lag cache (25 August 2026)

| Workstream | Status | Evidence / decision |
|---|---|---|
| CHIRPS lag derivation | **Partial, validated** | Built 1,787,184 source-grid rows for 63 cutoffs from 29 September through 30 November 2015, with complete 1/7/30/90-day pre-cutoff support and no imputation. |
| Scope boundary | **Explicit** | The cache covers only the downloaded 2015 July-November support window and is not linked to fire events or the VIIRS denominator. It cannot unlock Phase 1B by itself. |
| Next dependency | **Blocked externally** | Expand CHIRPS support to the registered study years and construct the valid-negative VIIRS frame after a frozen 2014 forest mask is available. |

## Execution update -- VIIRS opportunity classifier contract (25 August 2026)

| Workstream | Status | Evidence / decision |
|---|---|---|
| Pixel classification | **Implemented and tested** | Added a fail-closed classifier for paired VNP14/VNP03 arrays. It retains only clear-land class 5 negatives and fire classes 7–9 after geolocation, nominal quality, land, forest, coverage, and prior-negative checks. |
| Frame safety | **Strengthened** | The Phase 1B validator now requires both positive and negative rows that are actually marked `valid_opportunity=true`; a mere mixture of labels cannot unlock the denominator. |
| Current gate | **Blocked** | No frozen MapBiomas 2014 forest mask or event-level prior-negative linker is present, so no `opportunity_frame.csv` was fabricated. |

## Execution update -- MapBiomas export preflight (25 August 2026)

| Workstream | Status | Evidence / decision |
|---|---|---|
| Official export route | **Implemented** | Added `scripts/mapbiomas_collection41_export.js` for the registered MapBiomas Landy/GEE workflow. The recipe requires the exact Collection 4.1 asset ID and exports original 2014 class codes over the Kalimantan bounding box. |
| Local hand-off validator | **Implemented and passed** | Added `src/wildfire_research/mapbiomas.py`, `mapbiomas-preflight`, a crosswalk/provenance schema, and tests. The downloaded Collection 4.1.1 raster, official class crosswalk, provenance receipt, and SHA-256 are validated in `outputs/quality/mapbiomas_2014_preflight.json`. |
| Scientific safeguard | **Unchanged** | Natural-forest codes must be copied from the official Collection 4.1 legend and reviewed before the VIIRS forest denominator is built. Phase 1B and Phase 2 remain locked. |

## Execution update -- MapBiomas 2014 baseline acquired and validated (25 August 2026)

| Workstream | Status | Evidence / decision |
|---|---|---|
| Country-wide baseline export | **Complete** | Downloaded the official MapBiomas Indonesia Collection 4.1.1 2014 coverage GeoTIFF (`210,713,020` bytes) and stored it at `data/raw/mapbiomas_indonesia/mapbiomas_indonesia_c41_landcover_2014.tif`. |
| Raster integrity | **Passed** | EPSG:4326, one band, 170,756 × 63,429 pixels, nodata 0, country-wide bounds, and non-empty class sample. SHA-256: `2df0a9ac95abbd741c62f42993b861268f4d49a10da02c79be95babbef1b8db7`. |
| Natural-forest crosswalk | **Frozen for review** | Collection 4.1 legend codes 3 (Forest Formation), 5 (Mangrove), and 76 (Peat Swamp Forest) are recorded in `class_crosswalk.json`; the raster will be clipped to the Kalimantan analysis region downstream. |
| Phase 1B gate | **Still blocked** | MapBiomas is ready, but the full gate remains closed until a QA/timed MOD13Q1 table, complete CHIRPS support, a valid VIIRS positive/negative opportunity frame, and exposure provenance are present. |

## Execution update -- Kalimantan natural-forest mask built (25 August 2026)

| Workstream | Status | Evidence / decision |
|---|---|---|
| Binary forest mask | **Complete and validated** | Read the country-wide raster in tiled windows and wrote `data/derived/mapbiomas/mapbiomas_c41_natural_forest_mask_2014_kalimantan.tif`; no full-raster memory load or resampling was used. |
| Frozen definition | **Explicit** | Mask value `1` means MapBiomas Collection 4.1.1 class 3 (Forest Formation), 5 (Mangrove), or 76 (Peat Swamp Forest); `0` means all other classes or source nodata. |
| Coverage and summary | **Recorded** | 40,817 × 40,817 pixels over the registered Kalimantan bbox; 641,808,163 valid source pixels, of which 410,414,605 (63.95%) are natural-forest classes. Receipt: `outputs/quality/mapbiomas_2014_forest_mask.json`. |
| Phase 1B gate | **Still blocked** | The mask is ready for 1-km forest-fraction extraction, but a valid paired VIIRS positive/negative opportunity frame has not yet been constructed. |

## Execution update -- 1-km fixed forest cohort prepared (25 August 2026)

| Workstream | Status | Evidence / decision |
|---|---|---|
| Analysis grid | **Complete and validated** | Aggregated the binary 30 m mask to the origin-anchored EPSG:6933 1-km grid without treating zero-valued pixels as nodata. Output: `data/derived/mapbiomas/mapbiomas_c41_forest_fraction_1km_kalimantan.tif`. |
| Cohort counts | **Recorded** | 1,491,389 grid cells are represented; 329,365 meet the primary `forest_fraction >= 0.70` threshold and 366,153 meet the `>= 0.50` sensitivity threshold. Receipt: `outputs/quality/mapbiomas_2014_forest_fraction_1km.json`. |
| Scientific boundary | **Preserved** | The fraction defines fixed baseline landscape eligibility only. It is not a fire rate, a land-use-change measure, or a valid negative observation. |
| Phase 1B gate | **Still blocked** | Next dependency is intersecting paired VNP14/VNP03 science swaths with this grid and applying quality, coverage, cloud/water, and 72-hour prior-negative rules. |

## Execution update -- VIIRS/forest intersection diagnostic (25 August 2026)

| Workstream | Status | Evidence / decision |
|---|---|---|
| Paired swath intersection | **Diagnostic complete** | Streamed all 60 locally paired VNP14/VNP03 granules from the 2015 rehearsal window against the EPSG:6933 1-km forest cohort, with quality=0, land-water=Land, classes 5/7/8/9, and the ≤72-hour prior-negative rule. |
| Diagnostic counts | **Recorded, not inferential** | 5,057,389 candidate cell-pair rows; 4,477,822 rows had a prior negative within 72 hours; 594 positive and 4,477,228 negative rows. Receipt: `outputs/quality/viirs_opportunity_diagnostic.json`. |
| Scientific gate | **Still blocked** | The large row-level CSV is local-only and the archive covers only 2015. This is not the canonical `opportunity_frame.csv`; complete 2015–2025 swaths, event linkage, duplicate/orbit handling, and final registered coverage rules are still required. |

## Execution update -- source-gap repair before Phase 1B lock (26 August 2026)

| Workstream | Status | Evidence / decision |
|---|---|---|
| Daily extraction | **Complete** | Receipts exist for all 1,683 registered fire-season days and ERA5 attachment initially completed for all days. The pre-repair frame contained 13,911 cases and 55,644 controls. |
| Duplicate audit | **Repair implemented** | Three matched sets contained exact logical duplicates from repeated projected cell rows. Candidate matching now deduplicates identical cell-day/outcome rows and fails closed on conflicting copies; the finalizer also removes identical legacy logical copies before generating public IDs. |
| VNP14A1 availability | **Confirmed source gaps** | The official VNP14A1 archive lacks 15 event days in 2022 and 14 in 2024. Those event days remain no-observation. The earlier all-or-nothing history rule expanded the 2024 loss to 42 days and reduced support to 72.55%, below the registered 80% gate. |
| History-only amendment | **Registered before modeling** | When the VNP14A1 event day exists but a required lookback date is absent, science-quality NASA Terra MOD14A1.061 and Aqua MYD14A1.061 are fused only for prior-fire/processed-land history. Both products cover every confirmed history-gap date. They never define primary cases, and an exclusion sensitivity is mandatory. |
| Validation state | **Passed; Phase 2 environmental track unlocked** | The 80% threshold was unchanged. The final frame contains 14,091 cases and 56,364 controls in exactly 14,091 1:4 matched sets, with 70,455 rows and no validation errors. Annual support is at least 90.20% in every affected year (2022: 90.20%; 2024: 90.85%). The frame hash is `0112938dce8ee6a377b18812d26020566376c5f83047ef28d89432245da98936`; the 34-file immutable lock hash is `989adead69331806f3c0f3f9a578c2ca8296a108903ed276aad771ec483351a6`. `phase_1b_ready=true` and `phase_2_unlock=true` for the environmental daily-grid track. The human-access/intent/governance track remains separately blocked. |

## Execution update -- resilient ERA5 month retry (24 August 2026)

| Change | Status | Evidence / decision |
|---|---|---|
| Terminal CDS job failures | **Fixed** | `scripts/download_era5_land.py` now resubmits a failed month job up to two times by default instead of terminating the entire study-window download after a 400 result error. |
| Partial payload protection | **Fixed** | Each new response is written to a `.part` path and atomically renamed to `.nc` only after a non-empty payload is returned; failed attempts remove only the exact temporary file. |
| Regression coverage | **Complete** | Added month-level retry and partial-cleanup tests; full Python suite passes 43 tests. |
| Live process | **Running** | Replaced the old PID 32144 process with patched PID 16784; 93 completed months remain intact and the 2022-10 request is being retried automatically. |

## Execution update -- Phase 2 environmental matched-risk-set analysis (26 August 2026)

| Workstream | Status | Evidence / decision |
|---|---|---|
| Model specification | **Frozen before the first successful fit** | `config/phase2_model_specification.json` fixes conditional logistic regression, the primary peat ≥50% × root-zone dryness interaction, 25%/75% thresholds, fallback exclusion, the 2024-2025 locked test, three Holm-adjusted secondary interactions, and held-out prediction metrics. |
| Pre-fit covariate QA | **One set excluded fail-closed** | The initial transform stopped before fitting because one 11 August 2015 control contained CHIRPS sentinel `-9999`. The entire five-row set was excluded without zero replacement or imputation; the immutable source frame remains unchanged. Phase 2 uses 70,450 rows, 14,090 cases, 56,360 controls, and 14,090 exact sets. |
| Primary association | **Complete; inconclusive** | Peat ≥50% × one development-period SD drier 72-hour root-zone soil: interaction OR `0.8659`, 95% CI `0.6917-1.0839`, two-sided p=`0.2088`. The interval includes 1, so neither a stronger nor weaker conditional peat gradient is established. |
| Mandatory sensitivities | **Complete; mixed, do not override primary** | Excluding fallback-history dates is similar (OR `0.8637`, CI `0.6900-1.0811`). Threshold ≥25% is lower (OR `0.8011`, CI `0.6499-0.9874`), threshold ≥75% is inconclusive (OR `1.0398`, CI `0.8458-1.2784`), and locked 2024-2025 is lower (OR `0.6543`, CI `0.4434-0.9655`). These runs demonstrate threshold/time sensitivity and cannot replace the frozen ≥50% full-period conclusion. |
| Secondary conditions | **Complete; none survives Holm correction** | Peat interactions with higher 72-hour VPD, higher 24-hour maximum wind, and lower pre-fire EVI have Holm p-values `1.000`, `0.425`, and `1.000`, respectively. Drainage was not silently substituted and remains a separately timed sensitivity. |
| Held-out prediction | **Better than uniform ranking, not causal** | A 2018-2022 development fit produced locked 2024-2025 conditional log loss `1.468` versus uniform `1.609`, top-1 recall `36.96%` versus uniform expectation `20%`, and MRR `0.605`. Top-5 recall is structurally 100% in five-cell sets and is explicitly non-informative. |
| Uncertainty and diagnostics | **Passed** | Models converged with two-way cell/date cluster-robust covariance; the primary information condition number is `32.43`. Results and all coefficients are in `outputs/analysis/phase2_environmental_results.json`; the readable report is `outputs/insights/phase2_environmental_association.md`. |
| Claim boundary | **Unchanged** | This is a within-matched-set detectable-fire association. Human access, deliberate burning, plantation profit, actor attribution, government performance, absolute ignition risk, burned area, and global transportability remain unestimated. |

## Execution update -- Phase 3 fire-to-land-cover registration and extraction (28 August 2026)

| Workstream | Status | Evidence / decision |
|---|---|---|
| Pre-outcome registration | **Frozen** | `config/phase3_registration.json` fixes a one-year primary outcome, 10% loss-of-pre-index-forest threshold, 5%/20% and two-/three-year sensitivities, within-set adjusted risk difference, cell/date clustered uncertainty, Holm-corrected destination families, support gates, and non-causal language before annual outcomes are extracted. |
| Official temporal support | **Verified** | The authenticated MapBiomas Indonesia Collection 4.1 asset exposes 35 annual classification bands for 1990-2024. One-year follow-up therefore admits fire years 2015-2023; two-year follow-up ends at 2022 and three-year follow-up at 2021. Fire years 2024-2025 are excluded for incomplete follow-up, not coded as no change. |
| Class crosswalk | **Frozen** | `config/mapbiomas_collection41_legend.json` records natural-forest codes 3/5/76 plus distinct destinations for non-forest natural vegetation, rice, oil palm, pulpwood, other agriculture, mining, urban, other non-vegetation, aquaculture, and water. A mapped destination is explicitly not actor or intent evidence. |
| Locked-cell linkage | **Complete** | All 70,455 opportunity rows, 14,091 exact 1:4 sets, and 18,664 unique cells were audited. Every locked cell resolved to one private EPSG:6933 1-km grid centre. The 1,022,093-byte private upload table hash is `987abd0d71c4c4c5c5e9e2e73640639f83b6217e33ec758312c280622bcbd70a`; the table is Git-ignored and excluded from the dashboard. |
| Zero-budget extraction | **Complete** | All 38 restart-safe Earth Engine chunks completed and were expanded into 307 registered coordinate-free transition fields for 18,664 unique cells. The 21,710,356-byte result has SHA-256 `ddd1e1498c31c7c8920749e64e916a98c3924affd457fe9768b2a3efb146fe4d`; no duplicate cell IDs or missing values were found. All 38 temporary coordinate-bearing assets were removed. The method used neither paid object storage nor a national raster-stack download. |
| Cloud access audit | **Passed** | The previously registered `susenas-project` is active, its Earth Engine API is enabled, `ee.Initialize(project='susenas-project')` returned `EARTH_ENGINE_OK`, and the MapBiomas Collection 4 asset metadata was readable. The unregistered `gen-lang-client-0127774774` project is not used. No credential values were recorded. |
| Phase 3 gate and primary model | **Passed; result estimated** | `phase3_ready=true`, `phase3_model_run=true`, and no blockers remain. Of 12,178 primary candidate sets, 7,138 exact 1:4 sets passed complete-set/support rules (35,690 rows; 11,758 cells). Fire-positive cells had 13.74% unadjusted risk versus 4.40% for controls; the registered adjusted risk difference was **+5.89 points** (95% CI **+4.52 to +7.25**, p=**2.63e-17**) using two-way cell/date cluster-robust uncertainty. |
| Registered robustness | **Passed direction check** | Results remained positive for ≥5% loss at one year (+10.78 points), ≥20% at one year (+2.76), ≥10% at two years (+5.93), and ≥10% at three years (+6.10); all reported intervals excluded zero. The continuous outcome was strongly right-skewed, so both mean and median/IQR are reported. |
| Exploratory destinations | **Estimated with support gates and Holm correction** | Non-forest natural vegetation (+4.68 points), oil palm (+0.34), other agriculture (+0.30), and other non-vegetated land (+0.86) passed the registered family correction. Rice, pulpwood, mining, urban, aquaculture, and water lacked adequate within-set support. No destination result identifies deliberate burning, actor, owner, legality, planting timing, or profit. |
| Reporting and UI | **Updated** | Machine-readable results, readable Phase 3 report, access audit, synthesis, method, README, and the coordinate-free dashboard now report the completed estimate, selection flow, robustness checks, exploratory destinations, and the same non-causal claim boundary. |
| Verification | **Passed** | The coordinate-free transition table passed row, column, uniqueness, missingness, and hash checks; all temporary assets were deleted. The full Python test suite and static Next.js production build were rerun after final reporting changes. |

## Execution update -- Phase 3 publication validation and release package (28 August 2026)

| Workstream | Status | Evidence / decision |
|---|---|---|
| Attrition audit | **Complete; material selection boundary** | Of 12,178 primary-eligible sets, 5,040 (41.4%) were excluded and 7,138 analysed. Pre-index natural forest below 70% affected 5,031 sets. The maximum included-versus-excluded absolute SMD was 1.020, so transportability is explicitly limited to the retained Kalimantan population. |
| Influence and estimator checks | **Complete; positive direction retained** | Removing the top 0.5% and 1% of matched sets by score norm yielded +5.63 and +5.50 points. Conditional logistic OR was 3.46; adjusted continuous loss-share difference was +2.93 points. These are sensitivities, not replacements for the registered risk difference. |
| Temporal and spatial checks | **Complete; heterogeneous but pooled direction stable** | Year-specific estimates ranged +0.61 to +9.75 points; all leave-one-year-out estimates were positive (+4.13 to +6.96). Block-plus-date 95% CIs excluded zero at 25, 50, and 100 km. |
| Negative control | **Positive; causal interpretation rejected** | The fully pre-index outcome was +2.31 points (95% CI +1.13 to +3.50; p=0.000131). The common-support post-minus-pre diagnostic was +3.08 points (95% CI +1.53 to +4.63), but parallel trends are not established. Baseline trajectory/residual confounding must be reported with the primary result. |
| Map accounting | **Passed internally** | Across 447,936 cell–horizon pairs, no loss-minus-destination mass residual exceeded 1e-8. This is not independent MapBiomas accuracy validation. |
| Publication package | **Technically complete** | Added manuscript, supplement, references, figures, tables, coordinate-free bundle builder, SHA-256 manifest, reproduction runner, code/data licence separation, citation metadata, and a self-contained HTML technical report. The local release ZIP is ignored by Git and excludes coordinates, credentials, raw rasters, and raw provider archives. |
| Remaining external metadata | **Human/editorial only** | Verified authors, affiliations, contributor roles, acknowledgements/funding, conflict and ethics wording, target-journal formatting, and a permanent repository/archive DOI remain before journal submission. They do not block reproducibility of the statistical result. |
| Public dashboard deployment | **Ready** | The coordinate-free Next.js static export is deployed at `https://indonesia-wildfire-analysis.vercel.app`; the production response returned HTTP 200. The deployment excludes raw research archives and private coordinates. Receipt: `outputs/quality/vercel_deployment.json`. |
| Git-based continuous deployment | **Connected and verified** | Vercel is connected to `Shiverion/indonesia-wildfire-analysis`, production branch `main`, with project root `apps/evidence-explorer`. Commit `64b6b7987d1e23d13fe646e7f86e76dc036802b9` automatically created production deployment `dpl_5DhUX2RgBXNPNpYU6g1ouGDzcAMe`, which reached `READY` and returned HTTP 200. |
| Cesium runtime repair | **Passed locally and in production** | The prior bundle never created a globe canvas because Cesium 1.144's embedded SPZ WebAssembly was re-emitted with invalid octal escapes. Commit `11b5c1d59bcf9953e723a0d1022a58adddbcbe8d` serves the validated Cesium UMD runtime separately, uses Webpack, and rejects syntactically invalid generated chunks during `postbuild`. Deployment `dpl_A8yfwL3iCJZwRyw7FsSwbQpsS4wq` reached `READY`; a fresh browser created two Cesium canvases, completed province geometry loading, and logged no warnings or errors. |

## Execution update -- unified public research report (28 August 2026)

| Workstream | Status | Evidence / decision |
|---|---|---|
| Public narrative | **Reorganized** | The Next.js dashboard now presents one integrated report instead of exposing research-stage labels: summary, primary forest-loss association, peat/climate mechanism result, Indonesia and global spatial context, Kalimantan detail, and methods/provenance. |
| Scientific substance | **Preserved** | Effect estimates, confidence intervals, robustness checks, attrition and negative-control cautions, destination tables, interactive maps, source attribution, missingness rules, and the non-causal claim boundary remain available. Only workflow-oriented public framing was removed. |
| Reader safeguards | **Strengthened** | The summary states the main association and the inconclusive peat × dryness result together, while explicitly separating descriptive maps from fitted model domains and rejecting inference about deliberate ignition, actor, ownership, legality, profit, or government performance. |
| Local and production verification | **Passed** | The Next.js production build, TypeScript check, static-page generation, and generated JavaScript syntax validation passed. Git commit `3a5b0930d60e2604039d2fb127845696a5175ab4` triggered Vercel deployment `dpl_CzrdnY4bVAWYHDhhQRR43515LtJn`, which reached `READY` and returned HTTP 200. A fresh production browser loaded both Cesium canvases, completed Indonesia province geometry loading, and showed no reader-facing Phase 1/2/3 labels, including the evidence-boundary dialog and collapsed methodology text. |

## Execution update -- prior-year AlphaEarth predictive ablation (29 August 2026)

| Workstream | Status | Evidence / decision |
|---|---|---|
| Pre-extraction registration | **Frozen** | `config/ppe_alphaearth_registration.json` fixes the prediction-only question, t−1 embedding rule, documented 2017–2024 source years, 2018–2022 development, 2023 rehearsal, one-time 2024–2025 locked test, metrics, L2 penalty grid, and non-causal claim boundary. |
| Leakage and provenance gate | **Passed** | All five required feature families passed. Same-calendar-year AlphaEarth and post-fire MapBiomas variables were deliberate negative controls and were rejected automatically. |
| Data-minimal extraction | **Complete** | Earth Engine returned 20,684 registered cell-year vectors in 83 restart-safe chunks. The final private table is approximately 19.8 MB, contains 64 normalized dimensions, and uses event year minus one throughout; no Indonesia-wide 10 m raster was downloaded. |
| Spatial-temporal validation | **Passed** | Model selection used deterministic 100-km positive-cell blocks and purged every training set sharing a recurring cell with its test fold. Development selected penalty 0.1 for embedding-only and combined models; 2023 rehearsal retained the improvement. |
| Locked 2024–2025 test | **Accessed once; predictive gain retained** | Across 1,913 exact sets, conditional log loss was 1.4671 explicit, 1.2708 embedding-only, and 1.2664 combined. Top-1 recall was 36.8%, 45.8%, and 46.7%; MRR was 0.605, 0.672, and 0.677. Combined improvement was 0.2006 (1,000-set-bootstrap 95% interval 0.1712–0.2310). |
| Interpretation | **Prediction only** | Prior-year embeddings add out-of-time ranking information beyond named covariates. They do not identify a mechanism, deliberate burning, actor, ownership, plantation benefit, motive, or government performance and do not replace the registered association models. |

## Execution update -- accountable research explanation layer and map correction (29 August 2026)

| Workstream | Status | Evidence / decision |
|---|---|---|
| Model role | **Restricted to explanation** | Kimi K2.5 is used only to explain one selected public evidence pack. It is not part of the statistical pipeline, cannot browse, has no raw-data retrieval path, and cannot change research outputs. |
| Pre-model controls | **Passed** | The server enforces valid section IDs, 600-character input limits, same-origin requests, prompt/secret/private-coordinate rejection, research-scope terms, a best-effort per-instance rate limit, and a two-request concurrency cap. An unrelated test was refused before any model call. |
| Post-model validation | **Passed fail-closed** | Structured final JSON is checked against the selected fact-ID whitelist. Unknown citations, uncited answers, malformed output, and numeric tokens absent from cited statements become the exact bounded refusal. Kimi reasoning content is discarded server-side. |
| Claim-boundary test | **Passed fail-closed** | A question attempting to attribute government intent and oil-palm expansion was not answered as an established finding; the public response stated that the research has not performed sufficient analysis. No citation or actor claim was fabricated. |
| Accountability receipt | **Implemented** | Each response reports model, prompt version, corpus hash, section and citation IDs, validator result, latency, token usage when supplied, and that this application did not store the raw question. The UI also discloses Moonshot processing. |
| Reader interaction | **Implemented** | Seven report sections have explicit `Ask AI` controls with an explanatory hover/focus tooltip. Each control opens the minimizable sidebar with a section-specific evidence pack, a clearly labelled set of three distinct suggested questions (including one plain-language explanation), loading/error/empty states, source chips, evidence boundaries, and the audit receipt. Changing section clears the conversation to prevent evidence bleed. The model follows the reader's question language; the report interface remains English. Mobile uses a bottom sheet. |
| Assistant launcher | **Implemented** | The persistent launcher is a compact logo-only floating action at the lower-right edge instead of a text tab occupying the map/report margin. It retains a descriptive accessible name, keyboard focus ring, hover/focus tooltip, tactile pressed state, and a smaller mobile-safe footprint. |
| Desktop density calibration | **Implemented** | The report's desktop composition is calibrated to the reader-preferred 90%-zoom density without applying CSS `zoom` or scaling the Cesium canvas. Maximum report width is 1,332 px (90% of the former 1,480 px), desktop rem sizing and major vertical spacing are reduced proportionally, and globe stages are 10% shorter. Mobile type and touch targets retain their safer sizes. |
| Directional navigation audit | **Passed locally** | The Kalimantan control now labels the earlier global-comparison section with an upward arrow, matching its actual smooth-scroll destination. The summary's main-finding control retains a downward arrow because that destination follows it in the document order. |
| Assistant preflight regression | **Passed locally** | Every displayed suggestion is explicitly allowlisted after the restricted-content check, so a generic section-aware prompt such as “What are the main findings?” cannot be rejected merely because it omits a fire-specific keyword. Unrelated free-form questions remain subject to the scope filter. |
| Visual regression fixes | **Passed locally** | Status badges use explicit high-contrast foreground colors that cannot be overridden by the base badge selector. The `Estimated association`, locked-test, inconclusive, and unavailable states were audited together rather than patched individually. |
| Province metric controls | **Corrected** | `Completed 2024` and `Peatland share` are country-only aggregates and are now hidden in Indonesia-province mode. The map displays `Province bundle: latest NRT only`; switching back to world countries restores all three controls. |
| Identity | **Implemented** | A new leaf/flame/data-orbit mark is stored as a transparent, scalable SVG and is used in the site header, assistant, and browser icon. |
| Production verification | **Passed locally** | Next.js built successfully with `/` prerendered and `/api/research-chat` dynamic. TypeScript and generated JavaScript syntax checks passed. The 22 browser static files contained zero occurrences of the Kimi secret value or variable name; a production server returned HTTP 200 and refused an unrelated API question before calling Kimi. |
| Deployment boundary | **Configuration documented** | Static export was removed because a public API key cannot be shipped to the browser. Vercel must keep the Next.js framework output and set `KIMI_API_KEY` as a server environment variable. No deployment was performed in this update. |

## Execution update -- hybrid public report architecture (29 August 2026)

| Workstream | Status | Evidence / decision |
|---|---|---|
| Main-page boundary | **Implemented** | `/` is now a research introduction only. It imports no result JSON and displays no statistical estimates, maps, source counts, or fitted conclusions. It presents the motivation, four research-question families, claim boundary, and reading paths. |
| Evidence grouping | **Implemented** | `/findings` contains the forest-loss association, peat-by-dryness analysis, and prior-year AlphaEarth predictive check. `/explore` contains Indonesia province context, global country comparison, Kalimantan layers, trend context, and the accessible province table. `/methods` contains source attribution, environmental validation audit, provenance ledger, missingness safeguards, and claim boundaries. |
| Navigation model | **Corrected** | Primary navigation now changes routes and exposes an active-page state. Hash anchors are used only for subsections on the current page, including global-to-Kalimantan movement inside `/explore`; this removes the earlier ambiguity between page navigation and vertical scrolling. |
| Assistant context | **Page-bounded** | Each route initializes the evidence assistant with its own pack. The introduction pack contains only research purpose, report organization, and scope boundaries, while findings, map, and method pages retain their existing evidence-specific suggestions and validated citation contracts. |
| Route payload boundary | **Implemented** | The introduction imports no research-result JSON. The methods client receives only readiness, provenance, limitations, ledger metadata, and the primary environmental result rather than the full map bundle; its prerendered HTML fell from approximately 638 kB during refactor QA to 36 kB. The full aggregate geometry context remains confined to `/explore`. |
| Build verification | **Passed locally** | TypeScript passed. Next.js generated static `/`, `/findings`, `/explore`, and `/methods` routes plus the dynamic `/api/research-chat` endpoint. The production build compiled successfully and all 25 generated JavaScript chunks passed the syntax validator. |
