"""Intersect paired VIIRS swaths with the frozen 1-km forest cohort.

This creates a diagnostic, not the canonical Phase 1B denominator.  The local
archive covers only a 2015 rehearsal window, so the output is deliberately
written as ``opportunity_frame_diagnostic.csv`` and marked ``denominator_ready:
false``.  It aggregates valid clear-land and fire pixels by pair/cell, then
applies the registered <=72-hour prior-negative rule where the available
rehearsal swaths permit it.
"""

from __future__ import annotations

import argparse
import gc
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PAIR_INDEX = ROOT / "outputs" / "quality" / "viirs_pair_index.json"
GRID_TIF = ROOT / "data" / "derived" / "mapbiomas" / "mapbiomas_c41_forest_fraction_1km_kalimantan.tif"
OUTPUT_CSV = ROOT / "data" / "derived" / "viirs" / "opportunity_frame_diagnostic.csv"
OUTPUT_REPORT = ROOT / "outputs" / "quality" / "viirs_opportunity_diagnostic.json"
BBOX = (109.0, -5.0, 120.0, 6.0)
FOREST_THRESHOLD = 0.70
MAX_PRIOR_HOURS = 72.0
CELL_SIZE = 1000.0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_grid(path: Path) -> tuple[np.ndarray, float, float]:
    from PIL import Image

    image = Image.open(path)
    values = np.asarray(image, dtype=np.float32)
    tiepoint = image.tag_v2.get(33922)
    scale = image.tag_v2.get(33550)
    if not tiepoint or not scale:
        raise ValueError("forest-fraction grid lacks GeoTIFF transform tags")
    left = float(tiepoint[3])
    top = float(tiepoint[4])
    return values, left, top


