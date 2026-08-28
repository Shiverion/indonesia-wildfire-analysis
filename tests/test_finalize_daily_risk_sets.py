from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.finalize_daily_risk_sets import _deduplicate_logical_opportunities


def _duplicate_frame() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "opportunity_id": "first",
            "acquisition_utc": "2024-09-03T00:00:00Z",
            "matched_set_id": "set-1",
            "cell_id": "cell-1",
            "outcome_status": "positive",
            "forest_fraction": 0.9,
        },
        {
            "opportunity_id": "second",
            "acquisition_utc": "2024-09-03T00:00:00Z",
            "matched_set_id": "set-1",
            "cell_id": "cell-1",
            "outcome_status": "positive",
            "forest_fraction": 0.9,
        },
    ])


def test_logical_duplicate_is_collapsed_even_when_transient_id_differs() -> None:
    result, removed, errors = _deduplicate_logical_opportunities(_duplicate_frame())

    assert len(result) == 1
    assert removed == 1
    assert errors == []


def test_conflicting_logical_duplicate_fails_closed() -> None:
    frame = _duplicate_frame()
    frame.loc[1, "forest_fraction"] = 0.8

    result, removed, errors = _deduplicate_logical_opportunities(frame)

    assert len(result) == 2
    assert removed == 0
    assert errors == ["conflicting_duplicate_logical_opportunity"]
