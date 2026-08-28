"""Screen paired S-NPP VIIRS swaths before constructing the opportunity frame.

This module reads the science-product arrays, but deliberately stops short of
calling pixels valid opportunities.  A true denominator still requires the
frozen baseline-forest footprint, the registered quality/cloud rules, and the
analysis-grid intersection.  The output is a swath-level QA summary only; it
contains no detection coordinates or raw pixel records.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np


DEFAULT_BBOX = (109.0, -5.0, 120.0, 8.0)
PRESPECIFIED_PROCESSED_OR_FIRE_CLASSES = (5, 7, 8, 9)
CLEAR_LAND_CLASS = 5
FIRE_CLASSES = (7, 8, 9)
LAND_WATER_CLEAR_LAND_CLASS = 1


def classify_observation_pixels(
    fire_mask: np.ndarray,
    latitude: np.ndarray,
    longitude: np.ndarray,
    quality_flag: np.ndarray,
    land_water_mask: np.ndarray,
    forest_fraction: np.ndarray,
    cell_id: np.ndarray,
    prior_negative_hours: np.ndarray,
    coverage_fraction: np.ndarray,
    *,
    pair_key: str,
    acquisition_utc: str,
    bbox: Sequence[float] = DEFAULT_BBOX,
    minimum_forest_fraction: float = 0.70,
    maximum_prior_negative_hours: float = 72.0,
) -> list[dict[str, Any]]:
    """Classify paired pixels into positive/negative opportunity rows.

    The caller must provide the frozen 2014 forest fraction, analysis-grid cell
    IDs, prior-negative lookback, and coverage fraction.  This function never
    infers those fields from a fire mask or from missing granules.  VNP14IMG
    classes follow the NASA VIIRS active-fire guide: class 5 is clear land and
    classes 7-9 are low/nominal/high-confidence fire; classes 0-4 and 6 are not
    valid observation opportunities.
    """

    arrays = {
        "fire_mask": np.asarray(fire_mask),
        "latitude": np.asarray(latitude),
        "longitude": np.asarray(longitude),
        "quality_flag": np.asarray(quality_flag),
        "land_water_mask": np.asarray(land_water_mask),
        "forest_fraction": np.asarray(forest_fraction, dtype=np.float32),
        "cell_id": np.asarray(cell_id),
        "prior_negative_hours": np.asarray(prior_negative_hours, dtype=np.float32),
        "coverage_fraction": np.asarray(coverage_fraction, dtype=np.float32),
    }
    shapes = {name: value.shape for name, value in arrays.items()}
    if len(set(shapes.values())) != 1:
        raise ValueError(f"observation arrays have incompatible shapes: {shapes}")
    if not 0 <= minimum_forest_fraction <= 1:
        raise ValueError("minimum_forest_fraction must be between 0 and 1")
    if not 0 <= maximum_prior_negative_hours:
        raise ValueError("maximum_prior_negative_hours must be non-negative")
    min_lon, min_lat, max_lon, max_lat = map(float, bbox)
    finite_geo = np.isfinite(arrays["latitude"]) & np.isfinite(arrays["longitude"])
    in_bbox = (
        finite_geo
        & (arrays["longitude"] >= min_lon)
        & (arrays["longitude"] <= max_lon)
        & (arrays["latitude"] >= min_lat)
        & (arrays["latitude"] <= max_lat)
    )
    forest_ok = np.isfinite(arrays["forest_fraction"]) & (arrays["forest_fraction"] >= minimum_forest_fraction)
    quality_ok = arrays["quality_flag"] == 0
    clear_land = arrays["land_water_mask"] == LAND_WATER_CLEAR_LAND_CLASS
    processed_class = np.isin(arrays["fire_mask"], PRESPECIFIED_PROCESSED_OR_FIRE_CLASSES)
    valid_history = (
        np.isfinite(arrays["prior_negative_hours"])
        & (arrays["prior_negative_hours"] >= 0)
        & (arrays["prior_negative_hours"] <= maximum_prior_negative_hours)
    )
    valid = in_bbox & forest_ok & quality_ok & clear_land & processed_class & valid_history
    positive = np.isin(arrays["fire_mask"], FIRE_CLASSES)
    negative = arrays["fire_mask"] == CLEAR_LAND_CLASS
    valid &= positive | negative

    rows: list[dict[str, Any]] = []
    for index in np.flatnonzero(valid):
        outcome = "positive" if positive.flat[index] else "negative"
        cell = str(arrays["cell_id"].flat[index])
        rows.append({
            "opportunity_id": f"{pair_key}:{cell}:{int(index)}",
            "pair_key": pair_key,
            "cell_id": cell,
            "acquisition_utc": acquisition_utc,
            "outcome_status": outcome,
            "valid_opportunity": True,
            "forest_fraction": float(arrays["forest_fraction"].flat[index]),
            "quality_pass": True,
            "coverage_fraction": float(arrays["coverage_fraction"].flat[index]),
            "negative_lookback_hours": float(arrays["prior_negative_hours"].flat[index]),
        })
    return rows


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _counts(values: np.ndarray) -> dict[str, int]:
    unique, counts = np.unique(np.asarray(values), return_counts=True)
    return {str(int(value)): int(count) for value, count in zip(unique, counts, strict=True)}


def summarize_arrays(
    fire_mask: np.ndarray,
    latitude: np.ndarray,
    longitude: np.ndarray,
    quality_flag: np.ndarray,
    land_water_mask: np.ndarray,
    *,
    bbox: Sequence[float] = DEFAULT_BBOX,
) -> dict[str, Any]:
    """Summarize one paired swath without producing a pixel-level table."""

    arrays = {
        "fire_mask": np.asarray(fire_mask),
        "latitude": np.asarray(latitude),
        "longitude": np.asarray(longitude),
        "quality_flag": np.asarray(quality_flag),
        "land_water_mask": np.asarray(land_water_mask),
    }
    shapes = {name: value.shape for name, value in arrays.items()}
    if len(set(shapes.values())) != 1:
        raise ValueError(f"paired swath arrays have incompatible shapes: {shapes}")
    if len(bbox) != 4:
        raise ValueError("bbox must be [min_lon, min_lat, max_lon, max_lat]")
    min_lon, min_lat, max_lon, max_lat = map(float, bbox)
    if not min_lon < max_lon or not min_lat < max_lat:
        raise ValueError("bbox bounds must be strictly increasing")

    finite = np.isfinite(arrays["latitude"]) & np.isfinite(arrays["longitude"])
    in_bbox = (
        finite
        & (arrays["longitude"] >= min_lon)
        & (arrays["longitude"] <= max_lon)
        & (arrays["latitude"] >= min_lat)
        & (arrays["latitude"] <= max_lat)
    )
    out_of_range = finite & (
        (arrays["latitude"] < -90)
        | (arrays["latitude"] > 90)
        | (arrays["longitude"] < -180)
        | (arrays["longitude"] > 180)
    )
    mask = arrays["fire_mask"]
    processed_or_fire = np.isin(mask, PRESPECIFIED_PROCESSED_OR_FIRE_CLASSES)
    return {
        "array_shape": list(mask.shape),
        "pixel_count": int(mask.size),
        "fire_mask_class_counts": _counts(mask),
        "quality_flag_counts": _counts(arrays["quality_flag"]),
        "land_water_mask_counts": _counts(arrays["land_water_mask"]),
        "finite_geolocation_pixels": int(finite.sum()),
        "bbox_geolocation_pixels": int(in_bbox.sum()),
        "out_of_range_geolocation_pixels": int(out_of_range.sum()),
        "prespecified_processed_or_fire_class_count": int(processed_or_fire.sum()),
        "prespecified_processed_or_fire_in_bbox_count": int((processed_or_fire & in_bbox).sum()),
        "opportunity_status": "screened_not_denominator_ready",
    }


def _load_pair_rows(pair_index_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = json.loads(pair_index_path.read_text(encoding="utf-8"))
    rows = [row for row in payload.get("rows", []) if row.get("pair_status") == "paired"]
    return payload, rows


def _summarize_pair(root: Path, row: dict[str, Any], bbox: Sequence[float]) -> dict[str, Any]:
    try:
        from netCDF4 import Dataset
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise RuntimeError("netCDF4 is required; install it in the analysis runtime") from exc

    vnp14_path = root / row["vnp14_path"]
    vnp03_path = root / row["vnp03_path"]
    with Dataset(vnp14_path) as vnp14, Dataset(vnp03_path) as vnp03:
        geo = vnp03.groups["geolocation_data"]
        summary = summarize_arrays(
            vnp14.variables["fire mask"][:],
            geo.variables["latitude"][:],
            geo.variables["longitude"][:],
            geo.variables["quality_flag"][:],
            geo.variables["land_water_mask"][:],
            bbox=bbox,
        )
    return {
        "pair_key": row["pair_key"],
        "acquisition_utc": row["acquisition_utc"],
        "vnp14_path": row["vnp14_path"],
        "vnp03_path": row["vnp03_path"],
        **summary,
    }


def build_summary(
    root: Path,
    *,
    pair_index_path: Path | None = None,
    output_csv: Path | None = None,
    output_json: Path | None = None,
    bbox: Sequence[float] = DEFAULT_BBOX,
    limit: int | None = None,
) -> dict[str, Any]:
    """Build the local swath-screening report for paired granules."""

    pair_index_path = pair_index_path or root / "outputs" / "quality" / "viirs_pair_index.json"
    output_csv = output_csv or root / "data" / "derived" / "viirs" / "viirs_swath_summary.csv"
    output_json = output_json or root / "outputs" / "quality" / "viirs_swath_summary.json"
    pair_index_payload, rows = _load_pair_rows(pair_index_path)
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be positive")
        rows = rows[:limit]

    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for row in rows:
        try:
            results.append(_summarize_pair(root, row, bbox))
        except Exception as exc:  # keep a complete audit of failed granules
            failures.append({"pair_key": row.get("pair_key", ""), "error": f"{type(exc).__name__}: {exc}"})

    payload = {
        "schema_version": "viirs-swath-screening/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "pair_index": pair_index_path.relative_to(root).as_posix(),
            "pair_index_sha256": _sha256(pair_index_path),
            "bbox": list(map(float, bbox)),
        },
        "summary": {
            "paired_rows_available": len(_load_pair_rows(pair_index_path)[1]),
            "paired_rows_requested": len(rows),
            "swaths_screened": len(results),
            "swaths_failed": len(failures),
            "negative_frame_ready": False,
            "denominator_ready": False,
        },
        "interpretation": {
            "status": "screening_only_no_forest_cohort_or_observation_denominator",
            "class_rule": "Classes 5 and 7-9 are retained as the prespecified processed/active-fire screening group; no class is converted into a negative observation here.",
            "required_next_step": "Intersect quality-screened geolocation with the frozen 2014 baseline-forest footprint and analysis grid, then apply registered cloud/water/coverage rules.",
        },
        "failures": failures,
        "rows": results,
    }
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "pair_key", "acquisition_utc", "array_shape", "pixel_count", "finite_geolocation_pixels",
        "bbox_geolocation_pixels", "out_of_range_geolocation_pixels",
        "prespecified_processed_or_fire_class_count", "prespecified_processed_or_fire_in_bbox_count",
        "opportunity_status", "vnp14_path", "vnp03_path",
    ]
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in results:
            writer.writerow({field: json.dumps(row[field]) if field == "array_shape" else row[field] for field in fields})
    output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    payload["outputs"] = {
        "csv": output_csv.relative_to(root).as_posix(),
        "quality_json": output_json.relative_to(root).as_posix(),
    }
    return payload
