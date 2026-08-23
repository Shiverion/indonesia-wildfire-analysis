# Data directories

Raw inputs are intentionally excluded from version control. Do not rename provider files after acquisition; record their SHA-256, retrieval time, licence/terms, and source URL in the manifest or generated quality report.

- `raw/enso/` — automatically downloaded NOAA CPC RONI source text.
- `raw/viirs/` — authenticated VNP14IMG.002/VNP03IMG.002 swaths after acquisition.
- `raw/era5_land/` — frozen CDS request outputs.
- `raw/mapbiomas_indonesia/` — frozen Collection 4.1 export and class crosswalk.
- `derived/enso/` — deterministic seasonal RONI table generated from `raw/enso/`.

Never treat a missing raw directory as zero exposure, zero fire, or evidence of no transformation.
