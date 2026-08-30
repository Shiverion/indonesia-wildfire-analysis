from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.phase3_land_change import (
    browser_summary,
    eligible_event_years,
    expected_transition_columns,
    fit_within_set_lpm,
    holm_adjust,
    inspect_transition_summary,
    private_cell_id,
)


ROOT = Path(__file__).resolve().parents[1]


def test_private_cell_id_matches_frozen_phase1b_hash() -> None:
    assert private_cell_id(441, 817) == "6a12a2f8e220612a2615"


def test_followup_years_stop_at_last_available_map() -> None:
    assert eligible_event_years(2024, 1) == list(range(2015, 2024))
    assert eligible_event_years(2024, 2) == list(range(2015, 2023))
    assert eligible_event_years(2024, 3) == list(range(2015, 2022))


def test_holm_adjustment_preserves_order_and_caps_at_one() -> None:
    adjusted = holm_adjust([0.04, 0.001, 0.20, 0.03])
    assert adjusted == [0.09, 0.004, 0.20, 0.09]


def test_missing_transition_summary_fails_closed(tmp_path: Path) -> None:
    registration = json.loads((ROOT / "config" / "phase3_registration.json").read_text())
    audit = inspect_transition_summary(
        tmp_path / "missing.csv", registration, {"a", "b"}
    )
    assert audit["status"] == "missing"
    assert audit["gate_ready"] is False
    assert len(expected_transition_columns(registration)) == 307


def test_within_set_model_reports_finite_adjusted_risk_difference() -> None:
    rng = np.random.default_rng(20260827)
    rows = []
    for set_index in range(120):
        date = f"201{5 + set_index % 8}-{7 + set_index % 5:02d}-{1 + set_index % 27:02d}"
        latent = rng.normal(size=5)
        for position in range(5):
            exposed = int(position == 0)
            probability = 0.12 + 0.28 * exposed + 0.05 * (latent[position] > 0)
            rows.append(
                {
                    "matched_set_id": f"set-{set_index}",
                    "cell_id": f"cell-{(set_index * 3 + position) % 170}",
                    "date": date,
                    "year": 2015 + set_index % 8,
                    "fire_positive": exposed,
                    "land_change_outcome": int(rng.random() < probability),
                    "forest_fraction": 0.70 + 0.25 * rng.random(),
                    "peat_extent_percent": 100 * rng.random(),
                    "chirps_precip_7d_mm": 150 * rng.random(),
                    "chirps_precip_30d_mm": 400 * rng.random(),
                    "evi_prefire": 0.2 + 0.6 * rng.random(),
                    "era5_vpd_mean_72h_kpa": 0.2 + rng.random(),
                    "era5_wind_max_24h_ms": 1 + 5 * rng.random(),
                    "era5_rootzone_soil_water_mean_72h": 0.1 + 0.4 * rng.random(),
                }
            )
    model = fit_within_set_lpm(pd.DataFrame(rows), outcome_column="land_change_outcome")
    term = model["primary_term"]
    assert model["matched_set_count"] == 120
    assert np.isfinite(term["estimate"])
    assert np.isfinite(term["standard_error"])
    assert term["estimate"] > 0
    assert term["ci95"][0] < term["ci95"][1]


def test_browser_summary_carries_kalimantan_inference_scope() -> None:
    result = {
        "created_at_utc": "2026-08-28T00:00:00+00:00",
        "status": "blocked",
        "phase3_ready": False,
        "phase3_model_run": False,
        "scope": {
            "geography": "Kalimantan",
            "country_context": "Indonesia",
            "indonesia_map_role": "descriptive_context_only",
            "inference_generalization": "No Indonesia-wide or global inferential claim.",
        },
        "opportunity_inventory": {"matched_set_count": 1, "unique_cell_count": 5},
        "private_cell_index": {"private_cell_count": 5},
        "mapbiomas": {
            "official_available_years": [1990, 2024],
            "local_full_raster_years": [2014],
            "earth_engine_export": {},
        },
        "eligible_event_years_by_horizon": {"1": [2015]},
        "blockers": ["test"],
        "models": None,
        "claim_boundary": [],
    }
    summary = browser_summary(result)
    assert summary["scope"]["geography"] == "Kalimantan"
    assert summary["scope"]["indonesia_map_role"] == "descriptive_context_only"
