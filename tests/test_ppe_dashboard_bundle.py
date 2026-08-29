from __future__ import annotations

import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_alphaearth_dashboard_matches_locked_result_and_is_coordinate_free() -> None:
    locked = json.loads(
        (ROOT / "outputs" / "analysis" / "ppe_alphaearth_locked_test.json").read_text(
            encoding="utf-8"
        )
    )
    dashboard_path = ROOT / "apps" / "evidence-explorer" / "data" / "ppe-alphaearth.json"
    dashboard_text = dashboard_path.read_text(encoding="utf-8")
    dashboard = json.loads(dashboard_text)

    assert dashboard["status"] == locked["status"] == "locked_test_complete"
    for row in dashboard["models"]:
        family = {
            "Explicit weather, vegetation, forest and peat": "explicit",
            "Prior-year Earth AI embedding only": "embedding_only",
            "Combined": "combined",
        }[row["label"]]
        expected = locked["models"][family]["evaluation"]
        assert row["conditional_log_loss"] == pytest.approx(
            expected["conditional_log_loss"]
        )
        assert row["top1_recall"] == pytest.approx(
            expected["top1_recall_tie_fractional"]
        )
        assert row["mean_reciprocal_rank"] == pytest.approx(
            expected["mean_reciprocal_rank"]
        )

    improvement = locked["conditional_log_loss_improvement_vs_explicit"]["combined"]
    assert dashboard["combined_improvement"]["conditional_log_loss"] == pytest.approx(
        improvement["observed_improvement"]
    )
    assert dashboard["combined_improvement"]["ci95"] == pytest.approx(
        improvement["ci95_percentile"]
    )
    lowered = dashboard_text.lower()
    for forbidden in ("longitude", "latitude", "record_id", "cell_id"):
        assert forbidden not in lowered
