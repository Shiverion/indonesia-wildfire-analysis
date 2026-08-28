# Zero-budget execution plan

The project now uses a hard zero-budget rule: no S3, Backblaze, Cloudflare R2,
paid VM, or paid Earth Engine tier. Large provider archives are not required to
run the pilot and must not be downloaded locally by default.

## Why the three archives are large

- **CHIRPS** is a global daily raster. A single day is a complete global grid,
  not just Kalimantan; a ten-year request means thousands of global rasters.
- **MOD13Q1** is a 250 m, 16-day product distributed as multiple tiles. Each
  tile includes metadata, quality layers, and the full tile footprint even when
  only a small study region is needed.
- **VIIRS VNP14/VNP03** is a swath archive. VNP14 contains fire masks while
  VNP03 contains geolocation and observation-quality arrays; pairing many
  overpasses multiplies the number of large NetCDF files.

The local inventory is the authoritative size check. It currently reports about
47.10 GiB for these three source folders; this is not three small regional
tables. It is a partial archive containing provider-native global tiles/swaths.

## What is implemented

1. `config/zero_budget_pilot_2015.json` preserves the original one-year pilot; `config/phase2_registration.json` now freezes the full 2015-2025 environmental daily-grid track.
2. `scripts/inventory_raw_sources.py` records file counts, byte totals, and a
   60 GiB hard stop in `outputs/quality/raw_source_inventory.json`.
3. Full-download jobs remain stopped. No raw files are deleted.
4. VNP14A1 opportunity, CHIRPS lags, and MOD13Q1 EVI are obtained by risk-set-level Earth Engine computation only; only derived case/control Parquet chunks are retained locally.
5. `scripts/build_gee_daily_risk_sets.py` runs the full registered years resumably; `scripts/finalize_daily_risk_sets.py` joins local ERA5-Land and refuses certification until every day and covariate gate passes.
6. The older pilot scripts remain descriptive calibration evidence and cannot unlock Phase 2.

## Storage relocation

The active `data/raw` path in the repository is now a Windows junction to
`D:\projects\Indonesia Wildfire Analysis\data\raw`. The move was verified at
6,456 files and 62,845,738,404 bytes (58.53 GiB) before the temporary C: copy
was sent to the Recycle Bin. Existing scripts continue to use the repository
path; the payloads physically live on D:.

## Scientific boundary

The full registered environmental track can estimate whether first-observed
daily fire risk varies with antecedent weather, vegetation stress, and static
peat extent in baseline forest. It still cannot identify peat drainage state,
actor, motive, plantation beneficiary, government performance, road-opening
effects, or global generalisation. Those claims require their own dated inputs,
registration, and gate review—not paid storage alone.
