# Indonesia Wildfire Analysis

This repository implements a gated, reproducible research program for the Kalimantan human-accessibility, land-transformation, and wildfire hypothesis. It does not manufacture a human-fire result from open hotspot counts.

## Current outcome

The environmental daily-grid track has completed Phase 2. Its frozen primary test asks whether drier 72-hour root-zone soil changes the within-matched-set fire-detection gradient for cells with at least 50% mapped peat extent. The result is **inconclusive**: interaction odds ratio **0.866**, 95% CI **0.692–1.084**, two-sided **p=0.209**. This does not establish a stronger or weaker dryness interaction, and it is not proof of no effect.

A separately preregistered predictive robustness extension used 64-dimensional Google Satellite Embedding / AlphaEarth summaries from the **calendar year before** each opportunity. On the once-opened 2024–2025 locked test (1,913 exact matched sets), the combined explicit-plus-embedding model reduced conditional log loss from **1.4671 to 1.2664** and increased top-1 recall from **36.8% to 46.7%**. The log-loss improvement was **0.2006** (matched-set bootstrap 95% interval **0.1712–0.2310**). This establishes added out-of-time predictive information only; it does not identify what an embedding dimension represents or support causal claims about deliberate burning, plantations, actors, motives, or government performance.

Phase 3 is now **complete for the registered Kalimantan fire-to-land-cover association**. The wider Indonesia map is descriptive context only. All 38 zero-budget Earth Engine chunks completed, the validated coordinate-free table contains 18,664 unique 1-km cells and 307 registered transition fields, and all temporary coordinate-bearing cloud assets were removed. Among 7,138 complete exact 1:4 matched sets, fire-positive cells had an adjusted **+5.89 percentage-point** probability of losing at least 10% of pre-index natural forest within one year (95% CI **+4.52 to +7.25 points**, two-sided **p=2.63e-17**). This is a temporal association, not evidence of deliberate burning, actor, ownership, legality, or profit.

Publication diagnostics retain the positive direction under influence screening, conditional logistic regression, continuous loss share, leave-one-year-out analysis, and 25/50/100-km spatial clustering. They also identify two material constraints: **41.4%** of temporally eligible matched sets failed complete forest/observation support, and the pre-exposure negative control was positive (**+2.31 points**, 95% CI **+1.13 to +3.50**). That baseline difference indicates pre-existing land-change trajectory or residual confounding and rules out a causal reading of the main estimate.

The separate accessibility, land-transformation, actor-intent, plantation, and government-performance questions remain **NI -- not identifiable** because no validated dated exposure or intervention design is available. The environmental result must not be used as a substitute for those claims.

Open descriptive work has been completed separately:

- NOAA CPC RONI climate context, frozen with raw hash;
- anonymous GWIS aggregate monthly burned-area context through 2024; and
- a validated, sensor-stratified SiPongi portal-record archive for July-November 2015-2023.

Read the Phase 2 result in [phase2_environmental_association.md](outputs/insights/phase2_environmental_association.md), the [prior-year AlphaEarth predictive ablation](outputs/insights/ppe_alphaearth_predictive_ablation.md), the completed Phase 3 result in [phase3_fire_to_land_change.md](outputs/insights/phase3_fire_to_land_change.md), the [publication robustness audit](outputs/insights/phase3_publication_robustness.md), the broader evidence-bounded conclusion in [preliminary_synthesis.md](outputs/insights/preliminary_synthesis.md), and the audit trail in [PHASE_LOG.md](PHASE_LOG.md). The technical manuscript, supplement, final figures/tables, self-contained HTML report, citation file, licences, and coordinate-free release manifest are under [publication](publication/README.md).

An auxiliary, offline visual companion is available at [outputs/evidence-explorer/index.html](outputs/evidence-explorer/index.html). The maintained Next.js report uses a hybrid structure: `/` is an introduction without research results, `/findings` contains fitted statistical and predictive evidence, `/explore` contains the Indonesia/global maps and Kalimantan detail, and `/methods` contains validation, sources, provenance, and claim boundaries. Incompatible descriptive sources and the still-unidentified human track remain separate. No raw hotspot coordinates, private cell coordinates, or 1-km prediction surface are released.

