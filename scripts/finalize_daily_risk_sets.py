"""Attach ERA5-Land, validate the registered scope, and freeze the Phase 1B frame."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import transform

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wildfire_research.era5_features import attach_era5_features, load_prefire_hours
from wildfire_research.quality import sha256_file


ROOT = Path(__file__).resolve().parents[1]
REGISTRATION_PATH = ROOT / "config" / "phase2_registration.json"
SOURCE_ROOT = ROOT / "data" / "derived" / "viirs" / "daily_risk_sets"
CLIMATE_ROOT = ROOT / "data" / "derived" / "viirs" / "daily_risk_sets_with_era5"
ERA5_ROOT = ROOT / "data" / "raw" / "era5_land"
FOREST_PATH = ROOT / "data" / "derived" / "mapbiomas" / "mapbiomas_c41_forest_fraction_1km_kalimantan.tif"
FINAL_PATH = ROOT / "data" / "derived" / "viirs" / "opportunity_frame.csv"
REPORT_PATH = ROOT / "outputs" / "quality" / "daily_risk_set_frame.json"


def expected_days(registration: dict[str, Any]) -> list[date]:
    days: list[date] = []
    for year in registration["study_years"]:
        current = date(year, 7, 1)
        end = date(year, 11, 30)
        while current <= end:
            days.append(current)
            current += timedelta(days=1)
    return days


def _cell_centres(frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    with rasterio.open(FOREST_PATH) as forest:
        rows = pd.to_numeric(frame["grid_row"], errors="raise").astype(int).to_numpy()
        cols = pd.to_numeric(frame["grid_col"], errors="raise").astype(int).to_numpy()
        x = forest.transform.c + (cols + 0.5) * forest.transform.a
        y = forest.transform.f + (rows + 0.5) * forest.transform.e
        lon, lat = transform(forest.crs, "EPSG:4326", x.tolist(), y.tolist())
    return np.asarray(lon, dtype=float), np.asarray(lat, dtype=float)


def _private_ids(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()

    def digest(value: str) -> str:
        return hashlib.sha256(f"phase1b-grid:{value}".encode("utf-8")).hexdigest()[:20]

    cells = [digest(f"{int(row)}:{int(col)}") for row, col in zip(result["grid_row"], result["grid_col"], strict=True)]
    result["cell_id"] = cells
    case_lookup = (
        result.loc[result["outcome_status"] == "positive", ["matched_set_id", "cell_id"]]
        .drop_duplicates("matched_set_id")
        .set_index("matched_set_id")["cell_id"]
    )
    case_cells = result["matched_set_id"].map(case_lookup)
    if case_cells.isna().any():
        raise ValueError("a matched set has no unique positive case")
    dates = result["acquisition_utc"].astype(str).str.slice(0, 10)
    result["matched_set_id"] = [f"{day}:{cell}" for day, cell in zip(dates, case_cells, strict=True)]
    result["opportunity_id"] = [
        digest(f"{matched}:{cell}:{position}")
        for position, (matched, cell) in enumerate(zip(result["matched_set_id"], result["cell_id"], strict=True))
    ]
    return result.drop(columns=["grid_row", "grid_col", "supercell_id", "outcome", "negative_lookback_days"], errors="ignore")


def _deduplicate_logical_opportunities(frame: pd.DataFrame) -> tuple[pd.DataFrame, int, list[str]]:
    """Collapse identical cell/set copies while rejecting conflicting copies."""

    key = ["acquisition_utc", "matched_set_id", "cell_id", "outcome_status"]
    if frame.empty or not set(key).issubset(frame.columns):
        return frame, 0, []
    duplicated = frame.duplicated(key, keep=False)
    if not duplicated.any():
        return frame, 0, []
    compare_columns = [column for column in frame.columns if column not in key and column != "opportunity_id"]
    disagreement = (
        frame.loc[duplicated]
        .groupby(key, dropna=False)[compare_columns]
        .nunique(dropna=False)
        .gt(1)
        .any(axis=1)
    )
    if disagreement.any():
        return frame, 0, ["conflicting_duplicate_logical_opportunity"]
    deduplicated = frame.drop_duplicates(key, keep="first").copy()
    return deduplicated, int(len(frame) - len(deduplicated)), []


def _validate(frame: pd.DataFrame, registration: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "opportunity_id", "matched_set_id", "cell_id", "acquisition_utc", "outcome_status",
        "valid_opportunity", "history_fallback_used", "forest_fraction", "quality_pass", "coverage_fraction",
        "negative_lookback_hours", "peat_extent_percent", "evi_prefire",
        "chirps_precip_1d_mm", "chirps_precip_7d_mm", "chirps_precip_30d_mm", "chirps_precip_90d_mm",
        "era5_rain_24h_mm", "era5_rain_72h_mm", "era5_vpd_mean_24h_kpa",
        "era5_wind_max_24h_ms", "era5_rootzone_soil_water_mean_72h",
    }
    errors.extend(f"missing_column:{column}" for column in sorted(required - set(frame.columns)))
    forbidden = {"latitude", "longitude", "lat", "lon", "grid_row", "grid_col", "supercell_id"}
    errors.extend(f"forbidden_column:{column}" for column in sorted(forbidden & set(frame.columns)))
    if errors:
        return errors
    if frame["opportunity_id"].duplicated().any():
        errors.append("duplicate_opportunity_id")
    counts = frame.groupby("matched_set_id")["outcome_status"].value_counts().unstack(fill_value=0)
    if "positive" not in counts or "negative" not in counts or not ((counts["positive"] == 1) & (counts["negative"] == 4)).all():
        errors.append("matched_set_not_exactly_one_case_four_controls")
    numeric = [column for column in required if column in frame and column not in {"opportunity_id", "matched_set_id", "cell_id", "acquisition_utc", "outcome_status", "valid_opportunity", "history_fallback_used", "quality_pass"}]
    if not np.isfinite(frame[numeric].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)).all():
        errors.append("nonfinite_required_covariate")
    if not (pd.to_numeric(frame["forest_fraction"]) >= registration["cohort"]["minimum_forest_fraction"]).all():
        errors.append("forest_threshold_violation")
    if not (pd.to_numeric(frame["coverage_fraction"]) >= registration["outcome"]["prior_processed_fraction_min"]).all():
        errors.append("coverage_threshold_violation")
    if not (pd.to_numeric(frame["negative_lookback_hours"]) <= registration["outcome"]["prior_negative_days_max"] * 24).all():
        errors.append("prior_negative_window_violation")
    peat = pd.to_numeric(frame["peat_extent_percent"])
    if not ((peat >= 0) & (peat <= 100)).all():
        errors.append("peat_extent_out_of_range")
    timestamps = pd.to_datetime(frame["acquisition_utc"], utc=True, errors="coerce")
    observed_years = sorted(timestamps.dt.year.dropna().unique().tolist())
    if observed_years != registration["study_years"]:
        errors.append(f"study_year_coverage_mismatch:{observed_years}")
    if not timestamps.dt.month.between(7, 11).all():
        errors.append("date_outside_registered_fire_season")
    origin = pd.Timestamp("2000-01-01", tz="UTC")
    composite_end = origin + pd.to_timedelta(pd.to_numeric(frame["evi_composite_start_day"]) + 16, unit="D")
    if not (composite_end < timestamps.dt.normalize()).all():
        errors.append("vegetation_lookahead_detected")
    return errors


def finalize(*, allow_partial: bool, overwrite: bool) -> dict[str, Any]:
    registration = json.loads(REGISTRATION_PATH.read_text(encoding="utf-8"))
    days = expected_days(registration)
    completed: list[Path] = []
    missing_source: list[str] = []
    history_fallback_dates: set[str] = set()
    support_by_year = {
        int(year): {
            "registered_days": 0,
            "observation_supported_days": 0,
            "no_observation_days": 0,
            "history_fallback_days": 0,
        }
        for year in registration["study_years"]
    }
    for index, day in enumerate(days, start=1):
        support_by_year[day.year]["registered_days"] += 1
        source = SOURCE_ROOT / f"{day.year:04d}" / f"{day.isoformat()}.parquet"
        source_receipt = source.with_suffix(".json")
        target = CLIMATE_ROOT / f"{day.year:04d}" / f"{day.isoformat()}.parquet"
        if not source.is_file() or not source_receipt.is_file():
            missing_source.append(day.isoformat())
            continue
        try:
            source_record = json.loads(source_receipt.read_text(encoding="utf-8"))
            source_status = source_record.get("status")
        except (OSError, json.JSONDecodeError):
            source_status = None
        if source_status not in {"complete", "complete_no_observation"}:
            missing_source.append(day.isoformat())
            continue
        if source_status == "complete_no_observation":
            support_by_year[day.year]["no_observation_days"] += 1
        else:
            support_by_year[day.year]["observation_supported_days"] += 1
            if source_record.get("history_fallback_dates"):
                support_by_year[day.year]["history_fallback_days"] += 1
                history_fallback_dates.add(day.isoformat())
        source_is_newer = target.is_file() and source.stat().st_mtime_ns > target.stat().st_mtime_ns
        if not target.is_file() or overwrite or source_is_newer:
            frame = pd.read_parquet(source)
            if frame.empty:
                # A fully processed day with zero qualifying cases is evidence,
                # not a missing day. Preserve its empty chunk and receipt.
                enriched = frame
            else:
                lon, lat = _cell_centres(frame)
                hourly = load_prefire_hours(ERA5_ROOT, day, hours=72)
                enriched = attach_era5_features(frame, longitude=lon, latitude=lat, hourly=hourly)
                invalid_sets = enriched.loc[
                    enriched["weather_support_status"] != "complete_pre_event", "matched_set_id"
                ].unique()
                if len(invalid_sets):
                    enriched = enriched[~enriched["matched_set_id"].isin(invalid_sets)].copy()
            target.parent.mkdir(parents=True, exist_ok=True)
            enriched.to_parquet(target, index=False)
        completed.append(target)
        if index % 25 == 0:
            print(f"ERA5 attachment {index}/{len(days)}", flush=True)

    minimum_support = float(registration["outcome"]["minimum_calendar_support_fraction_each_year"])
    for counts in support_by_year.values():
        counts["calendar_support_fraction"] = round(
            counts["observation_supported_days"] / counts["registered_days"], 6
        ) if counts["registered_days"] else 0.0

    if missing_source and not allow_partial:
        report = {
            "schema_version": "daily-risk-set-frame/v1",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "blocked_incomplete_daily_extraction",
            "registered_day_count": len(days),
            "completed_day_count": len(completed),
            "missing_day_count": len(missing_source),
            "missing_days_preview": missing_source[:25],
            "observation_support_by_year": support_by_year,
            "minimum_calendar_support_fraction_each_year": minimum_support,
            "denominator_ready": False,
            "covariates_complete": False,
            "phase_1b_track_ready": False,
        }
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return report

    frames = [pd.read_parquet(path) for path in completed]
    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not combined.empty:
        combined["history_fallback_used"] = (
            combined["acquisition_utc"].astype(str).str.slice(0, 10).isin(history_fallback_dates)
        )
    combined, duplicate_rows_removed, deduplication_errors = _deduplicate_logical_opportunities(combined)
    final = _private_ids(combined)
    errors = (deduplication_errors + _validate(final, registration)) if not allow_partial else []
    if not allow_partial:
        for year, counts in support_by_year.items():
            if counts["calendar_support_fraction"] < minimum_support:
                errors.append(
                    f"calendar_support_below_registered_minimum:{year}:{counts['calendar_support_fraction']}"
                )
    ready = not missing_source and bool(len(final)) and not errors
    if ready:
        FINAL_PATH.parent.mkdir(parents=True, exist_ok=True)
        final.to_csv(FINAL_PATH, index=False)
    case_count = int((final.get("outcome_status", pd.Series(dtype=str)) == "positive").sum())
    control_count = int((final.get("outcome_status", pd.Series(dtype=str)) == "negative").sum())
    report = {
        "schema_version": "daily-risk-set-frame/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated_complete" if ready else "partial_or_invalid",
        "registration": REGISTRATION_PATH.relative_to(ROOT).as_posix(),
        "registration_sha256": sha256_file(REGISTRATION_PATH),
        "source_product": registration["outcome"]["product"],
        "study_years": registration["study_years"],
        "registered_day_count": len(days),
        "completed_day_count": len(completed),
        "missing_day_count": len(missing_source),
        "observation_support_by_year": support_by_year,
        "minimum_calendar_support_fraction_each_year": minimum_support,
        "row_count": int(len(final)),
        "case_count": case_count,
        "control_count": control_count,
        "matched_set_count": int(final.get("matched_set_id", pd.Series(dtype=str)).nunique()),
        "duplicate_logical_rows_removed": duplicate_rows_removed,
        "history_fallback_day_count": len(history_fallback_dates),
        "history_fallback_dates": sorted(history_fallback_dates),
        "history_fallback_row_count": int(final.get("history_fallback_used", pd.Series(dtype=bool)).sum()),
        "errors": errors,
        "denominator_ready": ready,
        "covariates_complete": ready,
        "phase_1b_track_ready": ready,
        "output": FINAL_PATH.relative_to(ROOT).as_posix() if ready else None,
        "output_sha256": sha256_file(FINAL_PATH) if ready else None,
        "coordinate_release": "none; projected indices are replaced by one-way cell identifiers",
        "interpretation_limit": "environmental association track only; no human-access, arson, plantation-profit, or government-performance conclusion",
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-partial", action="store_true", help="build available climate chunks but never certify Phase 1B")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    report = finalize(allow_partial=args.allow_partial, overwrite=args.overwrite)
    print(json.dumps(report, indent=2))
    return 0 if report.get("phase_1b_track_ready") else 2


if __name__ == "__main__":
    raise SystemExit(main())
