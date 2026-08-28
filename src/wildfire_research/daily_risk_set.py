"""Deterministic local matching helpers for the daily VIIRS risk-set track."""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np
import pandas as pd


EE_REQUIRED_COLUMNS = {
    "grid_col",
    "grid_row",
    "supercell_id",
    "outcome",
    "coverage_fraction",
    "negative_lookback_days",
    "chirps_precip_1d_mm",
    "chirps_precip_7d_mm",
    "chirps_precip_30d_mm",
    "chirps_precip_90d_mm",
    "evi_prefire",
    "evi_composite_start_day",
}


def deterministic_rank(seed: int, date_text: str, case_cell: str, control_cell: str) -> int:
    """Return a stable pseudo-random rank without depending on Python hash state."""

    value = f"{seed}:{date_text}:{case_cell}:{control_cell}".encode("utf-8")
    return int.from_bytes(hashlib.blake2b(value, digest_size=8).digest(), "big")


def match_daily_controls(
    frame: pd.DataFrame,
    *,
    date_text: str,
    controls_per_case: int = 4,
    maximum_distance_cells: float = 25.0,
    seed: int = 20260826,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Match QA-complete forest controls to cases within a fixed distance.

    Controls may be reused across risk sets, as frozen in the registration.
    Cases without the full requested number of controls are excluded rather
    than silently creating variable-size matched sets.
    """

    missing = sorted(EE_REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(f"Earth Engine frame missing columns: {missing}")
    if controls_per_case <= 0 or maximum_distance_cells <= 0:
        raise ValueError("matching parameters must be positive")

    working = frame.copy()
    working["outcome"] = pd.to_numeric(working["outcome"], errors="coerce")
    covariates = [
        "coverage_fraction",
        "negative_lookback_days",
        "chirps_precip_1d_mm",
        "chirps_precip_7d_mm",
        "chirps_precip_30d_mm",
        "chirps_precip_90d_mm",
        "evi_prefire",
        "evi_composite_start_day",
        "forest_fraction",
        "peat_extent_percent",
    ]
    finite = np.ones(len(working), dtype=bool)
    for column in covariates:
        values = pd.to_numeric(working[column], errors="coerce").to_numpy(dtype=float)
        finite &= np.isfinite(values)
        if column in {"evi_prefire", "evi_composite_start_day"}:
            finite &= values > -9000
    working = working.loc[finite].copy()

    # Earth Engine can occasionally return the same projected grid cell more
    # than once at an image/tile boundary. One cell-day is one opportunity;
    # retaining both copies would create duplicate cases and 8-control sets.
    cell_key = ["grid_row", "grid_col", "outcome"]
    duplicated = working.duplicated(cell_key, keep=False)
    duplicate_candidate_rows_removed = int(
        duplicated.sum() - working.loc[duplicated, cell_key].drop_duplicates().shape[0]
    )
    if duplicated.any():
        compare_columns = [column for column in working.columns if column not in cell_key]
        disagreement = (
            working.loc[duplicated]
            .groupby(cell_key, dropna=False)[compare_columns]
            .nunique(dropna=False)
            .gt(1)
            .any(axis=1)
        )
        if disagreement.any():
            raise ValueError("duplicate projected grid cells have conflicting values")
        working = working.drop_duplicates(cell_key, keep="first").copy()

    cases = working[working["outcome"] == 1].copy()
    controls = working[working["outcome"] == 0].copy()
    selected: list[pd.DataFrame] = []
    cases_without_controls = 0
    for case in cases.itertuples(index=False):
        case_col = int(case.grid_col)
        case_row = int(case.grid_row)
        case_cell = f"r{case_row}_c{case_col}"
        dx = controls["grid_col"].to_numpy(dtype=float) - case_col
        dy = controls["grid_row"].to_numpy(dtype=float) - case_row
        candidates = controls.loc[(dx * dx + dy * dy) <= maximum_distance_cells**2].copy()
        if len(candidates) < controls_per_case:
            cases_without_controls += 1
            continue
        candidates["_rank"] = [
            deterministic_rank(seed, date_text, case_cell, f"r{int(row)}_c{int(col)}")
            for row, col in zip(candidates["grid_row"], candidates["grid_col"], strict=True)
        ]
        candidates = candidates.nsmallest(controls_per_case, "_rank").drop(columns="_rank")
        case_frame = pd.DataFrame([case._asdict()])
        matched_set_id = f"{date_text}:r{case_row}:c{case_col}"
        case_frame["matched_set_id"] = matched_set_id
        candidates["matched_set_id"] = matched_set_id
        selected.extend([case_frame, candidates])

    if selected:
        result = pd.concat(selected, ignore_index=True)
        result["outcome_status"] = np.where(result["outcome"] == 1, "positive", "negative")
        result["cell_id"] = [f"r{int(row)}_c{int(col)}" for row, col in zip(result["grid_row"], result["grid_col"], strict=True)]
        result["opportunity_id"] = [
            f"{matched}:{status}:{index}"
            for index, (matched, status) in enumerate(zip(result["matched_set_id"], result["outcome_status"], strict=True))
        ]
        result["pair_key"] = f"VNP14A1.002:{date_text}"
        result["acquisition_utc"] = f"{date_text}T00:00:00Z"
        result["valid_opportunity"] = True
        result["quality_pass"] = True
        result["negative_lookback_hours"] = pd.to_numeric(result["negative_lookback_days"]) * 24
    else:
        result = pd.DataFrame()

    report = {
        "input_rows": int(len(frame)),
        "complete_covariate_rows": int(len(working)),
        "duplicate_candidate_rows_removed": duplicate_candidate_rows_removed,
        "eligible_cases_after_local_filters": int(len(cases)),
        "eligible_controls_after_local_filters": int(len(controls)),
        "cases_without_four_controls": int(cases_without_controls),
        "matched_cases": int((result.get("outcome", pd.Series(dtype=int)) == 1).sum()),
        "matched_controls": int((result.get("outcome", pd.Series(dtype=int)) == 0).sum()),
    }
    return result, report
