from __future__ import annotations

import numpy as np
import pandas as pd

from analysis.phase2_environmental import conditional_objective, exclude_incomplete_matched_sets, holm_adjust


def test_conditional_objective_gradient_matches_finite_difference() -> None:
    rng = np.random.default_rng(42)
    x = rng.normal(size=(8, 5, 4))
    y = np.zeros((8, 5), dtype=float)
    y[np.arange(8), rng.integers(0, 5, size=8)] = 1.0
    beta = np.array([0.2, -0.4, 0.1, 0.7])
    value, gradient = conditional_objective(beta, x, y)
    assert np.isfinite(value)
    epsilon = 1e-6
    numerical = np.empty_like(beta)
    for index in range(len(beta)):
        step = np.zeros_like(beta)
        step[index] = epsilon
        upper = conditional_objective(beta + step, x, y)[0]
        lower = conditional_objective(beta - step, x, y)[0]
        numerical[index] = (upper - lower) / (2 * epsilon)
    np.testing.assert_allclose(gradient, numerical, rtol=1e-5, atol=1e-6)


def test_holm_adjustment_is_monotone_in_sorted_p_values() -> None:
    raw = [0.04, 0.01, 0.20]
    adjusted = holm_adjust(raw)
    assert adjusted == [0.08, 0.03, 0.2]
    ordered = sorted(zip(raw, adjusted))
    assert [value for _, value in ordered] == sorted(value for _, value in ordered)


def test_missing_sentinel_excludes_the_whole_matched_set() -> None:
    rows = []
    for matched_set in ("a", "b"):
        for index in range(5):
            rows.append(
                {
                    "matched_set_id": matched_set,
                    "date": "2024-08-01",
                    "forest_fraction": 0.8,
                    "peat_extent_percent": 50.0,
                    "chirps_precip_1d_mm": 1.0,
                    "chirps_precip_7d_mm": -9999.0 if matched_set == "a" and index == 2 else 7.0,
                    "chirps_precip_30d_mm": 30.0,
                    "chirps_precip_90d_mm": 90.0,
                    "evi_prefire": 0.5,
                    "era5_vpd_mean_72h_kpa": 0.4,
                    "era5_wind_max_24h_ms": 3.0,
                    "era5_rootzone_soil_water_mean_72h": 0.3,
                }
            )
    filtered, report = exclude_incomplete_matched_sets(pd.DataFrame(rows))
    assert set(filtered["matched_set_id"]) == {"b"}
    assert report["invalid_source_row_count"] == 1
    assert report["excluded_matched_set_count"] == 1
    assert report["excluded_row_count"] == 5
    assert report["imputed_value_count"] == 0
