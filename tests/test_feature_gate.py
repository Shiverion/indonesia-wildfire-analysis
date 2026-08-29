from __future__ import annotations

import copy
import json
from pathlib import Path

from wildfire_research.feature_gate import audit_manifest, evaluate_feature


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_manifest() -> dict:
    return json.loads(
        (PROJECT_ROOT / "config" / "ppe_feature_manifest.json").read_text(
            encoding="utf-8"
        )
    )


def test_registered_manifest_passes_and_negative_controls_are_caught() -> None:
    result = audit_manifest(load_manifest())
    assert result["ready"] is True
    assert result["required_rejections"] == []
    assert result["negative_controls_caught"] is True


def test_same_year_alphaearth_is_rejected() -> None:
    manifest = load_manifest()
    candidate = copy.deepcopy(manifest["candidates"][-1])
    candidate["temporal_relation"] = "same_calendar_year"
    candidate["available_before_prediction_cutoff"] = False
    candidate["minimum_lag_years"] = 0
    result = evaluate_feature(candidate, manifest["target"], manifest["gate"])
    assert result.decision == "reject"
    assert any("temporal relation" in reason for reason in result.reasons)


def test_downstream_feature_is_rejected() -> None:
    manifest = load_manifest()
    candidate = copy.deepcopy(manifest["candidates"][0])
    candidate["causal_position"] = "downstream"
    result = evaluate_feature(candidate, manifest["target"], manifest["gate"])
    assert result.decision == "reject"
    assert any("causal position" in reason for reason in result.reasons)


def test_shared_source_path_is_rejected() -> None:
    manifest = load_manifest()
    candidate = copy.deepcopy(manifest["candidates"][0])
    candidate["shared_data_generation_with_target"] = True
    result = evaluate_feature(candidate, manifest["target"], manifest["gate"])
    assert result.decision == "reject"
    assert any("shares a data-generation" in reason for reason in result.reasons)


def test_missing_provenance_is_rejected() -> None:
    manifest = load_manifest()
    candidate = copy.deepcopy(manifest["candidates"][0])
    candidate["provenance_url"] = ""
    result = evaluate_feature(candidate, manifest["target"], manifest["gate"])
    assert result.decision == "reject"
    assert any("provenance_url" in reason for reason in result.reasons)
