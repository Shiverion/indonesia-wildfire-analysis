import sys
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from wildfire_research.covariates import (
    complete_daily_lag_sums,
    validate_prefire_support,
    vpd_kpa,
    wind_speed_ms,
)


def test_wind_speed_and_vpd_are_physical_nonnegative_values():
    assert wind_speed_ms(3.0, 4.0) == pytest.approx(5.0)
    assert vpd_kpa(303.15, 293.15) > 0
    assert vpd_kpa(293.15, 303.15) == pytest.approx(0.0)


def test_daily_lag_sums_exclude_cutoff_and_require_every_day():
    cutoff = date(2015, 8, 10)
    values = {cutoff - timedelta(days=offset): float(offset) for offset in range(1, 8)}
    assert complete_daily_lag_sums(values, cutoff, windows=(1, 7)) == {1: 1.0, 7: 28.0}
    del values[date(2015, 8, 5)]
    with pytest.raises(ValueError, match="missing pre-cutoff"):
        complete_daily_lag_sums(values, cutoff, windows=(7,))


def test_prefire_support_rejects_lookahead_and_naive_timestamps():
    cutoff = datetime(2015, 8, 10, tzinfo=timezone.utc)
    before = validate_prefire_support(
        cutoff,
        datetime(2015, 8, 1, tzinfo=timezone.utc),
        datetime(2015, 8, 9, 23, 59, tzinfo=timezone.utc),
    )
    assert before.valid is True
    assert validate_prefire_support(cutoff, cutoff - timedelta(days=1), cutoff + timedelta(seconds=1)).valid is False
    assert validate_prefire_support(cutoff, cutoff.replace(tzinfo=None), cutoff.replace(tzinfo=None)).valid is False
