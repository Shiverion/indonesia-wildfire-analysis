"""Build complete antecedent CHIRPS lag features for the local support window.

The output is an internal source-grid table, not a browser payload.  A cutoff
date is retained only when every preceding day needed by all requested windows
is present and has no CHIRPS nodata pixels.  Missing dates or missing raster
cells are never imputed.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CHIRPS_RE = re.compile(r"^chirps-v3\.0\.rnl\.(?P<date>\d{4}\.\d{2}\.\d{2})\.cog$")
DEFAULT_BBOX = (109.0, -5.0, 120.0, 8.0)
DEFAULT_WINDOWS = (1, 7, 30, 90)


def _date_range(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def rolling_lags(
    rainfall: np.ndarray,
    dates: Iterable[date],
    *,
    windows: tuple[int, ...] = DEFAULT_WINDOWS,
) -> tuple[list[date], dict[int, np.ndarray], np.ndarray]:
    """Return cutoff dates and complete pre-cutoff sums on a date-first array.

    ``rainfall[i]`` is the rainfall observed on ``dates[i]``.  For cutoff
    ``dates[i]``, a ``w``-day lag sums ``rainfall[i-w:i]`` and therefore never
    includes rainfall from the cutoff day itself.
    """

    values = np.asarray(rainfall, dtype=np.float32)
    date_list = list(dates)
    if values.ndim != 3 or values.shape[0] != len(date_list):
        raise ValueError("rainfall must have shape (date, row, column) matching dates")
    if not windows or any(window < 1 for window in windows):
        raise ValueError("windows must contain positive day counts")
    if len(set(date_list)) != len(date_list):
        raise ValueError("dates must be unique")
    if any((right - left).days != 1 for left, right in zip(date_list, date_list[1:])):
        raise ValueError("dates must be contiguous before lag derivation")

    maximum = max(windows)
    if len(date_list) <= maximum:
        empty = {window: np.empty((0,) + values.shape[1:], dtype=np.float32) for window in windows}
        return [], empty, np.empty((0,), dtype=np.int32)

    cutoff_indices = np.arange(maximum, len(date_list), dtype=np.int32)
    output_dates = [date_list[int(index)] for index in cutoff_indices]
    features: dict[int, np.ndarray] = {}
    finite = np.isfinite(values)
    for window in windows:
        result = np.full((len(cutoff_indices),) + values.shape[1:], np.nan, dtype=np.float32)
        for output_index, cutoff_index in enumerate(cutoff_indices):
            support = values[cutoff_index - window : cutoff_index]
            support_finite = finite[cutoff_index - window : cutoff_index].all(axis=0)
            total = np.where(support_finite, np.sum(support, axis=0, dtype=np.float64), np.nan)
            result[output_index] = total.astype(np.float32)
        features[window] = result
    complete = np.isfinite(features[maximum]).all(axis=(1, 2))
    return output_dates, features, complete


def _read_manifest(root: Path) -> tuple[date, date]:
    path = root / "data" / "raw" / "chirps" / "download_manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"CHIRPS manifest missing: {path}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    temporal = manifest.get("temporal")
    if not isinstance(temporal, list) or len(temporal) != 2:
        raise ValueError("CHIRPS manifest must declare a two-date temporal support window")
    return date.fromisoformat(temporal[0]), date.fromisoformat(temporal[1])


def _raster_files(root: Path, start: date, end: date) -> list[tuple[date, Path]]:
    directory = root / "data" / "raw" / "chirps"
    found: dict[date, Path] = {}
    for path in sorted(directory.rglob("*.cog")):
        match = CHIRPS_RE.fullmatch(path.name)
        if not match:
            continue
        current = date.fromisoformat(match["date"].replace(".", "-"))
        if start <= current <= end:
            if current in found:
                raise ValueError(f"duplicate CHIRPS raster for {current.isoformat()}")
            found[current] = path
    expected = _date_range(start, end)
    missing = [day.isoformat() for day in expected if day not in found]
    if missing:
        raise ValueError(f"CHIRPS support window has missing dates: {missing[:8]}{' ...' if len(missing) > 8 else ''}")
    return [(day, found[day]) for day in expected]


def build(
    root: Path,
    *,
    output_path: Path | None = None,
    quality_path: Path | None = None,
    bbox: tuple[float, float, float, float] = DEFAULT_BBOX,
    windows: tuple[int, ...] = DEFAULT_WINDOWS,
) -> dict:
    try:
        import rasterio
        from rasterio.windows import from_bounds
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("rasterio is required to read CHIRPS COGs") from exc

    start, end = _read_manifest(root)
    files = _raster_files(root, start, end)
    min_lon, min_lat, max_lon, max_lat = bbox
    if not min_lon < max_lon or not min_lat < max_lat:
        raise ValueError("bbox must be [min_lon, min_lat, max_lon, max_lat]")

    arrays: list[np.ndarray] = []
    dates: list[date] = []
    transform = None
    crs = None
    shape = None
    for current, path in files:
        with rasterio.open(path) as dataset:
            window = from_bounds(min_lon, min_lat, max_lon, max_lat, dataset.transform)
            window = window.round_offsets().round_lengths()
            array = dataset.read(1, window=window).astype(np.float32, copy=False)
            nodata = dataset.nodata
            if nodata is not None:
                array = np.where(array == nodata, np.nan, array)
            array = np.where(array <= -9990, np.nan, array)
            if shape is None:
                shape = array.shape
                transform = dataset.window_transform(window)
                crs = str(dataset.crs) if dataset.crs else None
            elif array.shape != shape:
                raise ValueError(f"CHIRPS raster shape changed at {path.name}: {array.shape} != {shape}")
            arrays.append(array)
            dates.append(current)

    rainfall = np.stack(arrays, axis=0)
    cutoff_dates, features, complete = rolling_lags(rainfall, dates, windows=windows)
    complete_grid = np.isfinite(features[max(windows)])
    valid_indices = np.arange(len(cutoff_dates), dtype=np.int32)
    output_path = output_path or root / "data" / "derived" / "chirps" / "chirps_lag_features_2015.parquet"
    quality_path = quality_path or root / "outputs" / "quality" / "chirps_lag_features_2015.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    quality_path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, float | int | str]] = []
    height, width = shape or (0, 0)
    # Keep this internal table in source-grid coordinates.  The later event
    # linker performs the registered native-grid-to-analysis-grid join.
    for output_index in valid_indices:
        for row in range(height):
            for column in range(width):
                if not complete_grid[output_index, row, column]:
                    continue
                record: dict[str, float | int | str] = {
                    "cutoff_date": cutoff_dates[int(output_index)].isoformat(),
                    "source_row": row,
                    "source_column": column,
                }
                for window in windows:
                    value = features[window][output_index, row, column]
                    record[f"rain_{window}d_mm"] = float(value) if np.isfinite(value) else np.nan
                rows.append(record)

    import pandas as pd

    frame = pd.DataFrame.from_records(rows)
    frame.to_parquet(output_path, index=False)
    report = {
        "schema_version": "chirps-lag-features/v1",
        "source": "CHIRPS v3 FINAL RNL daily COG",
        "support_window": [start.isoformat(), end.isoformat()],
        "bbox": list(bbox),
        "crs": crs,
        "source_grid_shape": list(shape or (0, 0)),
        "windows_days": list(windows),
        "input_date_count": len(dates),
        "output_cutoff_count": len(cutoff_dates),
        "complete_cutoff_count": int(complete_grid.any(axis=(1, 2)).sum()),
        "first_complete_cutoff": cutoff_dates[int(np.flatnonzero(complete_grid.any(axis=(1, 2)))[0])].isoformat() if complete_grid.any() else None,
        "last_complete_cutoff": cutoff_dates[int(np.flatnonzero(complete_grid.any(axis=(1, 2)))[-1])].isoformat() if complete_grid.any() else None,
        "row_count": len(frame),
        "nodata_policy": "Any missing value in a requested pre-cutoff window makes that cell-cutoff missing; no imputation.",
        "event_linkage": "Not yet applied; this is a source-grid cache and does not unlock Phase 1B.",
        "output": output_path.relative_to(root).as_posix(),
    }
    quality_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--quality", type=Path)
    args = parser.parse_args()
    report = build(ROOT, output_path=args.output, quality_path=args.quality)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
