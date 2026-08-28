"""Phase 1B readiness checks for temporal support and the VIIRS denominator.

Phase 1B is deliberately a *closure* phase. It certifies only a fully derived,
receipt-backed denominator and covariate frame. File presence alone never
passes a gate. The environmental-condition track is kept separate from the
still-blocked human-access/land-transformation track.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .protocol import validate_protocol
from .quality import sha256_file, verify_immutable_lock
from .temporal_qa import check_chirps, check_era5, check_mod13, run_temporal_qa
from .mapbiomas import validate_mapbiomas_export


ERA5_VARIABLES = ("u10", "v10", "t2m", "d2m", "tp", "swvl1", "swvl2", "swvl3")
FRAME_COLUMNS = {
    "opportunity_id",
    "pair_key",
    "cell_id",
    "acquisition_utc",
    "outcome_status",
    "valid_opportunity",
    "history_fallback_used",
    "forest_fraction",
    "quality_pass",
    "coverage_fraction",
    "negative_lookback_hours",
}
FRAME_FORBIDDEN_COLUMNS = {
    "latitude", "longitude", "lat", "lon", "reported_time",
    "grid_row", "grid_col", "supercell_id",
}
ERA5_RE = re.compile(r"era5_land_(?P<year>\d{4})_(?P<month>\d{2})\.nc$")
MAPBIOMAS_MASK_REL = "data/derived/mapbiomas/mapbiomas_c41_natural_forest_mask_2014_kalimantan.tif"
MAPBIOMAS_MASK_REPORT_REL = "outputs/quality/mapbiomas_2014_forest_mask.json"
MAPBIOMAS_GRID_REL = "data/derived/mapbiomas/mapbiomas_c41_forest_fraction_1km_kalimantan.tif"
MAPBIOMAS_GRID_REPORT_REL = "outputs/quality/mapbiomas_2014_forest_fraction_1km.json"
VIIRS_DIAGNOSTIC_REPORT_REL = "outputs/quality/viirs_opportunity_diagnostic.json"
DAILY_FRAME_REPORT_REL = "outputs/quality/daily_risk_set_frame.json"
REGISTRATION_REL = "config/phase2_registration.json"
TEST_LOCK_REL = "outputs/locks/locked_test_inputs.json"


def _study_years(root: Path) -> list[int]:
    config = json.loads((root / "config" / "study.json").read_text(encoding="utf-8"))
    return sorted({
        year
        for name in ("measurement_calibration", "model_development", "pipeline_rehearsal", "locked_retrospective_test")
        for year in range(
            int(config["time_split"][name][0]),
            int(config["time_split"][name][1]) + 1,
        )
    })


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check_mapbiomas_forest_mask(root: Path) -> dict[str, Any]:
    """Check the immutable, hash-receipted 2014 natural-forest mask."""

    path = root / Path(MAPBIOMAS_MASK_REL)
    report_path = root / Path(MAPBIOMAS_MASK_REPORT_REL)
    errors: list[str] = []
    if not path.is_file():
        errors.append("missing_forest_mask")
    if not report_path.is_file():
        errors.append("missing_forest_mask_report")
        report: dict[str, Any] = {}
    else:
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            report = {}
            errors.append("invalid_forest_mask_report")
    if report.get("status") != "validated":
        errors.append("forest_mask_report_not_validated")
    output = report.get("output", {}) if isinstance(report, dict) else {}
    if output.get("path") != MAPBIOMAS_MASK_REL:
        errors.append("forest_mask_report_path_mismatch")
    if output.get("forest_codes") != [3, 5, 76]:
        errors.append("forest_mask_codes_mismatch")
    if not isinstance(output.get("bbox_wgs84"), list) or len(output.get("bbox_wgs84", [])) != 4:
        errors.append("forest_mask_bbox_missing")
    expected_hash = output.get("sha256")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        errors.append("forest_mask_sha256_missing")
    elif path.is_file() and _sha256(path).lower() != expected_hash.lower():
        errors.append("forest_mask_sha256_mismatch")
    ready = path.is_file() and report_path.is_file() and not errors
    return {
        "status": "validated_forest_mask" if ready else "blocked_forest_mask",
        "gate_ready": ready,
        "path": MAPBIOMAS_MASK_REL,
        "report_path": MAPBIOMAS_MASK_REPORT_REL,
        "forest_codes": output.get("forest_codes", []),
        "forest_fraction_of_valid_source": output.get("natural_forest_fraction_of_valid_source"),
        "errors": errors,
    }


def check_mapbiomas_1km_grid(root: Path) -> dict[str, Any]:
    """Check the EPSG:6933 1-km forest-fraction receipt."""

    path = root / Path(MAPBIOMAS_GRID_REL)
    report_path = root / Path(MAPBIOMAS_GRID_REPORT_REL)
    errors: list[str] = []
    if not path.is_file():
        errors.append("missing_1km_forest_fraction_grid")
    if not report_path.is_file():
        errors.append("missing_1km_forest_fraction_report")
        report: dict[str, Any] = {}
    else:
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            report = {}
            errors.append("invalid_1km_forest_fraction_report")
    if report.get("status") != "validated":
        errors.append("1km_forest_fraction_report_not_validated")
    output = report.get("output", {}) if isinstance(report, dict) else {}
    if output.get("path") != MAPBIOMAS_GRID_REL:
        errors.append("1km_forest_fraction_report_path_mismatch")
    if output.get("crs") != "EPSG:6933":
        errors.append("1km_forest_fraction_crs_mismatch")
    if output.get("cell_size_m") != 1000 or output.get("anchor") != [0, 0]:
        errors.append("1km_forest_fraction_grid_definition_mismatch")
    expected_hash = output.get("sha256")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        errors.append("1km_forest_fraction_sha256_missing")
    elif path.is_file() and _sha256(path).lower() != expected_hash.lower():
        errors.append("1km_forest_fraction_sha256_mismatch")
    ready = path.is_file() and report_path.is_file() and not errors
    return {
        "status": "validated_1km_forest_fraction" if ready else "blocked_1km_forest_fraction",
        "gate_ready": ready,
        "path": MAPBIOMAS_GRID_REL,
        "report_path": MAPBIOMAS_GRID_REPORT_REL,
        "cells_at_or_above_70_percent": output.get("cells_at_or_above_70_percent"),
        "cells_at_or_above_50_percent": output.get("cells_at_or_above_50_percent"),
        "errors": errors,
    }


def read_viirs_diagnostic(root: Path) -> dict[str, Any] | None:
    """Expose a bounded VIIRS rehearsal receipt without treating it as a gate."""

    path = root / Path(VIIRS_DIAGNOSTIC_REPORT_REL)
    if not path.is_file():
        return None
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "invalid_diagnostic_report", "path": VIIRS_DIAGNOSTIC_REPORT_REL}
    return {
        "status": report.get("status", "unknown"),
        "path": VIIRS_DIAGNOSTIC_REPORT_REL,
        "denominator_ready": report.get("denominator_ready", False),
        "summary": report.get("summary", {}),
        "limitations": report.get("limitations", []),
    }


def _check_era5_content(root: Path, years: list[int]) -> dict[str, Any]:
    """Validate NetCDF metadata without loading the climate arrays."""

    files = sorted((root / "data" / "raw" / "era5_land").rglob("era5_land_*.nc"))
    expected = {(year, month) for year in years for month in range(1, 13)}
    observed: set[tuple[int, int]] = set()
    errors: list[dict[str, str]] = []
    try:
        import netCDF4  # type: ignore
    except ImportError:
        return {
            "status": "blocked_missing_netCDF4",
            "files_available": len(files),
            "files_checked": 0,
            "expected_file_count": len(expected),
            "observed_file_count_in_study_window": len({
                (int(match["year"]), int(match["month"]))
                for path in files
                if (match := ERA5_RE.fullmatch(path.name))
            } & expected),
            "missing_months": sorted(
                f"{year:04d}-{month:02d}"
                for year, month in expected
                if not any(
                    match and int(match["year"]) == year and int(match["month"]) == month
                    for path in files
                    for match in [ERA5_RE.fullmatch(path.name)]
                )
            ),
            "errors": [{"reason": "netCDF4 is not installed"}],
            "content_validated": False,
        }

    for path in files:
        match = ERA5_RE.fullmatch(path.name)
        if not match:
            errors.append({"path": path.as_posix(), "reason": "malformed_filename"})
            continue
        year, month = int(match["year"]), int(match["month"])
        observed.add((year, month))
        try:
            with netCDF4.Dataset(path) as dataset:
                names = set(dataset.variables)
                missing_variables = sorted(set(ERA5_VARIABLES) - names)
                if missing_variables:
                    errors.append({"path": path.as_posix(), "reason": f"missing_variables:{','.join(missing_variables)}"})
                    continue
                if "valid_time" not in names or "latitude" not in names or "longitude" not in names:
                    errors.append({"path": path.as_posix(), "reason": "missing_coordinate_or_time_variable"})
                    continue
                time_variable = dataset.variables["valid_time"]
                time_values = time_variable[:]
                time_len = len(time_values)
                expected_hours = (datetime(year, month % 12 + 1, 1) - datetime(year, month, 1)).total_seconds() / 3600 if month < 12 else (datetime(year + 1, 1, 1) - datetime(year, 12, 1)).total_seconds() / 3600
                if time_len != int(expected_hours):
                    errors.append({"path": path.as_posix(), "reason": f"expected_{int(expected_hours)}_hourly_records_got_{time_len}"})
                units = getattr(time_variable, "units", None)
                calendar = getattr(time_variable, "calendar", "standard")
                if not units:
                    errors.append({"path": path.as_posix(), "reason": "valid_time_missing_units"})
                elif time_len:
                    converted = netCDF4.num2date(
                        [time_values[0], time_values[-1]],
                        units=units,
                        calendar=calendar,
                        only_use_cftime_datetimes=False,
                    )
                    first, last = converted[0], converted[-1]
                    if (first.year, first.month, first.day, first.hour) != (year, month, 1, 0):
                        errors.append({"path": path.as_posix(), "reason": "valid_time_first_timestamp_mismatch"})
                    next_month = datetime(year + (month == 12), 1 if month == 12 else month + 1, 1)
                    expected_last = next_month - timedelta(hours=1)
                    if (last.year, last.month, last.day, last.hour) != (expected_last.year, expected_last.month, expected_last.day, expected_last.hour):
                        errors.append({"path": path.as_posix(), "reason": "valid_time_last_timestamp_mismatch"})
                lat = dataset.variables["latitude"][:]
                lon = dataset.variables["longitude"][:]
                if float(lat.min()) > -5 or float(lat.max()) < 8 or float(lon.min()) > 109 or float(lon.max()) < 120:
                    errors.append({"path": path.as_posix(), "reason": "requested_bbox_not_covered"})
                for variable in ERA5_VARIABLES:
                    if dataset.variables[variable].shape[0] != time_len:
                        errors.append({"path": path.as_posix(), "reason": f"{variable}_time_dimension_mismatch"})
        except Exception as exc:  # partial files are expected while acquisition runs
            errors.append({"path": path.as_posix(), "reason": f"unreadable:{type(exc).__name__}:{exc}"})

    missing = sorted(f"{year:04d}-{month:02d}" for year, month in expected - observed)
    content_validated = bool(files) and not missing and not errors
    return {
        "status": "content_validated_complete" if content_validated else "content_present_but_incomplete_or_invalid",
        "files_checked": len(files),
        "expected_file_count": len(expected),
        "observed_file_count_in_study_window": len(observed & expected),
        "missing_months": missing,
        "errors": errors,
        "content_validated": content_validated,
        "required_variables": list(ERA5_VARIABLES),
        "bbox": [8, 109, -5, 120],
    }


def validate_opportunity_frame(root: Path, path: Path | None = None) -> dict[str, Any]:
    """Validate a future aggregate cell-level opportunity frame.

    Coordinates and raw detection rows are intentionally excluded.  The frame
    must contain both positive and valid-negative observations before it can
    participate in a matched model.
    """

    path = path or root / "data" / "derived" / "viirs" / "opportunity_frame.csv"
    if not path.is_file():
        return {
            "status": "blocked_missing_opportunity_frame",
            "path": path.relative_to(root).as_posix(),
            "row_count": 0,
            "positive_rows": 0,
            "negative_rows": 0,
            "errors": ["No processed VIIRS opportunity frame exists; swath counts are not a denominator."],
            "denominator_ready": False,
        }
    errors: list[str] = []
    rows: list[dict[str, str]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        errors.extend(f"missing_column:{column}" for column in sorted(FRAME_COLUMNS - fields))
        errors.extend(f"forbidden_column:{column}" for column in sorted(fields & FRAME_FORBIDDEN_COLUMNS))
        rows = list(reader)
    seen: set[tuple[str, str]] = set()
    positive = negative = 0
    valid_positive = valid_negative = 0
    for row in rows:
        key = (row.get("opportunity_id", ""), row.get("cell_id", ""))
        if key in seen:
            errors.append(f"duplicate_key:{key[0]}:{key[1]}")
        seen.add(key)
        valid_value = row.get("valid_opportunity", "").lower() in {"true", "1"}
        if row.get("outcome_status") == "positive":
            positive += 1
            valid_positive += int(valid_value)
        elif row.get("outcome_status") == "negative":
            negative += 1
            valid_negative += int(valid_value)
        elif row.get("outcome_status") != "unknown":
            errors.append(f"invalid_outcome_status:{row.get('outcome_status', '')}")
        if row.get("valid_opportunity", "").lower() not in {"true", "false", "0", "1"}:
            errors.append(f"invalid_valid_opportunity:{key[0]}")
        if row.get("history_fallback_used", "").lower() not in {"true", "false", "0", "1"}:
            errors.append(f"invalid_history_fallback_flag:{key[0]}")
    ready = bool(rows) and positive > 0 and negative > 0 and valid_positive > 0 and valid_negative > 0 and not errors
    return {
        "status": "validated_positive_and_negative_frame" if ready else "present_but_not_ready",
        "path": path.relative_to(root).as_posix(),
        "row_count": len(rows),
        "positive_rows": positive,
        "negative_rows": negative,
        "valid_positive_rows": valid_positive,
        "valid_negative_rows": valid_negative,
        "errors": errors,
        "denominator_ready": ready,
    }


def validate_environmental_registration(root: Path) -> dict[str, Any]:
    """Validate the frozen daily-grid registration against the study config."""

    path = root / REGISTRATION_REL
    errors: list[str] = []
    if not path.is_file():
        return {"status": "blocked_missing_registration", "gate_ready": False, "errors": ["missing_registration"]}
    try:
        registration = json.loads(path.read_text(encoding="utf-8"))
        study = json.loads((root / "config" / "study.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "blocked_invalid_registration", "gate_ready": False, "errors": [str(exc)]}
    if registration.get("schema_version") != "environmental-daily-risk-set-registration/v1":
        errors.append("registration_schema_mismatch")
    if registration.get("track_id") != "environmental_daily_grid":
        errors.append("registration_track_mismatch")
    if registration.get("projection") != study.get("projection") or registration.get("grid_m") != 1000:
        errors.append("registration_grid_mismatch")
    if registration.get("study_years") != _study_years(root):
        errors.append("registration_years_mismatch")
    if registration.get("time_split") != study.get("time_split"):
        # study.json also contains monitoring_year, so compare registered split
        # members explicitly rather than accepting a hidden year reassignment.
        for key, value in registration.get("time_split", {}).items():
            if study.get("time_split", {}).get(key) != value:
                errors.append(f"registration_time_split_mismatch:{key}")
    outcome = registration.get("outcome", {})
    if outcome.get("product") != "NASA/VIIRS/002/VNP14A1" or outcome.get("product_version") != "002":
        errors.append("registration_viirs_product_mismatch")
    controls = registration.get("controls", {})
    if controls.get("per_case") != 4 or controls.get("maximum_distance_km") != 25:
        errors.append("registration_control_design_mismatch")
    release = registration.get("release_rules", {})
    if release.get("coordinates_in_public_artifact") is not False:
        errors.append("registration_coordinate_release_rule_missing")
    ready = not errors
    return {
        "status": "validated_registration" if ready else "blocked_invalid_registration",
        "gate_ready": ready,
        "path": REGISTRATION_REL,
        "sha256": sha256_file(path),
        "errors": errors,
    }


def validate_daily_frame_receipt(root: Path) -> dict[str, Any]:
    """Fail closed unless the complete registered frame and hash receipt agree."""

    report_path = root / DAILY_FRAME_REPORT_REL
    if not report_path.is_file():
        return {
            "status": "blocked_missing_daily_frame_receipt",
            "gate_ready": False,
            "denominator_ready": False,
            "covariates_complete": False,
            "errors": ["missing_daily_frame_receipt"],
        }
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "blocked_invalid_daily_frame_receipt",
            "gate_ready": False,
            "denominator_ready": False,
            "covariates_complete": False,
            "errors": [str(exc)],
        }
    errors: list[str] = []
    if report.get("schema_version") != "daily-risk-set-frame/v1":
        errors.append("daily_frame_schema_mismatch")
    if report.get("status") != "validated_complete":
        errors.append("daily_frame_not_validated_complete")
    if report.get("registered_day_count") != 1683 or report.get("completed_day_count") != 1683:
        errors.append("daily_frame_day_coverage_incomplete")
    if report.get("study_years") != _study_years(root):
        errors.append("daily_frame_year_coverage_mismatch")
    if report.get("source_product") != "NASA/VIIRS/002/VNP14A1":
        errors.append("daily_frame_source_product_mismatch")
    if report.get("control_count") != 4 * int(report.get("case_count", -1)):
        errors.append("daily_frame_control_ratio_mismatch")
    output_rel = report.get("output")
    if not isinstance(output_rel, str):
        errors.append("daily_frame_output_missing")
        output_path = None
    else:
        output_path = root / output_rel
        if not output_path.is_file():
            errors.append("daily_frame_output_not_found")
        elif report.get("output_sha256") != sha256_file(output_path):
            errors.append("daily_frame_output_hash_mismatch")
    registration_path = root / REGISTRATION_REL
    if registration_path.is_file() and report.get("registration_sha256") != sha256_file(registration_path):
        errors.append("daily_frame_registration_hash_mismatch")
    ready = (
        report.get("denominator_ready") is True
        and report.get("covariates_complete") is True
        and report.get("phase_1b_track_ready") is True
        and not errors
    )
    return {
        "status": "validated_complete_daily_frame" if ready else "blocked_incomplete_or_invalid_daily_frame",
        "gate_ready": ready,
        "denominator_ready": report.get("denominator_ready") is True and not errors,
        "covariates_complete": report.get("covariates_complete") is True and not errors,
        "path": DAILY_FRAME_REPORT_REL,
        "row_count": report.get("row_count", 0),
        "case_count": report.get("case_count", 0),
        "control_count": report.get("control_count", 0),
        "completed_day_count": report.get("completed_day_count", 0),
        "registered_day_count": report.get("registered_day_count", 1683),
        "errors": errors,
    }


def validate_peat_stratum_receipt(root: Path) -> dict[str, Any]:
    """Validate the frozen peat extent used by the environmental track."""

    receipt_path = root / "outputs" / "quality" / "peat_sensitivity_provenance.json"
    errors: list[str] = []
    if not receipt_path.is_file():
        return {"status": "blocked_missing_peat_receipt", "gate_ready": False, "errors": ["missing_peat_receipt"]}
    try:
        report = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "blocked_invalid_peat_receipt", "gate_ready": False, "errors": [str(exc)]}
    asset = report.get("assets", {}).get("peat_baseline", {})
    path_rel = asset.get("path")
    if not isinstance(path_rel, str):
        errors.append("peat_path_missing")
    else:
        path = root / path_rel
        if not path.is_file():
            errors.append("peat_file_missing")
        elif asset.get("sha256") != sha256_file(path):
            errors.append("peat_hash_mismatch")
    if asset.get("license") != "CC-BY-4.0" or asset.get("reference_period") != "2000-2020":
        errors.append("peat_provenance_mismatch")
    ready = not errors
    return {
        "status": "validated_static_peat_stratum" if ready else "blocked_invalid_peat_stratum",
        "gate_ready": ready,
        "path": path_rel,
        "receipt": "outputs/quality/peat_sensitivity_provenance.json",
        "errors": errors,
    }


def build_phase1b_readiness(root: Path) -> dict[str, Any]:
    years = _study_years(root)
    temporal = run_temporal_qa(root)
    era5_content = _check_era5_content(root, years)
    frame = validate_opportunity_frame(root)
    protocol = validate_protocol(root)
    era5_inventory = check_era5(root, years)
    chirps = check_chirps(root, years)
    vegetation = check_mod13(root, years)
    mapbiomas = validate_mapbiomas_export(root)
    mapbiomas_mask = check_mapbiomas_forest_mask(root)
    mapbiomas_grid = check_mapbiomas_1km_grid(root)
    viirs_diagnostic = read_viirs_diagnostic(root)
    registration = validate_environmental_registration(root)
    daily_frame = validate_daily_frame_receipt(root)
    peat_stratum = validate_peat_stratum_receipt(root)
    lock = verify_immutable_lock(root, root / TEST_LOCK_REL)

    workstreams = {
        "era5_temporal_support": {
            "status": "validated_and_joined" if era5_content["content_validated"] and daily_frame["covariates_complete"] else "ready_for_join" if era5_content["content_validated"] else "blocked_incomplete_or_invalid",
            "gate_ready": era5_content["content_validated"] and daily_frame["covariates_complete"],
            "required_for_environmental_track": True,
            "next_action": "run the ERA5 finalizer after daily extraction completes" if era5_content["content_validated"] else "complete and validate all registered ERA5-Land months",
            "inventory": era5_inventory,
            "content": era5_content,
        },
        "chirps_lag_features": {
            "status": "validated_event_linked_earth_engine" if daily_frame["covariates_complete"] else "blocked_daily_frame_incomplete",
            "gate_ready": daily_frame["covariates_complete"],
            "required_for_environmental_track": True,
            "next_action": "finish the registered Earth Engine daily extraction and receipt; the partial local archive is no longer the primary gate",
            "inventory": chirps,
        },
        "prefire_vegetation": {
            "status": "validated_prefire_event_linked_earth_engine" if daily_frame["covariates_complete"] else "blocked_daily_frame_incomplete",
            "gate_ready": daily_frame["covariates_complete"],
            "required_for_environmental_track": True,
            "next_action": "finish the registered Earth Engine MOD13Q1 QA join; the partial local archive remains a sensitivity source",
            "inventory": vegetation,
        },
        "environmental_registration": {
            "status": registration["status"],
            "gate_ready": registration["gate_ready"],
            "required_for_environmental_track": True,
            "next_action": "keep the registered file unchanged through locked analysis" if registration["gate_ready"] else "repair the registration errors before extraction",
            "registration": registration,
        },
        "mapbiomas_2014_baseline": {
            "status": mapbiomas["status"],
            "gate_ready": mapbiomas["ready"],
            "required_for_environmental_track": True,
            "next_action": mapbiomas["next_action"],
            "preflight": mapbiomas,
        },
        "mapbiomas_2014_forest_mask": {
            "status": mapbiomas_mask["status"],
            "gate_ready": mapbiomas_mask["gate_ready"],
            "required_for_environmental_track": True,
            "next_action": "use the validated binary mask to compute 1-km forest fractions for paired VIIRS pixels" if mapbiomas_mask["gate_ready"] else "build and hash the Kalimantan 2014 natural-forest mask from MapBiomas codes 3, 5, and 76",
            "mask": mapbiomas_mask,
        },
        "mapbiomas_2014_1km_forest_fraction": {
            "status": mapbiomas_grid["status"],
            "gate_ready": mapbiomas_grid["gate_ready"],
            "required_for_environmental_track": True,
            "next_action": "intersect paired VIIRS geolocation with the fixed 1-km grid and retain cells at or above the registered 70% forest threshold" if mapbiomas_grid["gate_ready"] else "aggregate the validated 30 m forest mask to the anchored EPSG:6933 1-km grid",
            "grid": mapbiomas_grid,
        },
        "viirs_opportunity_denominator": {
            "status": daily_frame["status"],
            "gate_ready": daily_frame["denominator_ready"],
            "required_for_environmental_track": True,
            "next_action": "complete all 1,683 registered fire-season days, then finalize and hash the 1:4 frame",
            "frame": daily_frame,
            "diagnostic": viirs_diagnostic,
        },
        "peat_static_stratum": {
            "status": peat_stratum["status"],
            "gate_ready": peat_stratum["gate_ready"],
            "required_for_environmental_track": True,
            "next_action": "retain threshold sensitivity at 25%, 50%, and 75% peat extent",
            "receipt": peat_stratum,
        },
        "exact_overpass_sensitivity": {
            "status": "diagnostic_sensitivity_only" if viirs_diagnostic else frame["status"],
            "gate_ready": bool(viirs_diagnostic),
            "required_for_environmental_track": False,
            "next_action": "retain the available VNP14IMG/VNP03IMG pairs for measurement sensitivity; do not treat them as the full denominator",
        },
        "human_access_confirmatory_track": {
            "status": "blocked_missing_dated_access_exposure",
            "gate_ready": False,
            "required_for_environmental_track": False,
            "next_action": "obtain a dated, licensed 2014 access exposure before making any road-opening, profit, intent, or government-performance claim",
            "protocol_phase_1_ready": protocol["phase_1_ready"],
            "blocked_assets": [row["asset_id"] for row in protocol["phase_1_gates"] if not row["gate_ready"]],
        },
    }
    gate_ready = all(
        item["gate_ready"]
        for item in workstreams.values()
        if item.get("required_for_environmental_track") is True
    )
    lock_valid = lock.get("valid") is True
    phase_2_unlock = gate_ready and registration["gate_ready"] and lock_valid
    return {
        "schema_version": "phase1b-readiness/v2",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "study_years": years,
        "phase": "Phase 1B -- temporal support and observation denominator closure",
        "status": "phase_2_unlocked" if phase_2_unlock else "ready_for_immutable_lock" if gate_ready else "blocked_phase1b_workstreams",
        "phase_1b_ready": gate_ready,
        "phase_2_unlock": phase_2_unlock,
        "selected_track": "environmental_daily_grid",
        "human_access_confirmatory_track_ready": False,
        "immutable_input_lock": lock,
        "workstreams": workstreams,
        "temporal_qa_status": temporal["status"],
        "acceptance_rule": "Phase 2 environmental modeling remains locked until every required environmental workstream passes and the registered inputs have a valid immutable lock. Non-required sensitivity and human-access tracks cannot silently block or unlock it.",
        "next_phase": "Phase 2 -- registered environmental matched-risk-set calibration" if phase_2_unlock else "Create and verify the immutable input lock" if gate_ready else "Continue Phase 1B daily extraction and finalization; do not fit an association model",
    }
