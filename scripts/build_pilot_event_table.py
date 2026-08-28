"""Build a compact 2015 event-level pilot table from existing local inputs.

This script intentionally does not download data and does not manufacture a
Phase 2 denominator.  It aggregates the existing VIIRS diagnostic by paired
overpass, attaches pre-cutoff regional ERA5-Land summaries, and links the
available MOD13Q1 tile/composite QA summary.  CHIRPS and peat remain explicitly
unlinked when a valid spatial/event join is unavailable.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
VIIRS_DIAGNOSTIC = ROOT / "data" / "derived" / "viirs" / "opportunity_frame_diagnostic.csv"
ERA5_ROOT = ROOT / "data" / "raw" / "era5_land" / "2015"
MOD13_SUMMARY = ROOT / "data" / "derived" / "mod13q1" / "mod13q1_2015_tile_summary.csv"
CHIRPS_LAGS = ROOT / "data" / "derived" / "chirps" / "chirps_lag_features_2015.parquet"
OUTPUT_CSV = ROOT / "data" / "derived" / "pilot" / "pilot_event_level_2015.csv"
OUTPUT_REPORT = ROOT / "outputs" / "quality" / "pilot_event_level_2015.json"
BBOX = (109.0, -5.0, 120.0, 6.0)


def _vpd_kpa(t2m: float, d2m: float) -> float:
    def es(kelvin: float) -> float:
        celsius = kelvin - 273.15
        return 0.6108 * math.exp((17.27 * celsius) / (celsius + 237.3))

    return max(0.0, es(t2m) - es(d2m))


def _as_utc(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)


def _aggregate_viirs(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"VIIRS diagnostic missing: {path}")
    aggregates: OrderedDict[str, dict[str, Any]] = OrderedDict()
    usecols = [
        "pair_key", "acquisition_utc", "outcome_status", "valid_opportunity",
        "forest_fraction", "coverage_fraction", "processed_pixel_count",
        "positive_pixel_count", "negative_pixel_count",
    ]
    for chunk in pd.read_csv(path, usecols=usecols, chunksize=200_000):
        chunk = chunk[chunk["valid_opportunity"].astype(str).str.lower().isin({"true", "1"})]
        for row in chunk.itertuples(index=False):
            key = str(row.pair_key)
            item = aggregates.setdefault(key, {
                "event_id": key,
                "pair_key": key,
                "acquisition_utc": str(row.acquisition_utc),
                "valid_opportunity_cells": 0,
                "positive_cells": 0,
                "negative_cells": 0,
                "processed_pixel_count": 0,
                "positive_pixel_count": 0,
                "negative_pixel_count": 0,
                "forest_fraction_sum": 0.0,
                "forest_fraction_n": 0,
                "coverage_fraction_sum": 0.0,
                "coverage_fraction_n": 0,
            })
            positive = int(row.positive_pixel_count)
            negative = int(row.negative_pixel_count)
            item["valid_opportunity_cells"] += 1
            item["positive_cells"] += int(positive > 0)
            item["negative_cells"] += int(negative > 0)
            item["processed_pixel_count"] += int(row.processed_pixel_count)
            item["positive_pixel_count"] += positive
            item["negative_pixel_count"] += negative
            if math.isfinite(float(row.forest_fraction)):
                item["forest_fraction_sum"] += float(row.forest_fraction)
                item["forest_fraction_n"] += 1
            if math.isfinite(float(row.coverage_fraction)):
                item["coverage_fraction_sum"] += float(row.coverage_fraction)
                item["coverage_fraction_n"] += 1

    rows: list[dict[str, Any]] = []
    for item in aggregates.values():
        acquisition = _as_utc(item["acquisition_utc"])
        item["acquisition_utc"] = acquisition.isoformat().replace("+00:00", "Z")
        item["event_date"] = acquisition.date().isoformat()
        item["outcome_status"] = "positive" if item["positive_pixel_count"] > 0 else "negative"
        item["forest_fraction_mean"] = (
            item["forest_fraction_sum"] / item["forest_fraction_n"] if item["forest_fraction_n"] else None
        )
        item["coverage_fraction_mean"] = (
            item["coverage_fraction_sum"] / item["coverage_fraction_n"] if item["coverage_fraction_n"] else None
        )
        for key in ("forest_fraction_sum", "forest_fraction_n", "coverage_fraction_sum", "coverage_fraction_n"):
            item.pop(key, None)
        rows.append(item)
    rows.sort(key=lambda row: row["acquisition_utc"])
    return rows


def _era5_hourly_regional_means() -> dict[datetime, dict[str, float]]:
    try:
        from netCDF4 import Dataset, num2date
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("netCDF4 is required; install it before running this local extraction") from exc

    hourly: dict[datetime, dict[str, float]] = {}
    files = sorted(ERA5_ROOT.glob("era5_land_2015_*.nc"))
    if len(files) != 12:
        raise ValueError(f"Expected 12 ERA5-Land 2015 files, found {len(files)}")
    for path in files:
        with Dataset(path) as dataset:
            lat = np.asarray(dataset.variables["latitude"][:])
            lon = np.asarray(dataset.variables["longitude"][:])
            lat_idx = np.flatnonzero((lat >= BBOX[1]) & (lat <= BBOX[3]))
            lon_idx = np.flatnonzero((lon >= BBOX[0]) & (lon <= BBOX[2]))
            if not len(lat_idx) or not len(lon_idx):
                raise ValueError(f"ERA5 file does not intersect bbox: {path.name}")
            time_var = dataset.variables["valid_time"]
            times = num2date(
                time_var[:], time_var.units,
                calendar=getattr(time_var, "calendar", "standard"),
                only_use_cftime_datetimes=False,
                only_use_python_datetimes=True,
            )
            names = ("u10", "v10", "t2m", "d2m", "tp", "swvl1", "swvl2", "swvl3")
            arrays: dict[str, np.ndarray] = {}
            for name in names:
                values = np.ma.filled(dataset.variables[name][:, lat_idx.min():lat_idx.max() + 1, lon_idx.min():lon_idx.max() + 1], np.nan).astype(np.float64)
                arrays[name] = np.nanmean(values, axis=(1, 2))
            for index, raw_time in enumerate(times):
                stamp = _as_utc(raw_time)
                row = {
                    "wind_10m_ms": float(math.hypot(arrays["u10"][index], arrays["v10"][index])),
                    "vpd_kpa": float(_vpd_kpa(arrays["t2m"][index], arrays["d2m"][index])),
                    "rain_mm": float(arrays["tp"][index] * 1000.0),
                    "soil_water_layer1": float(arrays["swvl1"][index]),
                    "soil_water_layer2": float(arrays["swvl2"][index]),
                    "soil_water_layer3": float(arrays["swvl3"][index]),
                }
                if all(math.isfinite(value) for value in row.values()):
                    hourly[stamp.replace(minute=0, second=0, microsecond=0)] = row
    return hourly


def _prefire_weather(cutoff: datetime, hourly: dict[datetime, dict[str, float]]) -> dict[str, Any]:
    prior = sorted(stamp for stamp in hourly if stamp < cutoff)
    values: dict[str, Any] = {"weather_support_status": "missing"}
    if len(prior) < 72:
        return values
    last_72 = prior[-72:]
    if (cutoff - last_72[0]).total_seconds() > 72 * 3600 + 3600:
        return values
    for index, window in ((24, "24h"), (72, "72h")):
        stamps = last_72[-index:]
        rainfall = [hourly[stamp]["rain_mm"] for stamp in stamps]
        vpds = [hourly[stamp]["vpd_kpa"] for stamp in stamps]
        winds = [hourly[stamp]["wind_10m_ms"] for stamp in stamps]
        soils = [hourly[stamp]["soil_water_layer1"] for stamp in stamps]
        values[f"era5_rain_{window}_mm"] = float(math.fsum(rainfall))
        values[f"era5_vpd_mean_{window}_kpa"] = float(np.mean(vpds))
        values[f"era5_wind_max_{window}_ms"] = float(max(winds))
        values[f"era5_soil_water_mean_{window}"] = float(np.mean(soils))
    values["weather_support_status"] = "complete_pre_cutoff_72h"
    return values


def _prefire_mod13(cutoff: datetime) -> dict[str, Any]:
    if not MOD13_SUMMARY.is_file():
        return {"vegetation_support_status": "missing"}
    frame = pd.read_csv(MOD13_SUMMARY)
    frame = frame[(frame.get("year") == 2015) & (frame.get("intersects_bbox") == True)]  # noqa: E712
    if frame.empty:
        return {"vegetation_support_status": "missing"}
    frame["composite_end"] = pd.to_datetime(frame["composite_end"], utc=True)
    eligible = frame[frame["composite_end"] < pd.Timestamp(cutoff)]
    if eligible.empty:
        return {"vegetation_support_status": "no_pre_cutoff_composite"}
    latest = eligible[eligible["composite_end"] == eligible["composite_end"].max()]
    weights = latest["qa_pass_pixels"].fillna(0).astype(float)
    values = latest["evi_mean_qa"].astype(float)
    mean = float(np.average(values, weights=weights)) if weights.sum() else float(values.mean())
    return {
        "prefire_evi_mean_qa": mean,
        "prefire_composite_end": latest["composite_end"].iloc[0].isoformat(),
        "vegetation_support_status": "tile_composite_summary_only",
    }


def build() -> dict[str, Any]:
    rows = _aggregate_viirs(VIIRS_DIAGNOSTIC)
    hourly = _era5_hourly_regional_means()
    output_rows: list[dict[str, Any]] = []
    for row in rows:
        cutoff = _as_utc(row["acquisition_utc"])
        row.update(_prefire_weather(cutoff, hourly))
        row.update(_prefire_mod13(cutoff))
        row["chirps_support_status"] = "not_spatially_linked"
        row["peat_support_status"] = "not_spatially_linked"
        row["analysis_role"] = "descriptive_pilot_only"
        output_rows.append(row)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(output_rows)
    frame.to_csv(OUTPUT_CSV, index=False)
    status_counts = frame["outcome_status"].value_counts().to_dict() if not frame.empty else {}
    report = {
        "schema_version": "pilot-event-level/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "descriptive_pilot_ready_not_phase2",
        "study_window": "2015 local diagnostic paired swaths",
        "inputs": {
            "viirs_diagnostic": str(VIIRS_DIAGNOSTIC.relative_to(ROOT)),
            "era5_land": "2015 monthly files; regional hourly summaries",
            "mod13q1": str(MOD13_SUMMARY.relative_to(ROOT)),
            "chirps_lags": str(CHIRPS_LAGS.relative_to(ROOT)),
        },
        "summary": {
            "event_rows": len(frame),
            "positive_events": int(status_counts.get("positive", 0)),
            "negative_events": int(status_counts.get("negative", 0)),
            "weather_complete_events": int((frame.get("weather_support_status") == "complete_pre_cutoff_72h").sum()) if not frame.empty else 0,
            "vegetation_summary_events": int((frame.get("vegetation_support_status") == "tile_composite_summary_only").sum()) if not frame.empty else 0,
            "chirps_spatially_linked_events": 0,
            "peat_spatially_linked_events": 0,
        },
        "output": {"path": str(OUTPUT_CSV.relative_to(ROOT)), "row_count": len(frame)},
        "inferential_status": "not_estimable",
        "limitations": [
            "VIIRS rows are aggregated from the diagnostic opportunity frame, not the canonical full-study denominator.",
            "ERA5 values are regional means, not cell-specific exposures; they are valid pre-cutoff summaries for descriptive use only.",
            "MOD13Q1 is a tile/composite summary and is not linked to each cell's pre-fire EVI.",
            "CHIRPS and peat are intentionally not joined without a spatially valid event/cell linker.",
            "No Phase 2 coefficient or causal conclusion is released from this table.",
        ],
    }
    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    report = build()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
