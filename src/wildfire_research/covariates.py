"""Small, fail-closed helpers for pre-fire climate and vegetation covariates.

These helpers deliberately do not impute missing days or repair look-ahead.  A
covariate is usable only when the requested support is complete and ends no
later than the event cutoff.  They are pure functions so they can be tested
before the large ERA5/CHIRPS extraction jobs finish.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Mapping, Sequence


def saturation_vapor_pressure_kpa(temperature_kelvin: float) -> float:
    """Return saturation vapour pressure (kPa) for air temperature in Kelvin."""
    if not math.isfinite(temperature_kelvin) or temperature_kelvin <= 0:
        raise ValueError("temperature_kelvin must be a finite positive value")
    celsius = temperature_kelvin - 273.15
    return 0.6108 * math.exp((17.27 * celsius) / (celsius + 237.3))


def vpd_kpa(t2m_kelvin: float, d2m_kelvin: float) -> float:
    """Compute vapour-pressure deficit from 2 m temperature/dewpoint.

    Slightly supersaturated reanalysis pairs are clamped to zero rather than
    being turned into a negative ``dryness`` value.
    """
    if not math.isfinite(d2m_kelvin) or d2m_kelvin <= 0:
        raise ValueError("d2m_kelvin must be a finite positive value")
    return max(0.0, saturation_vapor_pressure_kpa(t2m_kelvin) - saturation_vapor_pressure_kpa(d2m_kelvin))


def wind_speed_ms(u10_ms: float, v10_ms: float) -> float:
    """Compute 10 m wind speed from eastward/northward components."""
    if not math.isfinite(u10_ms) or not math.isfinite(v10_ms):
        raise ValueError("wind components must be finite")
    return math.hypot(u10_ms, v10_ms)


def complete_daily_lag_sums(
    daily_values: Mapping[date, float],
    cutoff_date: date,
    windows: Sequence[int] = (1, 7, 30, 90),
) -> dict[int, float]:
    """Sum complete pre-cutoff daily windows without filling missing dates.

    The event date is excluded.  For example, a 7-day value for cutoff
    ``2015-08-10`` uses 3--9 August.  Missing dates and non-finite values raise
    an error so callers cannot accidentally treat a sparse archive as a valid
    drought feature.
    """
    if not isinstance(cutoff_date, date):
        raise TypeError("cutoff_date must be a datetime.date")
    normalized_windows = tuple(dict.fromkeys(int(window) for window in windows))
    if not normalized_windows or any(window <= 0 for window in normalized_windows):
        raise ValueError("windows must contain positive integers")
    result: dict[int, float] = {}
    for window in normalized_windows:
        values: list[float] = []
        for offset in range(1, window + 1):
            day = cutoff_date - timedelta(days=offset)
            if day not in daily_values:
                raise ValueError(f"missing pre-cutoff daily support for {day.isoformat()}")
            value = float(daily_values[day])
            if not math.isfinite(value):
                raise ValueError(f"non-finite daily covariate on {day.isoformat()}")
            values.append(value)
        result[window] = math.fsum(values)
    return result


@dataclass(frozen=True)
class PrefireSupportCheck:
    """Machine-readable result for a temporal-support gate."""

    valid: bool
    reason: str


def validate_prefire_support(
    cutoff_utc: datetime,
    support_start_utc: datetime,
    support_end_utc: datetime,
) -> PrefireSupportCheck:
    """Check that a covariate support interval is complete and pre-fire."""
    values = (cutoff_utc, support_start_utc, support_end_utc)
    if any(value.tzinfo is None or value.utcoffset() is None for value in values):
        return PrefireSupportCheck(False, "all timestamps must be timezone-aware")
    normalized = tuple(value.astimezone(timezone.utc) for value in values)
    cutoff, start, end = normalized
    if start > end:
        return PrefireSupportCheck(False, "support_start_utc is after support_end_utc")
    if end > cutoff:
        return PrefireSupportCheck(False, "support interval extends to or beyond the event cutoff")
    return PrefireSupportCheck(True, "complete pre-fire support interval")
