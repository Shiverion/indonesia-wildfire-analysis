"""Build resumable daily VIIRS risk-set chunks with Earth Engine covariates.

The script downloads only analysis-ready candidate rows, then applies the
frozen local MapBiomas forest cohort, peat raster, and deterministic matching.
It never downloads global VIIRS, CHIRPS, or MODIS raster archives.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import transform

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wildfire_research.daily_risk_set import match_daily_controls


ROOT = Path(__file__).resolve().parents[1]
REGISTRATION_PATH = ROOT / "config" / "phase2_registration.json"
FOREST_PATH = ROOT / "data" / "derived" / "mapbiomas" / "mapbiomas_c41_forest_fraction_1km_kalimantan.tif"
PEAT_PATH = ROOT / "data" / "raw" / "peat" / "global" / "peatland.extent_multi_p_1km_s_2000_2020_go_epsg4326_v20260423.tif"
OUTPUT_ROOT = ROOT / "data" / "derived" / "viirs" / "daily_risk_sets"
STATUS_PATH = ROOT / "outputs" / "quality" / "daily_risk_set_extraction_status.json"
LOG_PATH = ROOT / "outputs" / "quality" / "daily_risk_set_extraction.log"
MISSING_SENTINEL = -9999.0


def _dates(start: date, end: date) -> list[date]:
    if end < start:
        raise ValueError("end date precedes start date")
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def _fire_season_days(years: list[int]) -> list[date]:
    return [day for year in years for day in _dates(date(year, 7, 1), date(year, 11, 30))]


def _log(message: str) -> None:
    stamp = datetime.now(timezone.utc).isoformat()
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"{stamp} {message}\n")
    print(message, flush=True)


def _ee_context(project: str) -> tuple[Any, Any, dict[str, Any]]:
    try:
        import ee
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Install earthengine-api before running this extractor") from exc

    registration = json.loads(REGISTRATION_PATH.read_text(encoding="utf-8"))
    ee.Initialize(project=project)
    with rasterio.open(FOREST_PATH) as source:
        projection_wkt = source.crs.to_wkt()
        bounds = source.bounds
        left_index = int(bounds.left // 1000)
        top_index = int(bounds.top // 1000)
    projection = ee.Projection(projection_wkt, [1000, 0, 0, 0, -1000, 0])
    # The WGS84 envelope avoids a server-side edge-transform failure seen when
    # a Rectangle is expressed directly in the WKT form of EPSG:6933.
    region = ee.Geometry.Rectangle([108, -5.5, 120.5, 8], None, False)
    first_year = min(registration["study_years"])
    last_year = max(registration["study_years"])
    viirs_indices = (
        ee.ImageCollection(registration["outcome"]["product"])
        .filterDate(f"{first_year}-06-24", f"{last_year}-12-01")
        .aggregate_array("system:index")
        .getInfo()
    )
    history_fallback_dates: dict[str, set[str]] = {}
    for product in registration["outcome"]["history_gap_fallback"]["products"]:
        timestamps = (
            ee.ImageCollection(product)
            .filterDate(f"{first_year}-06-24", f"{last_year}-12-01")
            .aggregate_array("system:time_start")
            .getInfo()
        )
        history_fallback_dates[product] = {
            datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc).date().isoformat()
            for value in timestamps
        }
    context = {
        "ee": ee,
        "projection": projection,
        "region": region,
        "left_index": left_index,
        "top_index": top_index,
        "registration": registration,
        "viirs_available_dates": {str(value).replace("_", "-") for value in viirs_indices},
        "history_fallback_available_dates": history_fallback_dates,
    }
    return ee, projection, context


def _daily_feature_collection(day: date, context: dict[str, Any]) -> Any:
    ee = context["ee"]
    projection = context["projection"]
    region = context["region"]
    registration = context["registration"]
    event = ee.Date(day.isoformat())
    viirs = ee.ImageCollection(registration["outcome"]["product"])

    def fire_mask(when: Any, source_day: date) -> Any:
        date_text = source_day.isoformat()
        if date_text in context["viirs_available_dates"]:
            return ee.Image(viirs.filterDate(when, when.advance(1, "day")).first()).select("FireMask").toByte()

        donor_images = []
        for product in registration["outcome"]["history_gap_fallback"]["products"]:
            if date_text in context["history_fallback_available_dates"][product]:
                donor_images.append(
                    ee.Image(ee.ImageCollection(product).filterDate(when, when.advance(1, "day")).first())
                    .select("FireMask")
                    .toByte()
                )
        if not donor_images:
            raise ValueError(f"no registered history source for {date_text}")
        any_fire = ee.Image.constant(0).toByte()
        any_valid_land = ee.Image.constant(0).toByte()
        for donor in donor_images:
            any_fire = any_fire.Or(donor.gte(7)).toByte()
            any_valid_land = any_valid_land.Or(donor.eq(5)).toByte()
        return ee.Image.constant(0).where(any_valid_land, 5).where(any_fire, 9).toByte()

    current = fire_mask(event, day)
    processed_count = ee.Image.constant(0).toByte()
    last_negative = ee.Image.constant(999).toInt16()
    for lag in (3, 2, 1):
        prior = fire_mask(event.advance(-lag, "day"), day - timedelta(days=lag))
        processed = prior.eq(5).Or(prior.gte(7)).toByte()
        processed_count = processed_count.add(processed).toByte()
        last_negative = last_negative.where(prior.eq(5), lag).toInt16()
    recent_fire = ee.Image.constant(0).toByte()
    for lag in range(1, 8):
        recent_fire = recent_fire.Or(
            fire_mask(event.advance(-lag, "day"), day - timedelta(days=lag)).gte(7)
        ).toByte()

    coverage = processed_count.divide(3).rename("coverage_fraction").toFloat()
    common = coverage.gte(0.5).And(last_negative.lte(3)).And(recent_fire.eq(0))
    cases = current.gte(7).And(common).rename("eligible").toByte().reproject(projection)
    controls = current.eq(5).And(common).rename("eligible").toByte().reproject(projection)

    pixels = ee.Image.pixelCoordinates(projection)
    grid_col = pixels.select("x").floor().subtract(context["left_index"]).rename("grid_col").toInt32()
    grid_row = ee.Image.constant(context["top_index"]).add(pixels.select("y").floor()).rename("grid_row").toInt32()
    supercell = (
        grid_col.divide(25).floor().toInt32().multiply(10000)
        .add(grid_row.divide(25).floor().toInt32())
        .rename("supercell_id").toInt32()
    )

    base = ee.Image.cat(
        grid_col,
        grid_row,
        supercell,
        last_negative.rename("negative_lookback_days"),
        coverage,
    )
    case_features = (
        base.addBands(ee.Image.constant(1).rename("outcome"))
        .updateMask(cases)
        .sample(region=region, projection=projection, scale=1000, geometries=False, tileScale=8)
    )
    near_case = cases.focalMax(radius=25, kernelType="square", units="pixels").gt(0)
    control_image = (
        base.addBands(ee.Image.constant(0).rename("outcome"))
        .updateMask(controls.And(near_case))
    )
    control_features = control_image.stratifiedSample(
        numPoints=registration["controls"]["earth_engine_candidates_per_active_supercell"],
        classBand="supercell_id",
        region=region,
        scale=1000,
        projection=projection,
        seed=registration["controls"]["random_seed"],
        geometries=False,
        tileScale=8,
    )
    return ee.FeatureCollection(case_features.merge(control_features))


def _ee_covariate_image(day: date, context: dict[str, Any]) -> Any:
    """Build pre-event CHIRPS and QA-valid MOD13Q1 bands in native CRS."""

    ee = context["ee"]
    registration = context["registration"]
    event = ee.Date(day.isoformat())
    chirps = ee.ImageCollection(registration["prefire_covariates"]["chirps"]["collection"])
    modis = ee.ImageCollection(registration["prefire_covariates"]["vegetation"]["collection"])
    rainfall = [
        chirps.filterDate(event.advance(-window, "day"), event).sum()
        .rename(f"chirps_precip_{window}d_mm").toFloat().unmask(MISSING_SENTINEL)
        for window in registration["prefire_covariates"]["chirps"]["windows_days"]
    ]
    # MOD13Q1 timestamps mark composite starts. The end-exclusive filter makes
    # the selected 16-day composite end strictly before the event day.
    composite = ee.Image(
        modis.filterDate(event.advance(-64, "day"), event.advance(-16, "day"))
        .sort("system:time_start", False).first()
    )
    evi = (
        composite.select("EVI").multiply(0.0001)
        .updateMask(composite.select("SummaryQA").eq(0))
        .rename("evi_prefire").toFloat().unmask(MISSING_SENTINEL)
    )
    composite_day = ee.Image.constant(
        ee.Date(composite.get("system:time_start")).difference(ee.Date("2000-01-01"), "day")
    ).rename("evi_composite_start_day").toInt32()
    return ee.Image.cat(*rainfall, evi, composite_day)


def _compute_dataframe(collection: Any, *, retries: int) -> pd.DataFrame:
    import ee

    for attempt in range(retries + 1):
        try:
            result = ee.data.computeFeatures({
                "expression": collection,
                "fileFormat": "PANDAS_DATAFRAME",
                "pageSize": 5000,
            })
            if not isinstance(result, pd.DataFrame):
                raise TypeError(f"Unexpected Earth Engine result type: {type(result).__name__}")
            return result.drop(columns=[column for column in ("geo", "system:index") if column in result], errors="ignore")
        except Exception as exc:
            if attempt >= retries:
                raise
            delay = min(300.0, 10.0 * (2**attempt)) + random.random() * 5.0
            _log(f"Earth Engine attempt {attempt + 1} failed ({type(exc).__name__}: {exc}); retry in {delay:.1f}s")
            time.sleep(delay)
    raise AssertionError("unreachable")


def _attach_ee_covariates(
    frame: pd.DataFrame,
    *,
    day: date,
    context: dict[str, Any],
    retries: int,
    batch_size: int = 1000,
) -> pd.DataFrame:
    """Sample native-CRS covariates at locally reconstructed cell centres."""

    ee = context["ee"]
    image = _ee_covariate_image(day, context)
    with rasterio.open(FOREST_PATH) as forest:
        rows = pd.to_numeric(frame["grid_row"], errors="raise").astype(int).to_numpy()
        cols = pd.to_numeric(frame["grid_col"], errors="raise").astype(int).to_numpy()
        x = forest.transform.c + (cols + 0.5) * forest.transform.a
        y = forest.transform.f + (rows + 0.5) * forest.transform.e
        lon, lat = transform(forest.crs, "EPSG:4326", x.tolist(), y.tolist())
    chunks: list[pd.DataFrame] = []
    for start in range(0, len(frame), batch_size):
        stop = min(len(frame), start + batch_size)
        features = [
            ee.Feature(ee.Geometry.Point([float(lon[index]), float(lat[index])]), {"row_id": int(index)})
            for index in range(start, stop)
        ]
        sampled = image.sampleRegions(
            collection=ee.FeatureCollection(features),
            properties=["row_id"],
            scale=1000,
            geometries=False,
            tileScale=4,
        )
        chunks.append(_compute_dataframe(sampled, retries=retries))
    covariates = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
    covariates["row_id"] = pd.to_numeric(covariates["row_id"], errors="raise").astype(int)
    if covariates["row_id"].duplicated().any() or len(covariates) != len(frame):
        raise ValueError("Earth Engine covariate join is not one-to-one")
    result = frame.reset_index(drop=True).copy()
    result["row_id"] = result.index
    result = result.merge(covariates, on="row_id", how="left", validate="one_to_one").drop(columns="row_id")
    return result


def _attach_local_strata(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    frame = frame.copy()
    rows = pd.to_numeric(frame["grid_row"], errors="coerce").fillna(-1).astype(int).to_numpy()
    cols = pd.to_numeric(frame["grid_col"], errors="coerce").fillna(-1).astype(int).to_numpy()
    with rasterio.open(FOREST_PATH) as forest:
        values = forest.read(1, masked=True)
        inside = (rows >= 0) & (rows < forest.height) & (cols >= 0) & (cols < forest.width)
        fractions = np.full(len(frame), np.nan, dtype=float)
        positions = np.flatnonzero(inside)
        fractions[positions] = np.asarray(values[rows[positions], cols[positions]].filled(np.nan), dtype=float)
        x = forest.transform.c + (cols + 0.5) * forest.transform.a
        y = forest.transform.f + (rows + 0.5) * forest.transform.e
        source_crs = forest.crs
    frame["forest_fraction"] = fractions
    forest_keep = np.isfinite(fractions) & (fractions >= 0.7)
    frame = frame.loc[forest_keep].copy()
    x = x[forest_keep]
    y = y[forest_keep]

    with rasterio.open(PEAT_PATH) as peat:
        lon, lat = transform(source_crs, peat.crs, x.tolist(), y.tolist())
        peat_values = np.asarray([value[0] for value in peat.sample(zip(lon, lat, strict=True))], dtype=float)
        peat_values[(peat_values < 0) | (peat_values > 100) | (peat_values == peat.nodata)] = np.nan
    frame["peat_extent_percent"] = peat_values
    return frame, {
        "outside_or_below_forest_threshold": int((~forest_keep).sum()),
        "peat_unknown": int(np.isnan(peat_values).sum()),
    }


def _write_status(days: list[date], completed: int, failed: dict[str, str], current: str | None) -> None:
    sizes = [path.stat().st_size for path in OUTPUT_ROOT.rglob("*.parquet")]
    payload = {
        "schema_version": "daily-risk-set-extraction-status/v1",
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "complete" if completed == len(days) and not failed else "running_or_incomplete",
        "expected_days": len(days),
        "completed_days": completed,
        "progress_percent": round(100 * completed / len(days), 2) if days else 100.0,
        "current_day": current,
        "failed_days": failed,
        "chunk_size_bytes": int(sum(sizes)),
        "output_root": OUTPUT_ROOT.relative_to(ROOT).as_posix(),
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def run(project: str, days: list[date], retries: int, overwrite: bool) -> int:
    _, _, context = _ee_context(project)
    registration = context["registration"]
    failed: dict[str, str] = {}
    completed = 0
    for day in days:
        output = OUTPUT_ROOT / f"{day.year:04d}" / f"{day.isoformat()}.parquet"
        receipt_path = output.with_suffix(".json")
        if output.is_file() and receipt_path.is_file() and not overwrite:
            try:
                existing_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                existing_receipt = {}
            event_available = day.isoformat() in context["viirs_available_dates"]
            history_dates = [day - timedelta(days=lag) for lag in range(1, 8)]
            history_fillable = all(
                value.isoformat() in context["viirs_available_dates"]
                or any(
                    value.isoformat() in available
                    for available in context["history_fallback_available_dates"].values()
                )
                for value in history_dates
            )
            repairable_history_gap = (
                existing_receipt.get("status") == "complete_no_observation"
                and event_available
                and history_fillable
            )
            if not repairable_history_gap:
                completed += 1
                _write_status(days, completed, failed, day.isoformat())
                continue
        try:
            _log(f"Extracting {day.isoformat()} ({completed + 1}/{len(days)})")
            history_dates = [day - timedelta(days=lag) for lag in range(1, 8)]
            missing_history_viirs_dates = [
                value.isoformat()
                for value in history_dates
                if value.isoformat() not in context["viirs_available_dates"]
            ]
            unavailable_history_dates = [
                value
                for value in missing_history_viirs_dates
                if not any(
                    value in available
                    for available in context["history_fallback_available_dates"].values()
                )
            ]
            event_product_available = day.isoformat() in context["viirs_available_dates"]
            if not event_product_available or unavailable_history_dates:
                output.parent.mkdir(parents=True, exist_ok=True)
                pd.DataFrame().to_parquet(output, index=False)
                receipt = {
                    "date": day.isoformat(),
                    "created_at_utc": datetime.now(timezone.utc).isoformat(),
                    "earth_engine_candidate_rows": 0,
                    "outside_or_below_forest_threshold": 0,
                    "peat_unknown": 0,
                    "input_rows": 0,
                    "complete_covariate_rows": 0,
                    "eligible_cases_after_local_filters": 0,
                    "eligible_controls_after_local_filters": 0,
                    "cases_without_four_controls": 0,
                    "matched_cases": 0,
                    "matched_controls": 0,
                    "duplicate_candidate_rows_removed": 0,
                    "viirs_support_ready": False,
                    "viirs_event_day_available": event_product_available,
                    "missing_required_viirs_dates": ([day.isoformat()] if not event_product_available else []) + unavailable_history_dates,
                    "history_fallback_dates": [],
                    "history_fallback_products": registration["outcome"]["history_gap_fallback"]["products"],
                    "output": output.relative_to(ROOT).as_posix(),
                    "status": "complete_no_observation",
                    "interpretation": "No valid observation opportunity; this day is not a negative fire observation.",
                }
                receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
                completed += 1
                _write_status(days, completed, failed, day.isoformat())
                continue
            raw = _compute_dataframe(_daily_feature_collection(day, context), retries=retries)
            if raw.empty:
                matched = pd.DataFrame()
                strata_report = {"outside_or_below_forest_threshold": 0, "peat_unknown": 0}
                match_report = {
                    "input_rows": 0,
                    "complete_covariate_rows": 0,
                    "eligible_cases_after_local_filters": 0,
                    "eligible_controls_after_local_filters": 0,
                    "cases_without_four_controls": 0,
                    "matched_cases": 0,
                    "matched_controls": 0,
                    "duplicate_candidate_rows_removed": 0,
                }
            else:
                filtered, strata_report = _attach_local_strata(raw)
                if filtered.empty:
                    matched = pd.DataFrame()
                    match_report = {
                        "input_rows": 0,
                        "complete_covariate_rows": 0,
                        "eligible_cases_after_local_filters": 0,
                        "eligible_controls_after_local_filters": 0,
                        "cases_without_four_controls": 0,
                        "matched_cases": 0,
                        "matched_controls": 0,
                        "duplicate_candidate_rows_removed": 0,
                    }
                else:
                    filtered = _attach_ee_covariates(filtered, day=day, context=context, retries=retries)
                    matched, match_report = match_daily_controls(
                        filtered,
                        date_text=day.isoformat(),
                        controls_per_case=registration["controls"]["per_case"],
                        maximum_distance_cells=registration["controls"]["maximum_distance_km"],
                        seed=registration["controls"]["random_seed"],
                    )
            output.parent.mkdir(parents=True, exist_ok=True)
            matched.to_parquet(output, index=False)
            receipt = {
                "date": day.isoformat(),
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "earth_engine_candidate_rows": int(len(raw)),
                **strata_report,
                **match_report,
                "viirs_support_ready": True,
                "viirs_event_day_available": True,
                "missing_required_viirs_dates": [],
                "history_fallback_dates": missing_history_viirs_dates,
                "history_fallback_products": registration["outcome"]["history_gap_fallback"]["products"],
                "output": output.relative_to(ROOT).as_posix(),
                "status": "complete",
            }
            receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
            completed += 1
        except Exception as exc:
            failed[day.isoformat()] = f"{type(exc).__name__}: {exc}"
            _log(f"FAILED {day.isoformat()}: {failed[day.isoformat()]}")
        _write_status(days, completed, failed, day.isoformat())
    _write_status(days, completed, failed, None)
    return 0 if completed == len(days) and not failed else 2


def main() -> int:
    global STATUS_PATH, LOG_PATH

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="susenas-project", help="Earth Engine-enabled Google Cloud project")
    parser.add_argument("--start", type=date.fromisoformat)
    parser.add_argument("--end", type=date.fromisoformat)
    parser.add_argument("--years", type=int, nargs="+", help="fire-season years to process")
    parser.add_argument("--worker-id", help="suffix for independent parallel-worker status and log files")
    parser.add_argument("--retries", type=int, default=8)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.worker_id:
        safe_worker = "".join(character for character in args.worker_id if character.isalnum() or character in {"-", "_"})
        if not safe_worker or safe_worker != args.worker_id:
            parser.error("--worker-id may contain only letters, numbers, '-' and '_'")
        STATUS_PATH = ROOT / "outputs" / "quality" / f"daily_risk_set_extraction_status_{safe_worker}.json"
        LOG_PATH = ROOT / "outputs" / "quality" / f"daily_risk_set_extraction_{safe_worker}.log"
    registration = json.loads(REGISTRATION_PATH.read_text(encoding="utf-8"))
    if args.years and (args.start or args.end):
        parser.error("use either --years or --start/--end, not both")
    if args.years:
        invalid = sorted(set(args.years) - set(registration["study_years"]))
        if invalid:
            parser.error(f"years outside registration: {invalid}")
        days = _fire_season_days(sorted(set(args.years)))
    elif args.start or args.end:
        if not args.start or not args.end:
            parser.error("--start and --end must be supplied together")
        days = _dates(args.start, args.end)
    else:
        days = _fire_season_days(registration["study_years"])
    return run(args.project, days, args.retries, args.overwrite)


if __name__ == "__main__":
    raise SystemExit(main())
