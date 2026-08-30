from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.phase3_publication_robustness import (
    _standardized_mean_difference,
    attrition_audit,
    eligibility_threshold_sensitivity,
    transition_mass_audit,
)


ROOT = Path(__file__).resolve().parents[1]


def test_standardized_mean_difference_retains_direction() -> None:
    included = pd.Series([2.0, 3.0, 4.0, 5.0])
    excluded = pd.Series([0.0, 1.0, 2.0, 3.0])
    value = _standardized_mean_difference(included, excluded)
    assert value is not None
    assert value > 0


def test_attrition_audit_reports_nonexclusive_reasons_and_smd() -> None:
    rows = []
    flags = []
    for index in range(8):
        included = index < 5
        rows.append(
            {
                "matched_set_id": f"set-{index}",
                "fire_positive": 1,
                "included_primary": included,
                "year": 2015 + index % 2,
                    "forest_fraction": (0.88 + index * 0.01) if included else (0.56 + index * 0.01),
                "peat_extent_percent": index,
                "chirps_precip_7d_mm": 10 + index,
                "chirps_precip_30d_mm": 40 + index,
                "evi_prefire": 0.5,
                "era5_vpd_mean_72h_kpa": 0.7,
                "era5_wind_max_24h_ms": 2.0,
                "era5_rootzone_soil_water_mean_72h": 0.3,
                    "pre_natural_fraction": (0.88 + index * 0.01) if included else (0.56 + index * 0.01),
            }
        )
        flags.append(
            {
                "matched_set_id": f"set-{index}",
                "pre_index_forest_below_70_percent": not included,
                "excluded": not included,
            }
        )
    result = attrition_audit(pd.DataFrame(rows), pd.DataFrame(flags))
    assert result["candidate_matched_set_count"] == 8
    assert result["included_matched_set_count"] == 5
    assert result["excluded_matched_set_count"] == 3
    assert result["reason_counts_nonexclusive"]["pre_index_forest_below_70_percent"] == 3
    assert "forest_fraction" in result["variables_above_abs_smd_0_10"]


def test_transition_mass_audit_detects_internal_imbalance() -> None:
    registration = json.loads((ROOT / "config" / "phase3_registration.json").read_text())
    row: dict[str, list[float] | list[str]] = {"cell_id": ["cell-a"]}
    for horizon_text, years in registration["time_alignment"]["eligible_event_years_by_horizon"].items():
        horizon = int(horizon_text)
        for year in years:
            row[f"loss_fraction_cell_{year}_h{horizon}"] = [0.2]
            for destination in (
                "nonforest_natural",
                "rice_paddy",
                "oil_palm",
                "pulpwood_plantation",
                "other_agriculture",
                "mining",
                "urban",
                "other_nonvegetated",
                "aquaculture",
                "water",
            ):
                row[f"to_{destination}_fraction_cell_{year}_h{horizon}"] = [0.02]
    passed = transition_mass_audit(pd.DataFrame(row), registration)
    assert passed["status"] == "passed_internal_mass_balance"
    first_loss = next(column for column in row if column.startswith("loss_fraction_cell"))
    row[first_loss] = [0.3]
    failed = transition_mass_audit(pd.DataFrame(row), registration)
    assert failed["status"] == "failed_internal_mass_balance"
    assert failed["count_above_1e_8"] == 1


def test_selection_threshold_sensitivity_is_explicitly_post_registration(monkeypatch) -> None:
    registration = {
        "eligibility": {"pre_index_minimum_natural_forest_fraction": 0.70}
    }

    def fake_build(_opportunities, _transitions, amended, **_kwargs):
        threshold = amended["eligibility"]["pre_index_minimum_natural_forest_fraction"]
        return pd.DataFrame({"threshold": [threshold]}), {
            "excluded_matched_set_count": int(1000 * threshold)
        }

    def fake_fit(frame, **_kwargs):
        threshold = float(frame.iloc[0]["threshold"])
        estimate = 0.08 - threshold * 0.04
        return {
            "matched_set_count": int(20_000 * (1 - threshold / 2)),
            "primary_term": {
                "estimate": estimate,
                "ci95": [estimate - 0.01, estimate + 0.01],
                "p_two_sided": 0.001,
            },
        }

    monkeypatch.setattr(
        "analysis.phase3_publication_robustness.phase3.build_horizon_frame",
        fake_build,
    )
    monkeypatch.setattr(
        "analysis.phase3_publication_robustness.phase3.fit_within_set_lpm",
        fake_fit,
    )
    result = eligibility_threshold_sensitivity(
        pd.DataFrame(), pd.DataFrame(), registration
    )
    assert result["status"] == "post_registration_selection_sensitivity"
    assert [row["pre_index_minimum_natural_forest_fraction"] for row in result["results"]] == [
        0.50,
        0.60,
        0.70,
        0.80,
    ]
    assert sum(row["registered_primary_threshold"] for row in result["results"]) == 1
    assert registration["eligibility"]["pre_index_minimum_natural_forest_fraction"] == 0.70