The maintainable Next.js App Router version is in [apps/evidence-explorer](apps/evidence-explorer). It uses CesiumJS for a real WGS84 WebGL globe: a local NASA Blue Marble Earth surface plus frozen geoBoundaries ADM1 polygons are the actual clickable/hoverable geometry. The SiPongi current-five and GWIS legacy-four systems remain separate; legacy Kalimantan Timur is one documented topological union of current East and North Kalimantan, not two GWIS values. Run `npm install`, `npm run sync-globe-assets`, then `npm run dev` in that folder for local development; `npm run build` creates the production Next.js application. The build-time synchronizer accepts only the canonical aggregate bundle and refuses raw SiPongi records, sensitive location fields, and quarantined responses. The globe does not use Cesium Ion, live tile services, raw hotspot points, or a risk layer. An optional server-side Kimi K2.5 explainer is restricted to compact public evidence packs and validates citations and numeric claims before display; it has no retrieval access to the raw research archive.

The coordinate-free production dashboard is live at [fire-research.shiverion.com](https://fire-research.shiverion.com). Vercel receives only the app directory and aggregate browser assets; the raw research archive, private coordinates, and local analysis inputs are not uploaded.

Security concerns should be reported privately according to [SECURITY.md](SECURITY.md). Code is MIT-licensed; datasets, maps, imagery, and source marks retain the separate terms documented in [DATA_LICENSE.md](DATA_LICENSE.md).

## Run the pipeline

```powershell
$py = 'C:\Users\miqba\AppData\Local\Programs\Python\Python313\python.exe'

& $py scripts\research.py fetch-roni
& $py scripts\research.py fetch-gwis
& $py scripts\research.py build-sipongi --start-year 2015 --end-year 2023
& $py scripts\research.py report-enso
& $py scripts\research.py report-gwis
& $py scripts\research.py report-sipongi
& $py scripts\research.py report-synthesis
& $py scripts\research.py build-explorer
& $py analysis\phase2_environmental.py
& $py scripts\research.py condition-audit
& $py scripts\research.py validate
& $py scripts\research.py verify-ledger
& $py -m unittest discover -s tests -v
```

### Reproduce the publication result

```powershell
python scripts\build_publication_bundle.py
python scripts\reproduce_publication.py --include-dashboard
```

The first command creates a compact ignored ZIP from the two coordinate-free analysis inputs and writes a tracked SHA-256 manifest. It does not package raw rasters, raw provider archives, credentials, or private cell coordinates. The second command verifies those hashes, reruns Phase 3 and all publication diagnostics, executes the complete Python suite, and builds the Next.js dashboard.

### Zero-budget mode (current execution policy)

The active execution policy is documented in [ZERO_BUDGET_PLAN.md](ZERO_BUDGET_PLAN.md)
and frozen in `config/zero_budget_pilot_2015.json`. Do not start a full
2015–2025 CHIRPS, MOD13Q1, or VIIRS archive download for this pilot. Check the
local inventory before any acquisition:

```powershell
python scripts\inventory_raw_sources.py
```

The pilot keeps only event-level derived tables locally and samples missing
rasters remotely where possible. A complete ten-year analysis remains a
separate, currently unfunded scope.

### Download the registered NASA and CDS inputs

Keep both account credentials local; never paste them into chat, a notebook, or a command line. The repository now includes resumable, hashed download helpers:

1. Install the clients:

```powershell
python -m pip install earthaccess cdsapi
```

2. Authenticate NASA Earthdata once on this machine. `earthaccess` opens the Earthdata login flow and stores a local credential entry; it does not write the password into this repository:

```powershell
python -c "import earthaccess; earthaccess.login(strategy='interactive', persist=True)"
```

Run a one-granule smoke test before requesting the large archive. VNP14 is searched through CMR; its matching VNP03 geolocation granule is resolved from the official LAADS archive using the same `YYYYDDD.HHMM` acquisition stamp.

```powershell
python scripts\download_earthdata.py viirs --start 2015-01-01 --end 2015-01-31 --limit 1 --dry-run
python scripts\download_earthdata.py viirs --start 2015-01-01 --end 2015-01-31 --limit 1
```

If LAADS returns `403 ... profile ... Organization`, open [your NASA Earthdata profile](https://urs.earthdata.nasa.gov/profile), complete the required organization/affiliation field truthfully, save the profile, and rerun the same command. A successful Earthdata login can access LP DAAC VNP14 while LAADS still rejects the VNP03 request until this profile requirement is satisfied.

When that succeeds, request the staged inputs (start with 2015 calibration; do not begin with the entire multi-year archive):

```powershell
python scripts\download_earthdata.py viirs --start 2015-01-01 --end 2015-12-31
python scripts\download_earthdata.py mod13q1 --start 2015-01-01 --end 2015-12-31
python scripts\download_earthdata.py hls --start 2015-01-01 --end 2015-12-31
```

CHIRPS v3 is anonymous and does not use either account. Start with a one-day smoke test, then expand the date range in batches:

```powershell
python scripts\download_chirps.py --start 2015-01-01 --end 2015-01-01
python scripts\download_chirps.py --start 2015-01-01 --end 2015-01-31
```

3. In the CDS profile, either copy the credentials block shown under **API access** into the local file `C:\Users\<you>\.cdsapirc`, or keep the existing project `.env` with `cds_api_key` (plus `url`/`key` if present). The downloader reads the project `.env` without printing or recording the secret. Do not commit either credential file. Test the request shape first, then download one month:

```powershell
python scripts\download_era5_land.py --year 2015 --month 01 --dry-run
python scripts\download_era5_land.py --year 2015 --month 01
```

Each ERA5 request is one month and can be resumed independently. After the first month is verified, add months explicitly, for example:

```powershell
python scripts\download_era5_land.py --year 2015 --month 01 --month 02 --month 03 --month 04
```

The study-window downloader now retries terminal CDS month-job failures automatically and writes `.part` files before atomically finalizing NetCDF payloads. The defaults are two month-level resubmissions with a 30-second delay; override them explicitly when needed:

```powershell
python scripts\download_era5_study_window.py --start-year 2016 --end-year 2025 --request-retries 2 --retry-delay-seconds 30
```

After the local CHIRPS support window is present, derive the complete source-grid antecedent cache with:

```powershell
python scripts\research.py build-chirps-lags
```

This writes `data/derived/chirps/chirps_lag_features_2015.parquet` for cutoffs with complete 1/7/30/90-day support. It is an internal cache only: because the current CHIRPS archive covers 2015 July-November, it does not unlock Phase 1B or substitute for event linkage.

The helpers write a manifest and SHA-256 receipts under `data/raw/viirs/`, `data/raw/mod13q1/`, `data/raw/hls/`, and `data/raw/era5_land/`. After any download, run:

```powershell
python scripts\research.py condition-audit
python scripts\research.py phase1b-audit
python scripts\research.py validate
python scripts\freeze_peat_sensitivity.py
```

These downloads alone do not pass Phase 1: the VIIRS science swaths still need an observation-opportunity/negative frame, vegetation must be linked to every event's pre-event cutoff across 2015-2025, and dated access remains a separate gate. The local MOD13Q1 QA extraction can be reproduced with `C:\Users\miqba\AppData\Local\Programs\Python\Python313\python.exe scripts\build_mod13q1_prefire_features.py`; it currently produces a 2015 tile/composite summary only.

The pure pre-fire covariate helpers in `src/wildfire_research/covariates.py` are already testable while acquisition continues: they compute VPD and wind speed, require complete daily lag support, and reject look-ahead intervals. `freeze_peat_sensitivity.py` records hashes for the current global peat raster and 2017 drainage sensitivity archive; it intentionally cannot unlock a model.

To audit the downloaded S-NPP granules before pixel decoding, build the deterministic acquisition-pair index:

```powershell
python scripts\build_viirs_pair_index.py
```

This confirms VNP14/VNP03 acquisition-stamp pairing and writes `data/derived/viirs/viirs_pair_index.csv` plus a quality receipt. It intentionally reports `denominator_ready: false`: a missing VNP14 file is never treated as a negative observation. The true denominator requires decoding VNP03 geolocation and both products' quality/status arrays, then retaining only valid observed pixels on the analysis grid.

The pixel classifier is implemented in `src/wildfire_research/viirs_opportunity.py`. It requires a frozen 2014 forest fraction, analysis-grid cell IDs, a prior-negative lookback, and coverage fraction supplied by the upstream linker. It follows the official VNP14IMG mask legend: class 5 is clear land, classes 7-9 are fire, and classes 0-4/6 are not valid opportunities ([NASA VIIRS active-fire user guide](https://viirsland.gsfc.nasa.gov/PDF/VIIRS_activefire_User_Guide.pdf)). Missing forest/history inputs fail closed; they are never inferred from the fire mask.

The MapBiomas hand-off is now explicit and locally testable. Register through the official Landy/GEE workflow, run `scripts/mapbiomas_collection41_export.js` in the Earth Engine Code Editor after inserting the exact Collection 4.1 asset ID, and place the original 2014 class GeoTIFF plus `class_crosswalk.json` and `mapbiomas_2014_provenance.json` under `data/raw/mapbiomas_indonesia/`. Then run:

```powershell
python scripts\research.py mapbiomas-preflight
```

The preflight checks collection/year identity, source metadata, the Kalimantan footprint, raster readability, and an explicit natural-forest legend crosswalk. It does not guess class codes and it never treats a Collection 4 export as Collection 4.1. The result is recorded at `outputs/quality/mapbiomas_2014_preflight.json`; a failing preflight keeps Phase 1B and the VIIRS denominator locked.

After the preflight passes, build the compact Kalimantan mask used for forest-fraction extraction:

```powershell
python scripts\build_mapbiomas_forest_mask.py
```

This reads the country-wide GeoTIFF in 512-pixel windows and writes `data/derived/mapbiomas/mapbiomas_c41_natural_forest_mask_2014_kalimantan.tif` plus `outputs/quality/mapbiomas_2014_forest_mask.json`. A mask value of 1 is limited to Collection 4.1 classes 3, 5, and 76; it is not a fire map and does not by itself create a VIIRS denominator.

Aggregate that mask to the registered, origin-anchored 1-km analysis grid with:

```powershell
python scripts\build_mapbiomas_1km_grid.py
```

The output is an EPSG:6933 GeoTIFF with an area-weighted forest fraction per cell. The primary cohort threshold is `>= 0.70`; the report also retains a `>= 0.50` sensitivity count. This is still a fixed landscape cohort, not a processed-observation denominator.

Once paired S-NPP swaths are present, the bounded rehearsal intersection can be run with `python scripts\build_viirs_opportunity_diagnostic.py`. It writes a 2015-only diagnostic receipt, not the canonical opportunity frame; the large row-level CSV is intentionally local and ignored by Git.

### Zero-budget environmental Phase 1B track

The environmental-condition module no longer requires downloading complete global VIIRS geolocation, CHIRPS, or MOD13Q1 archives. Its frozen registration is `config/phase2_registration.json` and uses the official daily 1-km `NASA/VIIRS/002/VNP14A1` FireMask in Earth Engine. Class 5 is a valid land negative, classes 7-9 are positive, and classes 0-4/6 are excluded. A case must have a valid prior negative within three days, at least 50% processed prior support, and no fire in the prior seven days. Each baseline-forest case is matched to four reusable controls within 25 km.

Phase 1B is complete for this environmental track: 1,683/1,683 registered days have receipts, the locked frame contains 14,091 exact 1:4 matched sets, all annual support gates pass, and the immutable lock verifies. Phase 2's pre-fit transform check then found one control carrying the CHIRPS missing sentinel `-9999`; its entire five-row matched set was excluded without imputation, leaving 14,090 sets in the model.

Run the frozen Phase 2 specification and all mandatory sensitivities with:

```powershell
python analysis\phase2_environmental.py
```

The result is written to `outputs/analysis/phase2_environmental_results.json`, the readable report to `outputs/insights/phase2_environmental_association.md`, and a compact coordinate-free bundle to `apps/evidence-explorer/data/phase2-environmental.json`.

### Phase 3 fire-to-land-cover-change extension

Phase 3 is frozen in `config/phase3_registration.json`. Its primary outcome is loss of at least 10% of the natural-forest area still present in the year before the index fire season, measured one annual map later. Five-/20-percent thresholds and two-/three-year follow-up are sensitivities. Destination classes—including oil palm, pulpwood, agriculture, mining, and non-forest natural vegetation—are separate exploratory transitions, never proof of actor or intent.

The registered model is complete. It retained 7,138 of 12,178 candidate complete-follow-up matched sets (35,690 rows; 11,758 unique cells) and estimated an adjusted risk difference of **+5.89 percentage points** (95% CI **+4.52 to +7.25**, p=**2.63e-17**). The direction is robust at 5% and 20% forest-loss thresholds and at two- and three-year horizons. Exploratory Holm-corrected destination associations include non-forest natural vegetation (+4.68 points), oil palm (+0.34 points), other agriculture (+0.30 points), and other non-vegetated land (+0.86 points); several rarer destinations failed the frozen support gate. These sequences do not identify why a fire occurred or who benefited.

Prepare or re-audit the private cell upload and gate with:

```powershell
python analysis\phase3_land_change.py --prepare-private-cells
```

This writes a private, Git-ignored table for exactly 18,664 locked cells. The validated zero-budget runner uses the already registered `susenas-project`, submits small restart-safe transition-histogram chunks, downloads only coordinate-free fractions, removes temporary private assets, and runs the registered model automatically:

```powershell
python analysis\export_phase3_earthengine.py --wait
```

The Earth Engine access probe, live chunk counts, retries, and final output hash are recorded without credentials in `outputs/quality/phase3_cloud_access_audit.json` and `outputs/quality/phase3_earthengine_export.json`. Re-running the command resumes submitted tasks after an interruption. The zero-budget design intentionally avoids paid object storage and the full national annual raster stack. `analysis/mapbiomas_phase3_export.js` remains a reference fallback only because a single full-size Code Editor export can exceed Earth Engine's computed-value limit.

Confirmed gaps in the VNP14A1 source archive are handled without lowering the registered 80% annual-support gate. A missing VNP14A1 event day is excluded as no observation. For missing lookback history only, the registered amendment fuses NASA science-quality Terra MOD14A1.061 and Aqua MYD14A1.061 fire masks; those products cannot define the event-day outcome. Receipts list every fallback-history date, and Phase 2 must retain an exclusion sensitivity.

Earth Engine computes daily VIIRS eligibility, pre-event CHIRPS 1/7/30/90-day rainfall, and QA-valid pre-event MOD13Q1 EVI. Local processing then applies the frozen MapBiomas 2014 forest fraction (`>=0.70`), the hashed peat stratum, and exact hourly ERA5-Land 24/72-hour features. It stores only selected cases/controls, not the source rasters. The older VNP14IMG/VNP03IMG swaths remain a measurement sensitivity and do not block this environmental track.

Run or resume the registered extraction and inspect progress with:

```powershell
python scripts\build_gee_daily_risk_sets.py
python scripts\monitor_daily_risk_sets.py
python scripts\finalize_daily_risk_sets.py
python scripts\research.py phase1b-audit
python scripts\research.py lock-test
python scripts\research.py phase1b-audit
```

`scripts/complete_phase1b_pipeline.py` supervises the currently parallelized extraction, reattempts any missing day, finalizes ERA5 features, creates/verifies the immutable lock, and refreshes the explorer. Phase 1B can certify the environmental association track without pretending that the separate human-access, actor-intent, or governance tracks are ready.

### Commands

```text
fetch-roni             Download, hash, and parse NOAA CPC RONI
build-enso             Rebuild the RONI table from a local raw file
fetch-gwis             Download/hash/filter the anonymous GWIS aggregate archive
report-enso            Write the non-causal ENSO context report
report-gwis            Write the GWIS burned-area/ENSO context report
fetch-sipongi          Download/resume validated SiPongi portal chunks
build-sipongi          Assemble a complete monthly-preferred local SiPongi archive
report-sipongi         Write the sensor-stratified SiPongi context report
report-synthesis       Write the cross-source, evidence-bounded insight report
build-explorer         Write the offline, aggregate-only Phase 0.5 Evidence Explorer
condition-audit        Audit local peat x dryness/drainage/vegetation inputs without network calls
temporal-qa            Audit registered date support and VIIRS swath screening without network calls
phase1b-audit          Close Phase 1B temporal and observation-denominator gates without network calls
mapbiomas-preflight    Validate the frozen MapBiomas Indonesia C4.1 2014 export and class crosswalk
validate               Check configuration, manifest, payload, and provenance gates
log-phase              Append a hash-linked phase-ledger record
verify-ledger          Verify phase-ledger integrity
lock-test              Refuse or create an immutable test-input lock after Phase 1
verify-test-lock       Check the locked-test inventory
```

`fetch-sipongi` treats a nonmatching province, malformed schema, impossible coordinate, out-of-period date, or unexpected JSON as a hard failure. Bad provider responses are moved to `data/raw/sipongi/_rejected/` with a receipt; they are not converted into zeroes or included in analysis.

## Required inputs for the still-blocked human-access track

The central human-access and transformation analysis remains correctly blocked until these are local, frozen, and validated. This does not reverse the completed environmental Phase 2 result:

### Research modules and priority

The current evidence is organized into four separate modules rather than one broad causal claim:

1. **Environmental conditions (Phase 2 complete):** the primary peat × root-zone dryness interaction is inconclusive; VPD, wind, and EVI condition tests are also inconclusive after their registered correction. Drainage and ENSO interactions require separate registrations.
2. **Fire followed by land-cover change (Phase 3 complete):** the registered model estimates a +5.89-point adjusted difference in one-year ≥10% natural-forest loss after fire detection (95% CI +4.52 to +7.25; p=2.63e-17). Threshold and horizon sensitivities retain the direction. This is an association only; the small mapped oil-palm destination association cannot identify deliberate ignition, an actor, ownership, legality, or profit.
3. **Governance and actor attribution (Phase 4):** postponed until dated intervention, permit, ownership, enforcement, and restoration records exist.
4. **Global replication (Phase 5; descriptive preparation in Phase 0.5):** the current globe is context-only until outcomes, periods, sensors, area offsets, and observation denominators are harmonized.

This ordering is recorded in `ENHANCED_RESEARCH_METHOD.md` and the generated preliminary synthesis. A descriptive global map does not unlock the Indonesian causal or association modules.

1. S-NPP VIIRS `VNP14IMG.002` paired with `VNP03IMG.002` science swaths, including processed/non-detection opportunities.
2. ERA5-Land request(s) for wind, VPD, soil water, and weather support, plus final CHIRPS rainfall inputs.
3. MapBiomas Indonesia Collection 4.1 2014 baseline forest and lagged transformation export with a fixed class crosswalk.
4. Prefire vegetation: QA-valid MOD13Q1.061 EVI, with HLS NDMI as a sensitivity. Dynamic vegetation is a possible mediator and is excluded from the total-accessibility and current-transformation estimands.
5. Dated historical road/settlement assets. Archived OSM snapshots are only a mapped-network sensitivity, not proof of road construction timing.
6. Frozen peat strata and any drainage source used; a 2017 canal map cannot be backdated to 2014.

The manifest at [data/manifests/assets.json](data/manifests/assets.json) records access class, expected local location, terms, and provenance state for each source.

## Important data boundaries

- RONI is an ENSO state/index, not an "El Nino wave." Its main effect is conditioned out of an exact-overpass matched set; it is used in a separate panel or exploratory interaction role.
- GWIS is an aggregate monthly burned-area/count product, not individual events or 2025 coverage.
- SiPongi provides positive portal records only. It has no swath denominator, validated UTC time, forest mask, or event linkage. Its all-platform counts change when S-NPP and NOAA-20 enter the portal, so the records must be stratified by satellite.
- MapBiomas Indonesia C4.1 is publicly licensed and supports annual maps through 2024. The compact Phase 3 export now uses the correctly registered free `susenas-project`; do not substitute another collection, treat the 2014 baseline as a longitudinal outcome, or code missing 2025-2026 follow-up as no change.

## Layout

- `config/study.json` - frozen design choices.
- `data/manifests/assets.json` - source/access/provenance register.
- `data/raw/` - provider responses; do not hand-edit.
- `data/derived/` - reproducible intermediate tables.
- `outputs/quality/` - acquisition and validation reports.
- `outputs/analysis/` - machine-readable model results plus fail-closed phase-status artifacts when an outcome gate is not ready.
- `outputs/insights/` - bounded descriptive findings.
- `analysis/` - post-lock statistical code kept outside the immutable Phase 1B input inventory.
- `outputs/evidence-explorer/` - self-contained offline visual explorer and its aggregate JSON bundle.
- `outputs/ledger/` - hash-linked phase evidence.
- `outputs/locks/` - immutable pre-unlock input archives.
- `src/wildfire_research/` - standard-library pipeline.