def _project_6933(lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Forward WGS84 -> EPSG:6933 CEA using the EPSG ellipsoidal formula."""

    a = 6378137.0
    e2 = 0.0066943799901413165
    e = math.sqrt(e2)
    standard_parallel = math.radians(30.0)
    m1 = math.cos(standard_parallel) / math.sqrt(1.0 - e2 * math.sin(standard_parallel) ** 2)
    lon_radians = np.deg2rad(lon.astype(np.float64))
    lat_radians = np.deg2rad(lat.astype(np.float64))
    sin_lat = np.sin(lat_radians)
    q = (1.0 - e2) * (
        sin_lat / (1.0 - e2 * sin_lat**2)
        - (1.0 / (2.0 * e)) * np.log((1.0 - e * sin_lat) / (1.0 + e * sin_lat))
    )
    return a * m1 * lon_radians, a * q / (2.0 * m1)


def _pair_rows(path: Path, limit: int | None) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = [row for row in payload.get("rows", []) if row.get("pair_status") == "paired"]
    rows.sort(key=lambda row: row["acquisition_utc"])
    return rows[:limit] if limit is not None else rows


def _aggregate_pair(row: dict[str, Any], grid: np.ndarray, grid_left: float, grid_top: float, chunk_rows: int) -> dict[str, Any]:
    try:
        import netCDF4
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise RuntimeError("netCDF4 is required for VIIRS opportunity processing") from exc

    # Keep HDF5/netCDF chunk caches bounded; these swaths are tens of millions
    # of pixels and the diagnostic is intentionally streamed one pair at a
    # time.
    netCDF4.set_chunk_cache(size=1024 * 1024, nelems=1024, preemption=0.75)
    Dataset = netCDF4.Dataset

    fire_path = ROOT / row["vnp14_path"]
    geo_path = ROOT / row["vnp03_path"]
    # Four int32 counters per 1-km cell: valid land, processed, positive,
    # negative.  This avoids creating a Python dict entry for every pixel.
    stats = np.zeros((grid.size, 4), dtype=np.int32)
    with Dataset(fire_path) as fire_ds, Dataset(geo_path) as geo_ds:
        # Avoid allocating a second boolean mask for every 256-row slice.
        # Fill values are filtered explicitly by the finite/range checks below.
        fire_ds.set_auto_mask(False)
        geo_ds.set_auto_mask(False)
        fire_var = fire_ds.variables["fire mask"]
        geo = geo_ds.groups["geolocation_data"]
        lat_var = geo.variables["latitude"]
        lon_var = geo.variables["longitude"]
        land_var = geo.variables["land_water_mask"]
        quality_var = geo.variables["quality_flag"]
        for variable in (fire_var, lat_var, lon_var, land_var, quality_var):
            try:
                variable.set_var_chunk_cache(size=1024 * 1024, nelems=1024, preemption=0.75)
            except AttributeError:
                pass
        if fire_var.shape != lat_var.shape:
            raise ValueError(f"fire/geolocation shape mismatch: {fire_var.shape} vs {lat_var.shape}")
        for start in range(0, fire_var.shape[0], chunk_rows):
            stop = min(fire_var.shape[0], start + chunk_rows)
            fire = np.asarray(fire_var[start:stop, :], dtype=np.uint8)
            lat = np.asarray(lat_var[start:stop, :], dtype=np.float32)
            lon = np.asarray(lon_var[start:stop, :], dtype=np.float32)
            land = np.asarray(land_var[start:stop, :], dtype=np.uint8)
            quality = np.asarray(quality_var[start:stop, :], dtype=np.uint8)
            finite = np.isfinite(lat) & np.isfinite(lon) & (lat > -90.0) & (lat < 90.0)
            in_bbox = finite & (lon >= BBOX[0]) & (lon <= BBOX[2]) & (lat >= BBOX[1]) & (lat <= BBOX[3])
            quality_land = in_bbox & (quality == 0) & (land == 1)
            if not quality_land.any():
                continue
            x, y = _project_6933(lon[quality_land], lat[quality_land])
            cols = np.floor((x - grid_left) / CELL_SIZE).astype(np.int64)
            rows = np.floor((grid_top - y) / CELL_SIZE).astype(np.int64)
            inside = (rows >= 0) & (rows < grid.shape[0]) & (cols >= 0) & (cols < grid.shape[1])
            if not inside.any():
                continue
            # Reconstruct the flattened fire class only for quality-passing
            # pixels, then retain the registered >=70% fixed forest cohort.
            fire_values = fire[quality_land][inside]
            cell_rows = rows[inside]
            cell_cols = cols[inside]
            fractions = grid[cell_rows, cell_cols]
            cohort = np.isfinite(fractions) & (fractions >= FOREST_THRESHOLD)
            if not cohort.any():
                continue
            fire_values = fire_values[cohort]
            cell_rows = cell_rows[cohort]
            cell_cols = cell_cols[cohort]
            cell_keys = cell_rows * grid.shape[1] + cell_cols
            unique_keys, inverse = np.unique(cell_keys, return_inverse=True)
            stats[unique_keys, 0] += np.bincount(inverse, minlength=unique_keys.size).astype(np.int32)
            stats[unique_keys, 1] += np.bincount(
                inverse, weights=np.isin(fire_values, (5, 7, 8, 9)).astype(np.int32), minlength=unique_keys.size
            ).astype(np.int32)
            stats[unique_keys, 2] += np.bincount(
                inverse, weights=np.isin(fire_values, (7, 8, 9)).astype(np.int32), minlength=unique_keys.size
            ).astype(np.int32)
            stats[unique_keys, 3] += np.bincount(
                inverse, weights=(fire_values == 5).astype(np.int32), minlength=unique_keys.size
            ).astype(np.int32)
    return {
        "pair_key": row["pair_key"],
        "acquisition_utc": row["acquisition_utc"],
        "stats": stats,
    }


def build_diagnostic(limit: int | None = None, chunk_rows: int = 128) -> dict[str, Any]:
    try:
        from PIL import Image  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Pillow is required to read the compact forest-fraction GeoTIFF") from exc
    if not PAIR_INDEX.is_file() or not GRID_TIF.is_file():
        raise FileNotFoundError("paired VIIRS index and 1-km MapBiomas grid are required")
    grid, grid_left, grid_top = _load_grid(GRID_TIF)
    pairs = _pair_rows(PAIR_INDEX, limit)
    last_negative_epoch = np.full(grid.size, np.nan, dtype=np.float64)
    output_rows: list[dict[str, Any]] = []
    candidate_rows = 0
    valid_rows = 0
    # Stream one swath at a time.  Holding all pair/cell dictionaries in an
    # ``aggregated`` list makes memory grow with the number of granules.
    for pair in pairs:
        item = _aggregate_pair(pair, grid, grid_left, grid_top, chunk_rows)
        acquired = datetime.fromisoformat(item["acquisition_utc"].replace("Z", "+00:00"))
        acquired_epoch = acquired.timestamp()
        candidate_keys = np.flatnonzero(item["stats"][:, 1] > 0)
        for cell_key in candidate_keys.tolist():
            valid_land, processed, positive, negative = [int(value) for value in item["stats"][cell_key]]
            if not processed:
                continue
            candidate_rows += 1
            prior_epoch = last_negative_epoch[cell_key]
            lookback_hours = (acquired_epoch - prior_epoch) / 3600.0 if np.isfinite(prior_epoch) else None
            valid_history = lookback_hours is not None and 0.0 <= lookback_hours <= MAX_PRIOR_HOURS
            if valid_history:
                cell_row = cell_key // grid.shape[1]
                cell_col = cell_key % grid.shape[1]
                fraction = float(grid[cell_row, cell_col])
                outcome = "positive" if positive else "negative"
                output_rows.append({
                    "opportunity_id": f"{item['pair_key']}:r{cell_row:04d}c{cell_col:04d}",
                    "pair_key": item["pair_key"],
                    "cell_id": f"r{cell_row:04d}c{cell_col:04d}",
                    "acquisition_utc": item["acquisition_utc"],
                    "outcome_status": outcome,
                    "valid_opportunity": True,
                    "forest_fraction": fraction,
                    "quality_pass": True,
                    "coverage_fraction": processed / valid_land if valid_land else 0.0,
                    "negative_lookback_hours": lookback_hours,
                    "processed_pixel_count": processed,
                    "positive_pixel_count": positive,
                    "negative_pixel_count": negative,
                })
                valid_rows += 1
            if negative:
                last_negative_epoch[cell_key] = acquired_epoch
        gc.collect()

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "opportunity_id", "pair_key", "cell_id", "acquisition_utc", "outcome_status",
        "valid_opportunity", "forest_fraction", "quality_pass", "coverage_fraction",
        "negative_lookback_hours", "processed_pixel_count", "positive_pixel_count", "negative_pixel_count",
    ]
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output_rows)
    report = {
        "schema_version": "viirs-opportunity-diagnostic/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "diagnostic_only_incomplete_study_window",
        "denominator_ready": False,
        "source": {
            "pair_index": PAIR_INDEX.relative_to(ROOT).as_posix(),
            "pair_index_sha256": _sha256(PAIR_INDEX),
            "forest_fraction_grid": GRID_TIF.relative_to(ROOT).as_posix(),
            "forest_fraction_grid_sha256": _sha256(GRID_TIF),
            "study_window": "2015 rehearsal swaths only",
        },
        "summary": {
            "paired_rows_requested": len(pairs),
            "candidate_pair_cell_rows": candidate_rows,
            "valid_prior_negative_rows": valid_rows,
            "positive_rows": sum(row["outcome_status"] == "positive" for row in output_rows),
            "negative_rows": sum(row["outcome_status"] == "negative" for row in output_rows),
            "forest_threshold": FOREST_THRESHOLD,
            "maximum_prior_negative_hours": MAX_PRIOR_HOURS,
        },
        "output": {
            "path": OUTPUT_CSV.relative_to(ROOT).as_posix(),
            "sha256": _sha256(OUTPUT_CSV),
        },
        "limitations": [
            "Only the locally available 2015 rehearsal swaths were processed; this cannot represent the registered 2015-2025 study window.",
            "This diagnostic does not unlock Phase 1B or replace the canonical opportunity_frame.csv.",
            "A final frame still requires complete science-quality swaths, event linkage, duplicate/orbit handling, and registered cloud/water/coverage rules across the full study window.",
        ],
    }
    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="process only the first N paired swaths")
    parser.add_argument("--chunk-rows", type=int, default=128)
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        raise SystemExit("--limit must be positive")
    if args.chunk_rows < 1:
        raise SystemExit("--chunk-rows must be positive")
    report = build_diagnostic(args.limit, args.chunk_rows)
    print(json.dumps({
        "status": report["status"],
        "denominator_ready": report["denominator_ready"],
        "paired_rows_requested": report["summary"]["paired_rows_requested"],
        "valid_prior_negative_rows": report["summary"]["valid_prior_negative_rows"],
        "output": report["output"]["path"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
