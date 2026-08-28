"""Cell-specific pre-event ERA5-Land features for daily risk-set rows."""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ERA5_VARIABLES = ("u10", "v10", "t2m", "d2m", "tp", "swvl1", "swvl2", "swvl3")


def _month_path(root: Path, stamp: datetime) -> Path:
    return root / f"{stamp.year:04d}" / f"era5_land_{stamp.year:04d}_{stamp.month:02d}.nc"


def _as_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    return datetime(value.year, value.month, value.day, value.hour, tzinfo=timezone.utc)


def load_prefire_hours(era5_root: Path, event_day: date, hours: int = 72) -> dict[str, np.ndarray]:
    """Load an exact, complete hourly interval ending at event-day midnight."""

    try:
        from netCDF4 import Dataset, num2date
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("netCDF4 is required for ERA5-Land feature extraction") from exc

    end = datetime.combine(event_day, datetime.min.time(), tzinfo=timezone.utc)
    start = end - timedelta(hours=hours)
    expected = [start + timedelta(hours=index) for index in range(hours)]
    months = sorted({(stamp.year, stamp.month) for stamp in expected})
    collected: dict[str, list[np.ndarray]] = {name: [] for name in ERA5_VARIABLES}
    collected_times: list[datetime] = []
    latitude: np.ndarray | None = None
    longitude: np.ndarray | None = None

    for year, month in months:
        path = _month_path(era5_root, datetime(year, month, 1, tzinfo=timezone.utc))
        if not path.is_file():
            raise FileNotFoundError(f"ERA5-Land month missing: {path}")
        with Dataset(path) as dataset:
            if latitude is None:
                latitude = np.asarray(dataset.variables["latitude"][:], dtype=float)
                longitude = np.asarray(dataset.variables["longitude"][:], dtype=float)
            time_var = dataset.variables["valid_time"]
            decoded = [
                _as_datetime(value)
                for value in num2date(
                    time_var[:],
                    time_var.units,
                    calendar=getattr(time_var, "calendar", "standard"),
                    only_use_cftime_datetimes=False,
                    only_use_python_datetimes=True,
                )
            ]
            indices = [index for index, stamp in enumerate(decoded) if start <= stamp < end]
            collected_times.extend(decoded[index] for index in indices)
            if not indices:
                continue
            first, last = min(indices), max(indices) + 1
            if indices != list(range(first, last)):
                raise ValueError(f"non-contiguous ERA5 time support in {path.name}")
            for name in ERA5_VARIABLES:
                values = np.ma.filled(dataset.variables[name][first:last, :, :], np.nan).astype(np.float32)
                collected[name].append(values)

    if collected_times != expected:
        raise ValueError(
            f"ERA5 prefire support is incomplete for {event_day.isoformat()}: "
            f"expected {len(expected)} hourly records, got {len(collected_times)}"
        )
    if latitude is None or longitude is None:
        raise ValueError("ERA5 coordinate arrays were not loaded")
    result = {name: np.concatenate(parts, axis=0) for name, parts in collected.items()}
    result["latitude"] = latitude
    result["longitude"] = longitude
    return result


def _saturation_vapour_pressure(temperature_kelvin: np.ndarray) -> np.ndarray:
    celsius = temperature_kelvin - 273.15
    return 0.6108 * np.exp((17.27 * celsius) / (celsius + 237.3))


def _nanmean_axis0(values: np.ndarray) -> np.ndarray:
    finite = np.isfinite(values)
    counts = finite.sum(axis=0)
    sums = np.where(finite, values, 0.0).sum(axis=0)
    return np.divide(sums, counts, out=np.full(counts.shape, np.nan, dtype=float), where=counts > 0)


def _nanmax_axis0(values: np.ndarray) -> np.ndarray:
    finite = np.isfinite(values)
    filled = np.where(finite, values, -np.inf)
    result = filled.max(axis=0)
    result[~finite.any(axis=0)] = np.nan
    return result


