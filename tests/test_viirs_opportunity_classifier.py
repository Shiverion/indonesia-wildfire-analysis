from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wildfire_research.viirs_opportunity import classify_observation_pixels


def test_classifier_keeps_clear_land_negative_and_fire_positive_only() -> None:
    fire = np.array([[5, 7, 8, 9, 4, 6]], dtype=np.uint8)
    lat = np.full_like(fire, 0, dtype=np.float32)
    lon = np.full_like(fire, 112, dtype=np.float32)
    quality = np.zeros_like(fire)
    land_water = np.ones_like(fire)
    forest = np.full_like(fire, 0.8, dtype=np.float32)
    cells = np.arange(6).reshape(1, 6)
    prior = np.full_like(fire, 24, dtype=np.float32)
    coverage = np.ones_like(fire, dtype=np.float32)

    rows = classify_observation_pixels(
        fire, lat, lon, quality, land_water, forest, cells, prior, coverage,
        pair_key="2015182.0554", acquisition_utc="2015-07-01T05:54:00Z",
    )
    assert [row["outcome_status"] for row in rows] == ["negative", "positive", "positive", "positive"]


def test_classifier_fails_closed_for_missing_history_or_forest() -> None:
    fire = np.array([[5, 7]], dtype=np.uint8)
    common = np.zeros_like(fire, dtype=np.float32)
    land_water = np.ones_like(fire)
    forest = np.array([[0.8, np.nan]], dtype=np.float32)
    cells = np.array([[1, 2]])
    prior = np.array([[np.nan, 24]], dtype=np.float32)
    coverage = np.ones_like(fire, dtype=np.float32)

    rows = classify_observation_pixels(
        fire, common, np.full_like(common, 112), np.zeros_like(fire), land_water,
        forest, cells, prior, coverage, pair_key="p", acquisition_utc="t",
    )
    assert rows == []
