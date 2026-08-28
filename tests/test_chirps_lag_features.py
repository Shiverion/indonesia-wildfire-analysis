from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_chirps_lag_features import rolling_lags


def test_rolling_lags_exclude_cutoff_and_require_complete_support() -> None:
    dates = [date(2015, 1, 1) + timedelta(days=i) for i in range(8)]
    rainfall = np.arange(8, dtype=np.float32).reshape(8, 1, 1)
    cutoffs, features, complete = rolling_lags(rainfall, dates, windows=(1, 3))

    assert cutoffs == dates[3:]
    assert features[1][:, 0, 0].tolist() == [2.0, 3.0, 4.0, 5.0, 6.0]
    assert features[3][:, 0, 0].tolist() == [3.0, 6.0, 9.0, 12.0, 15.0]
    assert complete.tolist() == [True] * 5


def test_rolling_lags_marks_missing_pixel_support_incomplete() -> None:
    dates = [date(2015, 1, 1) + timedelta(days=i) for i in range(5)]
    rainfall = np.ones((5, 1, 1), dtype=np.float32)
    rainfall[1, 0, 0] = np.nan
    _, features, complete = rolling_lags(rainfall, dates, windows=(2,))

    assert np.isnan(features[2][0, 0, 0])
    assert complete.tolist() == [False, False, True]
