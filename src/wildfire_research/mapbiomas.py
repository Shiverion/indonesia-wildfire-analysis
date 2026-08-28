"""Fail-closed validation for the MapBiomas Indonesia 2014 baseline export.

The research protocol needs a *frozen* land-cover export and an explicit class
crosswalk before VIIRS pixels can be restricted to baseline natural forest.
This module deliberately does not guess MapBiomas class codes or a Google
Earth Engine asset ID.  It validates the small, reviewable hand-off produced
by the official MapBiomas Landy/GEE workflow and writes an actionable report
when that hand-off has not happened yet.
"""

from __future__ import annotations

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import logical_relative


MAPBIOMAS_FAQ_URL = "https://landy.mapbiomas.id/en/faq"
MAPBIOMAS_GEE_URL = "https://landy.mapbiomas.id/en/gee"
MAPBIOMAS_DOWNLOAD_URL = "https://landy.mapbiomas.id/en/downloads"
MAPBIOMAS_LEGEND_URL = "https://landy.mapbiomas.id/en/legendcode"
COLLECTION = "4.1"
BASELINE_YEAR = 2014
# The ERA5 request uses a padded climate bbox reaching 8 N.  The actual
# Indonesian Kalimantan baseline is covered by the Indonesia land-cover
# raster through approximately 6 N; keep this requirement tied to the forest
# mask footprint rather than rejecting a valid country-wide export for ocean
# padding north of the island.
KALIMANTAN_BBOX_WGS84 = [109.0, -5.0, 120.0, 6.0]


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.is_file():
        return None, "missing_file"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"invalid_json:{type(exc).__name__}"
    if not isinstance(value, dict):
        return None, "json_root_must_be_object"
    return value, None


def _relative(root: Path, path: Path) -> str:
    return logical_relative(root, path)


def _metadata_errors(metadata: dict[str, Any] | None) -> list[str]:
    if metadata is None:
        return ["missing_or_invalid_provenance_metadata"]
    errors: list[str] = []
    required = {
        "source_url",
        "retrieved_at_utc",
        "collection",
        "baseline_year",
        "export_kind",
        "export_region_bbox_wgs84",
    }
    errors.extend(f"provenance_missing_field:{field}" for field in sorted(required - set(metadata)))
    if metadata.get("collection") != COLLECTION:
        errors.append(f"provenance_collection_must_be:{COLLECTION}")
    if metadata.get("baseline_year") != BASELINE_YEAR:
        errors.append(f"provenance_baseline_year_must_be:{BASELINE_YEAR}")
    identifier = metadata.get("export_asset_id") or metadata.get("download_id")
    if not isinstance(identifier, str) or not identifier.strip():
        errors.append("provenance_export_asset_id_or_download_id_empty")
    if metadata.get("export_kind") != "land_cover_raster":
        errors.append("provenance_export_kind_must_be:land_cover_raster")
    bbox = metadata.get("export_region_bbox_wgs84")
    if not isinstance(bbox, list) or len(bbox) != 4 or not all(isinstance(value, (int, float)) for value in bbox):
        errors.append("provenance_export_region_bbox_invalid")
    else:
        west, south, east, north = [float(value) for value in bbox]
        if not (west < east and south < north):
            errors.append("provenance_export_region_bbox_not_ordered")
        target_west, target_south, target_east, target_north = KALIMANTAN_BBOX_WGS84
        if west > target_west or south > target_south or east < target_east or north < target_north:
            errors.append("provenance_export_region_does_not_cover_kalimantan_bbox")
    if not isinstance(metadata.get("source_url"), str) or "mapbiomas" not in metadata.get("source_url", "").lower():
        errors.append("provenance_source_url_not_mapbiomas")
    try:
        datetime.fromisoformat(str(metadata.get("retrieved_at_utc", "")).replace("Z", "+00:00"))
    except ValueError:
        errors.append("provenance_retrieved_at_utc_invalid")
    return errors


