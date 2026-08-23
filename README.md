# Indonesia Wildfire Analysis

This repository implements a gated, reproducible research program for the Kalimantan human-accessibility, land-transformation, and wildfire hypothesis. It does not manufacture a human-fire result from open hotspot counts.

## Current outcome

The central accessibility and transformation question is currently **NI -- not identifiable**. The primary 1 km matched-overpass design cannot run until its science-quality fire, observation-opportunity, vegetation, climate, and dated-exposure inputs have all passed the Phase 1 gates.

Open descriptive work has been completed separately:

- NOAA CPC RONI climate context, frozen with raw hash;
- anonymous GWIS aggregate monthly burned-area context through 2024; and
- a validated, sensor-stratified SiPongi portal-record archive for July-November 2015-2023.

Read the evidence-bounded conclusion in [preliminary_synthesis.md](outputs/insights/preliminary_synthesis.md) and the audit trail in [PHASE_LOG.md](PHASE_LOG.md).

An auxiliary, offline visual companion is available at [outputs/evidence-explorer/index.html](outputs/evidence-explorer/index.html). Its central view is a dependency-free interactive orthographic globe: drag/touch to rotate, scroll/pinch to zoom, click generalized provincial aggregate anchors to inspect them, and use keyboard controls or the semantic province table as an alternative. It displays only pre-aggregated descriptive data, keeps the incompatible GWIS legacy-four and SiPongi current-five geographies separate, and prominently retains the `NI -- not identifiable` conclusion. The anchors are not raw hotspots or verified province boundaries; it is not a risk map, a causal model, or a substitute for the primary analysis.

The maintainable Next.js App Router version is in [apps/evidence-explorer](apps/evidence-explorer). It now uses CesiumJS for a real WGS84 WebGL globe: a local NASA Blue Marble Earth surface plus frozen geoBoundaries ADM1 polygons are the actual clickable/hoverable geometry. The SiPongi current-five and GWIS legacy-four systems remain separate; legacy Kalimantan Timur is one documented topological union of current East and North Kalimantan, not two GWIS values. Run `npm install`, `npm run sync-globe-assets`, then `npm run dev` in that folder for local development; `npm run build` writes the deployable export to `apps/evidence-explorer/out/`. The build-time synchronizer accepts only the canonical aggregate bundle and refuses raw SiPongi records, sensitive location fields, quarantined 2024 responses, a Phase 1-ready state, or any conclusion other than `NI -- not identifiable`. The globe does not use Cesium Ion, live tile services, raw hotspot points, or a risk layer.

## Run the pipeline

```powershell
$py = 'C:\Users\miqba\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'

& $py scripts\research.py fetch-roni
& $py scripts\research.py fetch-gwis
& $py scripts\research.py build-sipongi --start-year 2015 --end-year 2023
& $py scripts\research.py report-enso
& $py scripts\research.py report-gwis
& $py scripts\research.py report-sipongi
& $py scripts\research.py report-synthesis
& $py scripts\research.py build-explorer
& $py scripts\research.py condition-audit
& $py scripts\research.py validate
& $py scripts\research.py verify-ledger
& $py -m unittest discover -s tests -v
```

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

The helpers write a manifest and SHA-256 receipts under `data/raw/viirs/`, `data/raw/mod13q1/`, `data/raw/hls/`, and `data/raw/era5_land/`. After any download, run:

```powershell
python scripts\research.py condition-audit
python scripts\research.py validate
```

These downloads alone do not pass Phase 1: the VIIRS science swaths still need an observation-opportunity/negative frame, vegetation must pass QA and pre-event timing checks, and dated access remains a separate gate.

To audit the downloaded S-NPP granules before pixel decoding, build the deterministic acquisition-pair index:

```powershell
python scripts\build_viirs_pair_index.py
```

This confirms VNP14/VNP03 acquisition-stamp pairing and writes `data/derived/viirs/viirs_pair_index.csv` plus a quality receipt. It intentionally reports `denominator_ready: false`: a missing VNP14 file is never treated as a negative observation. The true denominator requires decoding VNP03 geolocation and both products' quality/status arrays, then retaining only valid observed pixels on the analysis grid.

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
validate               Check configuration, manifest, payload, and provenance gates
log-phase              Append a hash-linked phase-ledger record
verify-ledger          Verify phase-ledger integrity
lock-test              Refuse or create an immutable test-input lock after Phase 1
verify-test-lock       Check the locked-test inventory
```

`fetch-sipongi` treats a nonmatching province, malformed schema, impossible coordinate, out-of-period date, or unexpected JSON as a hard failure. Bad provider responses are moved to `data/raw/sipongi/_rejected/` with a receipt; they are not converted into zeroes or included in analysis.

## Required Phase 1 inputs

The primary analysis remains correctly blocked until these are local, frozen, and validated:

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
- MapBiomas Indonesia C4.1 is publicly licensed but needs free Google Earth Engine access; do not silently substitute Collection 4.

## Layout

- `config/study.json` - frozen design choices.
- `data/manifests/assets.json` - source/access/provenance register.
- `data/raw/` - provider responses; do not hand-edit.
- `data/derived/` - reproducible intermediate tables.
- `outputs/quality/` - acquisition and validation reports.
- `outputs/insights/` - bounded descriptive findings.
- `outputs/evidence-explorer/` - self-contained offline visual explorer and its aggregate JSON bundle.
- `outputs/ledger/` - hash-linked phase evidence.
- `outputs/locks/` - immutable pre-unlock input archives.
- `src/wildfire_research/` - standard-library pipeline.
