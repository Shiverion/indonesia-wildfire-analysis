from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wildfire_research.era5_features import attach_era5_features


def test_era5_features_use_complete_prior_windows_and_nearest_valid_land() -> None:
    shape = (72, 2, 2)
    hourly = {
        "u10": np.full(shape, 3.0),
        "v10": np.full(shape, 4.0),
        "t2m": np.full(shape, 300.0),
        "d2m": np.full(shape, 295.0),
        "tp": np.full(shape, 0.001),
        "swvl1": np.full(shape, 0.1),
        "swvl2": np.full(shape, 0.2),
        "swvl3": np.full(shape, 0.3),
        "latitude": np.array([1.0, 0.0]),
        "longitude": np.array([100.0, 101.0]),
    }
    # Force the nearest cell to be invalid; the helper must use a nearby valid
    # land cell and record the non-zero source distance.
    for name in ("u10", "v10", "t2m", "d2m", "tp", "swvl1", "swvl2", "swvl3"):
        hourly[name][:, 0, 0] = np.nan
    result = attach_era5_features(
        pd.DataFrame({"id": [1]}),
        longitude=np.array([100.0]),
        latitude=np.array([1.0]),
        hourly=hourly,
    )
    assert result.loc[0, "weather_support_status"] == "invalid_or_missing"
    # The next native cell is farther than the registered 25-km limit in this
    # synthetic 1-degree grid, so the function correctly refuses substitution.
    assert np.isnan(result.loc[0, "era5_source_distance_km"])


def test_era5_features_compute_registered_metrics() -> None:
    shape = (72, 1, 1)
    hourly = {
        "u10": np.full(shape, 3.0),
        "v10": np.full(shape, 4.0),
        "t2m": np.full(shape, 300.0),
        "d2m": np.full(shape, 295.0),
        "tp": np.full(shape, 0.001),
        "swvl1": np.full(shape, 0.1),
        "swvl2": np.full(shape, 0.2),
        "swvl3": np.full(shape, 0.3),
        "latitude": np.array([0.0]),
        "longitude": np.array([100.0]),
    }
    result = attach_era5_features(
        pd.DataFrame({"id": [1]}),
        longitude=np.array([100.0]),
        latitude=np.array([0.0]),
        hourly=hourly,
    )
    assert result.loc[0, "weather_support_status"] == "complete_pre_event"
    assert abs(result.loc[0, "era5_rain_24h_mm"] - 24.0) < 1e-6
    assert abs(result.loc[0, "era5_rain_72h_mm"] - 72.0) < 1e-6
    assert abs(result.loc[0, "era5_wind_max_24h_ms"] - 5.0) < 1e-6
    assert abs(result.loc[0, "era5_rootzone_soil_water_mean_72h"] - 0.265) < 1e-6