def _crosswalk_errors(crosswalk: dict[str, Any] | None) -> list[str]:
    if crosswalk is None:
        return ["missing_or_invalid_class_crosswalk"]
    errors: list[str] = []
    if crosswalk.get("schema_version") != "mapbiomas-class-crosswalk/v1":
        errors.append("crosswalk_schema_version_invalid")
    if crosswalk.get("collection") != COLLECTION:
        errors.append(f"crosswalk_collection_must_be:{COLLECTION}")
    if crosswalk.get("baseline_year") != BASELINE_YEAR:
        errors.append(f"crosswalk_baseline_year_must_be:{BASELINE_YEAR}")
    codes = crosswalk.get("natural_forest_codes")
    if not isinstance(codes, list) or not codes or any(isinstance(code, bool) or not isinstance(code, int) or code <= 0 for code in codes):
        errors.append("crosswalk_natural_forest_codes_must_be_nonempty_positive_integers")
    elif len(set(codes)) != len(codes):
        errors.append("crosswalk_natural_forest_codes_duplicate")
    labels = crosswalk.get("class_labels")
    if not isinstance(labels, dict):
        errors.append("crosswalk_class_labels_missing")
    if not isinstance(crosswalk.get("legend_source_url"), str) or "mapbiomas" not in crosswalk.get("legend_source_url", "").lower():
        errors.append("crosswalk_legend_source_url_not_mapbiomas")
    return errors


def _trusted_prior_preflight(root: Path, raster_path: Path) -> dict[str, Any] | None:
    """Reuse a rasterio-backed preflight when the active runtime lacks rasterio.

    The bundled execution runtime used by the command-line workflow does not
    always ship GDAL/rasterio.  A prior preflight is safe to reuse only when it
    is explicitly ready and its recorded SHA-256 still matches the current
    raster, so a changed or partial download remains fail-closed.
    """

    report_path = root / "outputs" / "quality" / "mapbiomas_2014_preflight.json"
    report, error = _read_json(report_path)
    if error or not report or report.get("ready") is not True:
        return None
    expected_path = _relative(root, raster_path)
    candidates = [
        check for check in report.get("raster_checks", [])
        if isinstance(check, dict) and check.get("path") == expected_path and check.get("readable") is True
    ]
    if len(candidates) != 1:
        return None
    metadata = report.get("metadata")
    expected_hash = metadata.get("raw_sha256") if isinstance(metadata, dict) else None
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        return None
    digest = hashlib.sha256()
    try:
        with raster_path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return None
    if digest.hexdigest().lower() != expected_hash.lower():
        return None
    trusted = dict(candidates[0])
    trusted["validation_method"] = "prior_rasterio_preflight_sha256_verified"
    return trusted


def _raster_checks(root: Path, raster_path: Path, forest_codes: list[int]) -> dict[str, Any]:
    """Check the exported raster without requiring the full raster in memory."""

    result: dict[str, Any] = {
        "path": _relative(root, raster_path),
        "format": raster_path.suffix.lower().lstrip("."),
        "readable": False,
        "errors": [],
    }
    try:
        import rasterio  # type: ignore
        from rasterio.warp import transform_bounds  # type: ignore
    except ImportError:
        trusted = _trusted_prior_preflight(root, raster_path)
        if trusted is not None:
            return trusted
        result["errors"] = ["rasterio_not_installed"]
        return result
    try:
        with rasterio.open(raster_path) as dataset:
            result.update({
                "width": dataset.width,
                "height": dataset.height,
                "band_count": dataset.count,
                "crs": dataset.crs.to_string() if dataset.crs else None,
                "dtype": dataset.dtypes[0] if dataset.dtypes else None,
                "nodata": dataset.nodata,
            })
            errors: list[str] = []
            if dataset.count != 1:
                errors.append("raster_must_have_one_band")
            if not dataset.crs:
                errors.append("raster_crs_missing")
            if dataset.width <= 0 or dataset.height <= 0:
                errors.append("raster_dimensions_invalid")
            bounds = list(dataset.bounds)
            if dataset.crs:
                try:
                    bounds_wgs84 = list(transform_bounds(dataset.crs, "EPSG:4326", *dataset.bounds, densify_pts=21))
                except Exception:
                    bounds_wgs84 = []
            else:
                bounds_wgs84 = []
            result["bounds_wgs84"] = bounds_wgs84
            if len(bounds_wgs84) == 4:
                west, south, east, north = bounds_wgs84
                tw, ts, te, tn = KALIMANTAN_BBOX_WGS84
                if west > tw or south > ts or east < te or north < tn:
                    errors.append("raster_bounds_do_not_cover_kalimantan_bbox")
            # A decimated sample catches an empty export and grossly wrong
            # class values while keeping the preflight cheap for large rasters.
            if dataset.count == 1 and dataset.width > 0 and dataset.height > 0:
                sample = dataset.read(1, out_shape=(min(dataset.height, 1024), min(dataset.width, 1024)), masked=True)
                values = {int(value) for value in sample.compressed()}
                result["sample_unique_values"] = sorted(values)[:200]
                result["sample_valid_pixel_count"] = int(sample.count())
                if not values:
                    errors.append("raster_has_no_valid_sample_pixels")
                if forest_codes and values and not values.intersection(forest_codes):
                    errors.append("raster_sample_contains_no_natural_forest_class_code")
            result["readable"] = not errors
            result["errors"] = errors
    except Exception as exc:
        result["errors"] = [f"raster_unreadable:{type(exc).__name__}:{exc}"]
    return result


