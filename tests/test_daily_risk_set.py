from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wildfire_research.daily_risk_set import match_daily_controls


def _row(outcome: int, row: int, col: int) -> dict:
    return {
        "grid_col": col,
        "grid_row": row,
        "supercell_id": 1,
        "outcome": outcome,
        "coverage_fraction": 1.0,
        "negative_lookback_days": 1,
        "chirps_precip_1d_mm": 1.0,
        "chirps_precip_7d_mm": 7.0,
        "chirps_precip_30d_mm": 30.0,
        "chirps_precip_90d_mm": 90.0,
        "evi_prefire": 0.5,
        "evi_composite_start_day": 100,
        "forest_fraction": 0.9,
        "peat_extent_percent": 50.0,
    }


def test_matching_is_exactly_one_case_four_nearby_controls() -> None:
    rows = [_row(1, 10, 10)]
    rows.extend(_row(0, 10, col) for col in (11, 12, 13, 14, 15))
    rows.append(_row(0, 100, 100))
    result, report = match_daily_controls(pd.DataFrame(rows), date_text="2015-07-01")
    assert report["matched_cases"] == 1
    assert report["matched_controls"] == 4
    assert len(result) == 5
    assert result.groupby("matched_set_id")["outcome_status"].value_counts().to_dict() == {
        ("2015-07-01:r10:c10", "positive"): 1,
        ("2015-07-01:r10:c10", "negative"): 4,
    }


def test_case_without_full_control_set_is_excluded() -> None:
    frame = pd.DataFrame([_row(1, 10, 10), _row(0, 10, 11), _row(0, 10, 12)])
    result, report = match_daily_controls(frame, date_text="2015-07-01")
    assert result.empty
    assert report["cases_without_four_controls"] == 1


def test_missing_evi_is_fail_closed_before_matching() -> None:
    rows = [_row(1, 10, 10)] + [_row(0, 10, col) for col in (11, 12, 13, 14)]
    rows[0]["evi_prefire"] = -9999
    result, report = match_daily_controls(pd.DataFrame(rows), date_text="2015-07-01")
    assert result.empty
    assert report["eligible_cases_after_local_filters"] == 0


def test_matching_deduplicates_identical_projected_cells() -> None:
    rows = [_row(1, 10, 10)]
    rows.extend(_row(0, 10, col) for col in (11, 12, 13, 14, 15))
    rows.append(_row(1, 10, 10))

    result, report = match_daily_controls(pd.DataFrame(rows), date_text="2015-07-01")

    counts = result.groupby("matched_set_id")["outcome_status"].value_counts().unstack(fill_value=0)
    assert ((counts["positive"] == 1) & (counts["negative"] == 4)).all()
    assert report["duplicate_candidate_rows_removed"] == 1
