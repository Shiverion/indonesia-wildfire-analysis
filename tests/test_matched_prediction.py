from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from wildfire_research.matched_prediction import (
    assign_spatial_block_folds,
    choose_penalty,
    conditional_ranking_metrics,
    fit_ridge_conditional,
    pack_exact_matched_sets,
    purged_fold_sets,
)


def simple_sets(count: int = 10) -> tuple[pd.DataFrame, np.ndarray]:
    rows = []
    values = []
    for set_index in range(count):
        for member in range(5):
            rows.append(
                {
                    "matched_set_id": f"s{set_index}",
                    "cell_id": f"c{set_index}_{member}",
                    "outcome": int(member == 0),
                    "spatial_block": f"b{set_index % 5}",
                }
            )
            values.append([1.0 if member == 0 else -1.0])
    return pd.DataFrame(rows), np.asarray(values)


def test_ridge_conditional_fit_improves_ranking() -> None:
    frame, matrix = simple_sets()
    x, y, _ = pack_exact_matched_sets(frame, matrix)
    fit = fit_ridge_conditional(x, y, penalty=1.0)
    metrics = conditional_ranking_metrics(x, y, fit.coefficients)
    assert fit.converged
    assert metrics["conditional_log_loss"] < np.log(5)
    assert metrics["top1_recall_tie_fractional"] == pytest.approx(1.0)


def test_pack_rejects_incomplete_set() -> None:
    frame, matrix = simple_sets(1)
    with pytest.raises(ValueError, match="must have 5 rows"):
        pack_exact_matched_sets(frame.iloc[:-1], matrix[:-1])


def test_spatial_folds_are_deterministic_and_cell_purged() -> None:
    frame, _ = simple_sets()
    # Make one cell recur in a set assigned to another positive-cell block.
    frame.loc[frame["matched_set_id"].eq("s1") & frame["outcome"].eq(0), "cell_id"] = "c0_1"
    assignments = assign_spatial_block_folds(frame, folds=5)
    assignments_again = assign_spatial_block_folds(frame, folds=5)
    pd.testing.assert_frame_equal(assignments, assignments_again)
    fold = int(assignments.loc[assignments["matched_set_id"].eq("s0"), "fold"].iloc[0])
    train, test, audit = purged_fold_sets(frame, assignments, fold)
    train_cells = set(frame.loc[frame["matched_set_id"].isin(train), "cell_id"])
    test_cells = set(frame.loc[frame["matched_set_id"].isin(test), "cell_id"])
    assert not (train_cells & test_cells)
    assert audit["purged_training_set_count"] >= 1


def test_choose_penalty_prefers_larger_on_tie() -> None:
    rows = [
        {"penalty": 0.1, "mean_conditional_log_loss": 1.0},
        {"penalty": 10.0, "mean_conditional_log_loss": 1.0},
    ]
    assert choose_penalty(rows) == 10.0