def validate_mapbiomas_export(root: Path, export_dir: Path | None = None) -> dict[str, Any]:
    """Validate the frozen MapBiomas export hand-off, without network calls."""

    root = root.absolute()
    export_dir = (export_dir or root / "data" / "raw" / "mapbiomas_indonesia").absolute()
    metadata_path = export_dir / "mapbiomas_2014_provenance.json"
    crosswalk_path = export_dir / "class_crosswalk.json"
    metadata, metadata_error = _read_json(metadata_path)
    crosswalk, crosswalk_error = _read_json(crosswalk_path)
    metadata_errors = _metadata_errors(metadata)
    crosswalk_errors = _crosswalk_errors(crosswalk)
    forest_codes = crosswalk.get("natural_forest_codes", []) if isinstance(crosswalk, dict) else []
    raster_paths = sorted(path for path in export_dir.glob("*.tif") if path.is_file()) + sorted(path for path in export_dir.glob("*.tiff") if path.is_file())
    raster_checks = [_raster_checks(root, path, forest_codes) for path in raster_paths]
    errors: list[str] = []
    if not export_dir.is_dir():
        errors.append("export_directory_missing")
    if metadata_error:
        errors.append(f"provenance_{metadata_error}")
    if crosswalk_error:
        errors.append(f"crosswalk_{crosswalk_error}")
    errors.extend(metadata_errors)
    errors.extend(crosswalk_errors)
    if not raster_paths:
        errors.append("missing_land_cover_raster")
    elif len(raster_paths) != 1:
        errors.append("expected_exactly_one_land_cover_raster")
    for check in raster_checks:
        errors.extend(check["errors"])
    ready = bool(export_dir.is_dir() and raster_paths and len(raster_paths) == 1 and not errors)
    return {
        "schema_version": "mapbiomas-preflight/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_collection_4_1_2014_export" if ready else "blocked_mapbiomas_export_preflight",
        "ready": ready,
        "export_directory": _relative(root, export_dir) if export_dir.is_relative_to(root) else str(export_dir),
        "provenance_path": _relative(root, metadata_path) if metadata_path.is_relative_to(root) else str(metadata_path),
        "crosswalk_path": _relative(root, crosswalk_path) if crosswalk_path.is_relative_to(root) else str(crosswalk_path),
        "metadata": metadata or {},
        "crosswalk": crosswalk or {},
        "raster_checks": raster_checks,
        "errors": errors,
        "official_workflow": {
            "faq_url": MAPBIOMAS_FAQ_URL,
            "gee_url": MAPBIOMAS_GEE_URL,
            "download_url": MAPBIOMAS_DOWNLOAD_URL,
            "legend_url": MAPBIOMAS_LEGEND_URL,
            "required_collection": COLLECTION,
            "required_baseline_year": BASELINE_YEAR,
            "required_region_bbox_wgs84": KALIMANTAN_BBOX_WGS84,
        },
        "next_action": (
            "Place one official Collection 4.1 2014 land-cover GeoTIFF, class_crosswalk.json, "
            "and mapbiomas_2014_provenance.json in data/raw/mapbiomas_indonesia/, then rerun "
            "python scripts/research.py mapbiomas-preflight."
        ) if not ready else "Use the validated raster and crosswalk to build the frozen 2014 forest mask before VIIRS frame construction.",
    }


def write_mapbiomas_preflight(root: Path, output_path: Path | None = None) -> dict[str, Any]:
    output_path = output_path or root / "outputs" / "quality" / "mapbiomas_2014_preflight.json"
    report = validate_mapbiomas_export(root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report