def attach_era5_features(
    frame: pd.DataFrame,
    *,
    longitude: np.ndarray,
    latitude: np.ndarray,
    hourly: dict[str, np.ndarray],
) -> pd.DataFrame:
    """Attach nearest-native-cell 24/72-hour summaries without upscaling claims."""

    if len(frame) != len(longitude) or len(frame) != len(latitude):
        raise ValueError("coordinate arrays must align one-to-one with frame rows")
    hours = hourly["u10"].shape[0]
    if hours != 72 or any(hourly[name].shape[0] != hours for name in ERA5_VARIABLES):
        raise ValueError("exactly 72 aligned hourly records are required")
    lat_axis = np.asarray(hourly["latitude"], dtype=float)
    lon_axis = np.asarray(hourly["longitude"], dtype=float)
    lat_index = np.abs(lat_axis[:, None] - latitude[None, :]).argmin(axis=0)
    lon_index = np.abs(lon_axis[:, None] - longitude[None, :]).argmin(axis=0)
    valid_grid = np.ones((len(lat_axis), len(lon_axis)), dtype=bool)
    for name in ERA5_VARIABLES:
        valid_grid &= np.isfinite(hourly[name]).all(axis=0)

    source_distance_km = np.full(len(frame), np.nan, dtype=float)
    earth_radius_km = 6371.0088
    for position in range(len(frame)):
        nearest_lat = int(lat_index[position])
        nearest_lon = int(lon_index[position])
        candidates: list[tuple[float, int, int]] = []
        for row in range(max(0, nearest_lat - 3), min(len(lat_axis), nearest_lat + 4)):
            for column in range(max(0, nearest_lon - 3), min(len(lon_axis), nearest_lon + 4)):
                if not valid_grid[row, column]:
                    continue
                dlat = math.radians(lat_axis[row] - latitude[position])
                dlon = math.radians(lon_axis[column] - longitude[position])
                a = (
                    math.sin(dlat / 2) ** 2
                    + math.cos(math.radians(latitude[position]))
                    * math.cos(math.radians(lat_axis[row]))
                    * math.sin(dlon / 2) ** 2
                )
                distance = 2 * earth_radius_km * math.asin(min(1.0, math.sqrt(a)))
                candidates.append((distance, row, column))
        if candidates:
            distance, row, column = min(candidates)
            if distance <= 25.0:
                lat_index[position] = row
                lon_index[position] = column
                source_distance_km[position] = distance

    sampled = {name: hourly[name][:, lat_index, lon_index].astype(float) for name in ERA5_VARIABLES}
    wind = np.hypot(sampled["u10"], sampled["v10"])
    vpd = np.maximum(0.0, _saturation_vapour_pressure(sampled["t2m"]) - _saturation_vapour_pressure(sampled["d2m"]))
    result = frame.copy()
    result["era5_source_distance_km"] = source_distance_km
    for window in (24, 72):
        section = slice(hours - window, hours)
        suffix = f"{window}h"
        result[f"era5_rain_{suffix}_mm"] = np.nansum(sampled["tp"][section] * 1000.0, axis=0)
        result[f"era5_vpd_mean_{suffix}_kpa"] = _nanmean_axis0(vpd[section])
        result[f"era5_wind_max_{suffix}_ms"] = _nanmax_axis0(wind[section])
        for layer in (1, 2, 3):
            result[f"era5_soil_water_l{layer}_mean_{suffix}"] = _nanmean_axis0(sampled[f"swvl{layer}"][section])
        result[f"era5_rootzone_soil_water_mean_{suffix}"] = (
            0.07 * result[f"era5_soil_water_l1_mean_{suffix}"]
            + 0.21 * result[f"era5_soil_water_l2_mean_{suffix}"]
            + 0.72 * result[f"era5_soil_water_l3_mean_{suffix}"]
        )
    feature_columns = [column for column in result.columns if column.startswith("era5_")]
    finite = np.isfinite(result[feature_columns].to_numpy(dtype=float)).all(axis=1)
    result["era5_support_hours"] = 72
    result["weather_support_status"] = np.where(finite, "complete_pre_event", "invalid_or_missing")
    return result
