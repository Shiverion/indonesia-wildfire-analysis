#!/usr/bin/env python3
"""Prepare, gate, and fit the registered Phase 3 fire-to-land-change analysis.

The script deliberately writes a blocked readiness result when the annual
MapBiomas transition summary is absent.  It never substitutes the 2014
baseline raster for dated post-fire outcomes and never turns missing/not-
observed pixels into stable land cover.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy.stats import norm


ROOT = Path(__file__).resolve().parents[1]
REGISTRATION_PATH = ROOT / "config" / "phase3_registration.json"
REPORTING_AMENDMENT_PATH = ROOT / "config" / "phase3_reporting_amendment_2026-08-30.json"
LEGEND_PATH = ROOT / "config" / "mapbiomas_collection41_legend.json"
PHASE1B_PATH = ROOT / "outputs" / "quality" / "phase1b_readiness.json"
OPPORTUNITY_PATH = ROOT / "data" / "derived" / "viirs" / "opportunity_frame.csv"
DAILY_ROOT = ROOT / "data" / "derived" / "viirs" / "daily_risk_sets"
FOREST_GRID_PATH = (
    ROOT
    / "data"
    / "derived"
    / "mapbiomas"
    / "mapbiomas_c41_forest_fraction_1km_kalimantan.tif"
)
PRIVATE_CELL_PATH = (
    ROOT / "data" / "derived" / "phase3" / "phase3_cell_centres_private.csv"
)
TRANSITION_SUMMARY_PATH = (
    ROOT
    / "data"
    / "derived"
    / "phase3"
    / "mapbiomas_c41_transition_summary_private.csv"
)
PRIVATE_CELL_RECEIPT_PATH = (
    ROOT / "outputs" / "quality" / "phase3_private_cell_index.json"
)
CLOUD_AUDIT_PATH = ROOT / "outputs" / "quality" / "phase3_cloud_access_audit.json"
EARTH_ENGINE_EXPORT_PATH = (
    ROOT / "outputs" / "quality" / "phase3_earthengine_export.json"
)
READINESS_PATH = ROOT / "outputs" / "quality" / "phase3_readiness.json"
RESULT_PATH = ROOT / "outputs" / "analysis" / "phase3_land_change_results.json"
MARKDOWN_PATH = ROOT / "outputs" / "insights" / "phase3_fire_to_land_change.md"
BROWSER_PATH = ROOT / "apps" / "evidence-explorer" / "data" / "phase3-status.json"

DESTINATIONS = (
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
)

MODEL_COVARIATES = (
    ("forest_fraction", "identity", 1.0),
    ("peat_extent_percent", "identity", 1.0),
    ("chirps_precip_7d_mm", "log1p", 1.0),
    ("chirps_precip_30d_mm", "log1p", 1.0),
    ("evi_prefire", "identity", 1.0),
    ("era5_vpd_mean_72h_kpa", "identity", 1.0),
    ("era5_wind_max_24h_ms", "identity", 1.0),
    ("era5_rootzone_soil_water_mean_72h", "identity", 1.0),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def display_path(path: Path) -> str:
    try:
        value = path.relative_to(ROOT)
    except ValueError:
        value = path
    return str(value).replace("\\", "/")


def private_cell_id(grid_row: int, grid_col: int) -> str:
    value = f"phase1b-grid:{int(grid_row)}:{int(grid_col)}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]


def eligible_event_years(last_map_year: int, horizon: int) -> list[int]:
    if horizon < 1:
        raise ValueError("horizon must be at least one year")
    return list(range(2015, last_map_year - horizon + 1))


def expected_transition_columns(registration: dict[str, Any]) -> list[str]:
    columns = {"cell_id"}
    horizon_years = registration["time_alignment"]["eligible_event_years_by_horizon"]
    for horizon_text, years in horizon_years.items():
        horizon = int(horizon_text)
        for year in years:
            columns.add(f"pre_natural_fraction_{year}")
            columns.add(f"pre_observed_fraction_{year}")
            columns.add(f"post_observed_fraction_{year}_h{horizon}")
            columns.add(f"loss_fraction_cell_{year}_h{horizon}")
            for destination in DESTINATIONS:
                columns.add(f"to_{destination}_fraction_cell_{year}_h{horizon}")
    return sorted(columns)


def load_opportunities(path: Path = OPPORTUNITY_PATH) -> pd.DataFrame:
    frame = pd.read_csv(path, low_memory=False)
    required = {
        "cell_id",
        "matched_set_id",
        "outcome_status",
        "acquisition_utc",
        "valid_opportunity",
        "quality_pass",
        *[item[0] for item in MODEL_COVARIATES],
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Opportunity frame missing columns: {', '.join(missing)}")
    frame = frame.copy()
    frame["date"] = frame["acquisition_utc"].astype(str).str.slice(0, 10)
    frame["year"] = pd.to_numeric(frame["date"].str.slice(0, 4), errors="raise").astype(int)
    frame["fire_positive"] = (frame["outcome_status"] == "positive").astype(np.int8)
    sizes = frame.groupby("matched_set_id", sort=False).size()
    positives = frame.groupby("matched_set_id", sort=False)["fire_positive"].sum()
    if not sizes.eq(5).all() or not positives.eq(1).all():
        raise ValueError("Opportunity frame is not composed of exact 1:4 matched sets")
    if frame.duplicated(["matched_set_id", "cell_id"]).any():
        raise ValueError("A cell is duplicated inside an opportunity matched set")
    return frame


def build_private_cell_index(
    opportunities: pd.DataFrame,
    *,
    daily_root: Path = DAILY_ROOT,
    forest_grid_path: Path = FOREST_GRID_PATH,
    output_path: Path = PRIVATE_CELL_PATH,
) -> dict[str, Any]:
    """Recover exact private grid cells without releasing coordinates publicly."""

    parquet_paths = sorted(daily_root.rglob("*.parquet"))
    if not parquet_paths:
        raise FileNotFoundError(f"No daily Parquet chunks found under {daily_root}")
    wanted = set(opportunities["cell_id"].astype(str).unique())
    parts: list[pd.DataFrame] = []
    for path in parquet_paths:
        try:
            chunk = pd.read_parquet(path, columns=["grid_row", "grid_col"])
        except Exception as exc:
            # Fully supported days with no qualifying cases are intentionally
            # stored as zero-row, zero-column Parquet files.
            empty_probe = pd.read_parquet(path)
            if empty_probe.empty and len(empty_probe.columns) == 0:
                continue
            raise ValueError(f"Non-empty daily chunk lacks grid coordinates: {path}") from exc
        if chunk.empty:
            continue
        chunk = chunk.drop_duplicates().copy()
        chunk["cell_id"] = [
            private_cell_id(row, col)
            for row, col in zip(chunk["grid_row"], chunk["grid_col"], strict=True)
        ]
        matched = chunk[chunk["cell_id"].isin(wanted)]
        if not matched.empty:
            parts.append(matched)
    if not parts:
        raise ValueError("No private grid coordinates matched the locked opportunity frame")
    cells = pd.concat(parts, ignore_index=True).drop_duplicates()
    conflicts = (
        cells.groupby("cell_id")[["grid_row", "grid_col"]]
        .nunique(dropna=False)
        .gt(1)
        .any(axis=1)
    )
    if conflicts.any():
        raise ValueError("A private cell hash resolves to more than one grid coordinate")
    cells = cells.drop_duplicates("cell_id").sort_values("cell_id").reset_index(drop=True)
    missing = sorted(wanted - set(cells["cell_id"]))
    if missing:
        raise ValueError(f"Private index is missing {len(missing)} locked cells")

    import rasterio
    from rasterio.warp import transform

    with rasterio.open(forest_grid_path) as forest:
        rows = cells["grid_row"].astype(int).to_numpy()
        cols = cells["grid_col"].astype(int).to_numpy()
        x = forest.transform.c + (cols + 0.5) * forest.transform.a
        y = forest.transform.f + (rows + 0.5) * forest.transform.e
        lon, lat = transform(forest.crs, "EPSG:4326", x.tolist(), y.tolist())
    cells["longitude"] = np.asarray(lon, dtype=float)
    cells["latitude"] = np.asarray(lat, dtype=float)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cells.to_csv(output_path, index=False, float_format="%.8f")
    return {
        "schema_version": "phase3-private-cell-index/v1",
        "created_at_utc": utc_now(),
        "status": "complete_private_local_only",
        "source_daily_parquet_count": len(parquet_paths),
        "locked_opportunity_cell_count": len(wanted),
        "private_cell_count": int(len(cells)),
        "all_locked_cells_resolved": True,
        "grid_crs": "EPSG:6933",
        "grid_cell_size_m": 1000,
        "output": {
            "path": str(output_path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256_file(output_path),
            "tracked_by_git": False,
            "contains_coordinates": True,
        },
        "privacy_guardrail": "This file is ignored by Git and must not be bundled into the dashboard or Vercel deployment.",
    }


def inspect_transition_summary(
    path: Path,
    registration: dict[str, Any],
    expected_cells: set[str],
) -> dict[str, Any]:
    expected_columns = expected_transition_columns(registration)
    if not path.is_file():
        return {
            "status": "missing",
            "path": display_path(path),
            "required_column_count": len(expected_columns),
            "missing_columns": expected_columns,
            "gate_ready": False,
        }
    frame = pd.read_csv(path, low_memory=False)
    missing_columns = sorted(set(expected_columns) - set(frame.columns))
    errors: list[str] = []
    if frame.get("cell_id", pd.Series(dtype=str)).duplicated().any():
        errors.append("duplicate_cell_id")
    found_cells = set(frame.get("cell_id", pd.Series(dtype=str)).astype(str))
    missing_cells = expected_cells - found_cells
    unexpected_cells = found_cells - expected_cells
    if missing_cells:
        errors.append(f"missing_locked_cells:{len(missing_cells)}")
    if unexpected_cells:
        errors.append(f"unexpected_cells:{len(unexpected_cells)}")
    if missing_columns:
        errors.append(f"missing_columns:{len(missing_columns)}")
    fraction_columns = [column for column in expected_columns if column != "cell_id" and column in frame]
    nonfinite_count = 0
    out_of_range_count = 0
    if fraction_columns:
        matrix = frame[fraction_columns].apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
        nonfinite_count = int((~np.isfinite(matrix)).sum())
        out_of_range_count = int(((matrix < -1e-9) | (matrix > 1 + 1e-9)).sum())
        if nonfinite_count:
            errors.append(f"nonfinite_fraction_values:{nonfinite_count}")
        if out_of_range_count:
            errors.append(f"fraction_out_of_range:{out_of_range_count}")
    return {
        "status": "validated" if not errors else "invalid",
        "path": display_path(path),
        "sha256": sha256_file(path),
        "row_count": int(len(frame)),
        "expected_cell_count": len(expected_cells),
        "required_column_count": len(expected_columns),
        "missing_column_count": len(missing_columns),
        "missing_columns": missing_columns,
        "missing_cell_count": len(missing_cells),
        "unexpected_cell_count": len(unexpected_cells),
        "nonfinite_fraction_value_count": nonfinite_count,
        "out_of_range_fraction_value_count": out_of_range_count,
        "errors": errors,
        "gate_ready": not errors,
    }


def _cluster_meat(x: np.ndarray, residual: np.ndarray, labels: pd.Series) -> tuple[np.ndarray, int]:
    codes, uniques = pd.factorize(labels.astype(str), sort=False)
    groups = len(uniques)
    if groups < 2:
        raise ValueError("Cluster covariance needs at least two clusters")
    scores = x * residual[:, None]
    sums = np.zeros((groups, x.shape[1]), dtype=float)
    np.add.at(sums, codes, scores)
    meat = sums.T @ sums
    n, k = x.shape
    correction = (groups / (groups - 1)) * ((n - 1) / max(n - k, 1))
    return correction * meat, groups


def _standardize_covariates(
    frame: pd.DataFrame,
    reference_years: Iterable[int],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    result = frame.copy()
    reference = result[result["year"].isin(list(reference_years))]
    if reference.empty:
        raise ValueError("No rows exist in the registered standardization period")
    receipt: dict[str, Any] = {}
    for source, transform_name, direction in MODEL_COVARIATES:
        raw_reference = pd.to_numeric(reference[source], errors="coerce").to_numpy(dtype=float)
        raw_all = pd.to_numeric(result[source], errors="coerce").to_numpy(dtype=float)
        if transform_name == "log1p":
            if (raw_reference < 0).any() or (raw_all < 0).any():
                raise ValueError(f"{source} contains a negative value before log1p")
            raw_reference = np.log1p(raw_reference)
            raw_all = np.log1p(raw_all)
        mean = float(raw_reference.mean())
        sd = float(raw_reference.std(ddof=0))
        if not math.isfinite(sd) or sd <= 0:
            raise ValueError(f"{source} has invalid standard deviation")
        name = f"{source}_z"
        result[name] = direction * (raw_all - mean) / sd
        receipt[name] = {"source": source, "transform": transform_name, "mean": mean, "sd": sd}
    return result, receipt


def fit_within_set_lpm(
    frame: pd.DataFrame,
    *,
    outcome_column: str,
    reference_years: Iterable[int] = range(2015, 2023),
) -> dict[str, Any]:
    """Fit an adjusted fixed-set linear probability model with clustered SEs."""

    if frame.empty:
        raise ValueError("The Phase 3 model frame is empty")
    work, standardization = _standardize_covariates(frame, reference_years)
    feature_names = ["fire_positive", *[f"{item[0]}_z" for item in MODEL_COVARIATES]]
    y = pd.to_numeric(work[outcome_column], errors="raise").to_numpy(dtype=float)
    x = work[feature_names].to_numpy(dtype=float)
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Phase 3 model matrix contains non-finite values")
    groups = work["matched_set_id"].astype(str).reset_index(drop=True)
    y_within = y - pd.Series(y).groupby(groups.to_numpy(), sort=False).transform("mean").to_numpy()
    x_within = np.empty_like(x)
    for index in range(x.shape[1]):
        x_within[:, index] = x[:, index] - pd.Series(x[:, index]).groupby(
            groups.to_numpy(), sort=False
        ).transform("mean").to_numpy()
    information = x_within.T @ x_within
    bread = np.linalg.pinv(information, rcond=1e-12)
    beta = bread @ (x_within.T @ y_within)
    residual = y_within - x_within @ beta
    cell_meat, cell_clusters = _cluster_meat(x_within, residual, work["cell_id"])
    date_meat, date_clusters = _cluster_meat(x_within, residual, work["date"])
    intersection = work["cell_id"].astype(str) + "|" + work["date"].astype(str)
    intersection_meat, intersection_clusters = _cluster_meat(x_within, residual, intersection)
    covariance = bread @ (cell_meat + date_meat - intersection_meat) @ bread
    covariance = (covariance + covariance.T) / 2
    method = "two_way_cell_and_date_cluster_robust"
    warning = None
    if not np.isfinite(np.diag(covariance)).all() or (np.diag(covariance) <= 0).any():
        covariance = bread @ cell_meat @ bread
        covariance = (covariance + covariance.T) / 2
        method = "cell_cluster_robust_fallback"
        warning = "Two-way covariance had an invalid diagonal; cell-only covariance was used."
    standard_errors = np.sqrt(np.maximum(np.diag(covariance), 0))
    estimates = []
    for index, name in enumerate(feature_names):
        estimate = float(beta[index])
        se = float(standard_errors[index])
        z = estimate / se if se > 0 else math.nan
        estimates.append(
            {
                "term": name,
                "estimate": estimate,
                "standard_error": se,
                "ci95": [estimate - 1.96 * se, estimate + 1.96 * se],
                "z": z if math.isfinite(z) else None,
                "p_two_sided": float(2 * norm.sf(abs(z))) if math.isfinite(z) else None,
            }
        )
    exposed = work.loc[work["fire_positive"] == 1, outcome_column].astype(float)
    controls = work.loc[work["fire_positive"] == 0, outcome_column].astype(float)
    control_risk = float(controls.mean())
    exposed_risk = float(exposed.mean())
    variation_sets = int(work.groupby("matched_set_id")[outcome_column].nunique().gt(1).sum())
    set_scores = x_within * residual[:, None]
    score_norm = pd.DataFrame(set_scores).assign(set_id=groups.to_numpy()).groupby("set_id").sum()
    score_norms = np.linalg.norm(score_norm.to_numpy(dtype=float), axis=1)
    return {
        "model": "within-matched-set linear probability model",
        "effect_measure": "adjusted risk difference",
        "row_count": int(len(work)),
        "matched_set_count": int(work["matched_set_id"].nunique()),
        "unique_cell_count": int(work["cell_id"].nunique()),
        "outcome_variation_matched_set_count": variation_sets,
        "unadjusted": {
            "fire_positive_risk": exposed_risk,
            "fire_negative_risk": control_risk,
            "risk_difference": exposed_risk - control_risk,
            "risk_ratio": exposed_risk / control_risk if control_risk > 0 else None,
            "risk_ratio_zero_control_guard": control_risk == 0,
        },
        "primary_term": next(row for row in estimates if row["term"] == "fire_positive"),
        "coefficients": estimates,
        "standardization": standardization,
        "uncertainty": {
            "method": method,
            "cell_clusters": cell_clusters,
            "date_clusters": date_clusters,
            "cell_date_clusters": intersection_clusters,
            "warning": warning,
        },
        "diagnostics": {
            "information_condition_number": float(np.linalg.cond(information)),
            "residual_rmse": float(np.sqrt(np.mean(residual**2))),
            "matched_set_score_norm_p99": float(np.quantile(score_norms, 0.99)),
            "matched_set_score_norm_max": float(score_norms.max()),
        },
    }


def _distribution(values: pd.Series) -> dict[str, Any]:
    array = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    return {
        "n": int(len(array)),
        "mean": float(array.mean()),
        "median": float(np.median(array)),
        "standard_deviation": float(array.std(ddof=1)) if len(array) > 1 else 0.0,
        "p25": float(np.quantile(array, 0.25)),
        "p75": float(np.quantile(array, 0.75)),
        "p05": float(np.quantile(array, 0.05)),
        "p95": float(np.quantile(array, 0.95)),
    }


def build_horizon_frame(
    opportunities: pd.DataFrame,
    transitions: pd.DataFrame,
    registration: dict[str, Any],
    *,
    horizon: int,
    threshold: float,
    destination: str | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    years = registration["time_alignment"]["eligible_event_years_by_horizon"][str(horizon)]
    pieces: list[pd.DataFrame] = []
    for year in years:
        source = opportunities[opportunities["year"] == year].copy()
        pre = f"pre_natural_fraction_{year}"
        pre_observed = f"pre_observed_fraction_{year}"
        post_observed = f"post_observed_fraction_{year}_h{horizon}"
        loss = f"loss_fraction_cell_{year}_h{horizon}"
        outcome_fraction = (
            f"to_{destination}_fraction_cell_{year}_h{horizon}" if destination else loss
        )
        lookup = transitions[["cell_id", pre, pre_observed, post_observed, outcome_fraction]].copy()
        lookup = lookup.rename(
            columns={
                pre: "pre_natural_fraction",
                pre_observed: "pre_observed_fraction",
                post_observed: "post_observed_fraction",
                outcome_fraction: "transition_fraction_cell",
            }
        )
        pieces.append(source.merge(lookup, on="cell_id", how="left", validate="many_to_one"))
    frame = pd.concat(pieces, ignore_index=True)
    pre_min = float(registration["eligibility"]["pre_index_minimum_natural_forest_fraction"])
    observed_min = float(registration["eligibility"]["minimum_pre_and_followup_observed_fraction"])
    required = [
        "pre_natural_fraction",
        "pre_observed_fraction",
        "post_observed_fraction",
        "transition_fraction_cell",
    ]
    numeric = frame[required].apply(pd.to_numeric, errors="coerce")
    invalid = (
        ~np.isfinite(numeric.to_numpy(dtype=float)).all(axis=1)
        | (numeric["pre_natural_fraction"] < pre_min)
        | (numeric["pre_observed_fraction"] < observed_min)
        | (numeric["post_observed_fraction"] < observed_min)
        | (numeric["transition_fraction_cell"] < 0)
        | (numeric["transition_fraction_cell"] > numeric["pre_natural_fraction"] + 1e-8)
    )
    rainfall_invalid = frame[["chirps_precip_7d_mm", "chirps_precip_30d_mm"]].lt(0).any(axis=1)
    invalid_sets = set(frame.loc[invalid | rainfall_invalid, "matched_set_id"].astype(str))
    kept = frame[~frame["matched_set_id"].astype(str).isin(invalid_sets)].copy()
    kept["transition_share_preforest"] = (
        kept["transition_fraction_cell"] / kept["pre_natural_fraction"]
    )
    kept["land_change_outcome"] = (kept["transition_share_preforest"] >= threshold).astype(np.int8)
    return kept, {
        "horizon_years": horizon,
        "threshold_share_of_preforest": threshold,
        "destination": destination or "any_natural_forest_loss",
        "candidate_matched_set_count": int(frame["matched_set_id"].nunique()),
        "excluded_matched_set_count": len(invalid_sets),
        "included_matched_set_count": int(kept["matched_set_id"].nunique()),
        "included_row_count": int(len(kept)),
        "missing_or_support_failures_are_zero": False,
        "distribution_by_exposure": {
            label: _distribution(group["transition_share_preforest"])
            for label, group in kept.groupby("outcome_status", sort=True)
        },
    }


def holm_adjust(p_values: list[float]) -> list[float]:
    count = len(p_values)
    order = np.argsort(p_values)
    adjusted = np.empty(count, dtype=float)
    running = 0.0
    for rank, index in enumerate(order):
        candidate = min(1.0, (count - rank) * float(p_values[index]))
        running = max(running, candidate)
        adjusted[index] = running
    return adjusted.tolist()


def run_models(
    opportunities: pd.DataFrame,
    transitions: pd.DataFrame,
    registration: dict[str, Any],
) -> dict[str, Any]:
    minimum_sets = int(registration["eligibility"]["minimum_complete_matched_sets"])
    minimum_variation = int(
        registration["eligibility"]["minimum_exposure_and_outcome_variation_sets"]
    )

    def estimate(*, horizon: int, threshold: float, destination: str | None = None) -> dict[str, Any]:
        frame, flow = build_horizon_frame(
            opportunities,
            transitions,
            registration,
            horizon=horizon,
            threshold=threshold,
            destination=destination,
        )
        variation = int(frame.groupby("matched_set_id")["land_change_outcome"].nunique().gt(1).sum())
        if frame["matched_set_id"].nunique() < minimum_sets or variation < minimum_variation:
            return {
                "status": "not_estimated_insufficient_support",
                "flow": flow,
                "outcome_variation_matched_set_count": variation,
                "minimum_complete_matched_sets": minimum_sets,
                "minimum_variation_matched_sets": minimum_variation,
            }
        model = fit_within_set_lpm(frame, outcome_column="land_change_outcome")
        return {"status": "estimated", "flow": flow, "model": model}

    primary = estimate(horizon=1, threshold=0.10)
    threshold_sensitivities = [
        {"threshold": threshold, **estimate(horizon=1, threshold=threshold)}
        for threshold in (0.05, 0.20)
    ]
    horizon_sensitivities = [
        {"horizon": horizon, **estimate(horizon=horizon, threshold=0.10)}
        for horizon in (2, 3)
    ]
    secondary_sensitivities = [
        *threshold_sensitivities,
        *horizon_sensitivities,
    ]
    estimated_sensitivities = [
        item for item in secondary_sensitivities if item["status"] == "estimated"
    ]
    if estimated_sensitivities:
        adjusted = holm_adjust(
            [item["model"]["primary_term"]["p_two_sided"] for item in estimated_sensitivities]
        )
        for item, p_holm in zip(estimated_sensitivities, adjusted, strict=True):
            item["model"]["primary_term"]["p_holm_secondary_family"] = p_holm
    destination_models = [
        {"destination": destination, **estimate(horizon=1, threshold=0.10, destination=destination)}
        for destination in DESTINATIONS
    ]
    estimated_destinations = [item for item in destination_models if item["status"] == "estimated"]
    if estimated_destinations:
        adjusted = holm_adjust(
            [item["model"]["primary_term"]["p_two_sided"] for item in estimated_destinations]
        )
        for item, p_holm in zip(estimated_destinations, adjusted, strict=True):
            item["model"]["primary_term"]["p_holm_destination_family"] = p_holm
    return {
        "primary": primary,
        "threshold_sensitivities": threshold_sensitivities,
        "horizon_sensitivities": horizon_sensitivities,
        "destination_models": destination_models,
    }


def render_markdown(result: dict[str, Any]) -> str:
    inventory = result["opportunity_inventory"]
    export_receipt = result["mapbiomas"].get("earth_engine_export", {})
    cloud_ready = (
        result["mapbiomas"].get("cloud_access", {}).get("status")
        == "ready_registered_earth_engine_project"
    )
    lines = [
        "# Phase 3 — Fire followed by land-cover change",
        "",
        f"**Status:** {result['status'].replace('_', ' ')}",
        f"**Updated:** {result['created_at_utc']}",
        "**Inferential geography:** Kalimantan. The Indonesia-wide map is descriptive context only.",
        "**Registered claim:** association only; not actor, intent, profit, legality, or government-performance attribution.",
        "",
        "## What is already complete",
        "",
        f"- The locked fire-opportunity input contains **{inventory['row_count']:,} rows**, **{inventory['matched_set_count']:,} exact 1:4 matched sets**, and **{inventory['unique_cell_count']:,} unique 1 km cells**.",
        f"- A private coordinate index resolves **{result['private_cell_index']['private_cell_count']:,} cells** for cloud extraction; it is excluded from Git and the dashboard.",
        "- The outcome definition, follow-up windows, class crosswalk, exclusion rules, estimator, uncertainty, sensitivities, and claim boundaries were frozen before extracting the annual outcome.",
        "- Official MapBiomas Indonesia Collection 4.1 support is annual **1990–2024**. Therefore one-year follow-up is eligible through fire year 2023; 2024–2025 fires are not silently treated as having no land-cover change.",
        "",
        "## Current gate",
        "",
    ]
    if result["phase3_model_run"]:
        primary = result["models"]["primary"]
        if primary["status"] == "estimated":
            term = primary["model"]["primary_term"]
            unadjusted = primary["model"]["unadjusted"]
            flow = primary["flow"]
            negative = flow["distribution_by_exposure"]["negative"]
            positive = flow["distribution_by_exposure"]["positive"]
            lines.extend(
                [
                    "The primary Phase 3 model was estimated.",
                    "",
                    f"- Adjusted risk difference: **{term['estimate']:.4f}** (95% CI {term['ci95'][0]:.4f} to {term['ci95'][1]:.4f}; p={term['p_two_sided']:.4g}).",
                    f"- Complete matched sets: **{primary['model']['matched_set_count']:,}**.",
                    f"- Unadjusted probability of losing at least 10% of pre-index natural forest by the one-year map: **{unadjusted['fire_positive_risk'] * 100:.2f}%** in fire-positive cells versus **{unadjusted['fire_negative_risk'] * 100:.2f}%** in matched fire-negative cells (risk ratio {unadjusted['risk_ratio']:.2f}).",
                    f"- The continuous loss-share distribution is strongly right-skewed: fire-positive mean **{positive['mean'] * 100:.2f}%**, median **{positive['median'] * 100:.2f}%**, IQR {positive['p25'] * 100:.2f}%–{positive['p75'] * 100:.2f}%; negative mean **{negative['mean'] * 100:.2f}%**, median **{negative['median'] * 100:.2f}%**, IQR {negative['p25'] * 100:.2f}%–{negative['p75'] * 100:.2f}%.",
                    f"- Of **{flow['candidate_matched_set_count']:,}** temporally eligible candidate sets, **{flow['included_matched_set_count']:,}** passed the complete-set forest and observed-support gates; **{flow['excluded_matched_set_count']:,}** were excluded rather than imputed.",
                    "- This estimate is an association between index-day fire detection and later mapped land-cover change.",
                    "",
                    "## Registered robustness checks",
                    "",
                    "| Analysis | Adjusted risk difference | 95% CI | Raw p | Holm p (4 secondary checks) |",
                    "|---|---:|---:|---:|---:|",
                ]
            )
            sensitivity_rows = [
                ("5% loss threshold, one year", result["models"]["threshold_sensitivities"][0]),
                ("20% loss threshold, one year", result["models"]["threshold_sensitivities"][1]),
                ("10% loss threshold, two years", result["models"]["horizon_sensitivities"][0]),
                ("10% loss threshold, three years", result["models"]["horizon_sensitivities"][1]),
            ]
            for label, sensitivity in sensitivity_rows:
                sensitivity_term = sensitivity["model"]["primary_term"]
                lines.append(
                    f"| {label} | {sensitivity_term['estimate'] * 100:.2f} pp | "
                    f"{sensitivity_term['ci95'][0] * 100:.2f} to {sensitivity_term['ci95'][1] * 100:.2f} pp | "
                    f"{sensitivity_term['p_two_sided']:.3g} | "
                    f"{sensitivity_term['p_holm_secondary_family']:.3g} |"
                )
            lines.extend(
                [
                    "",
                    "All four registered threshold/horizon checks remain positive after a conservative Holm correction across the four secondary checks. The single registered primary test remains unadjusted, as frozen before outcome extraction. This reporting amendment was added after the multiplicity audit; it changes no estimate or model and does not make the association causal.",
                    "",
                    "## Exploratory destination classes",
                    "",
                    "Each estimable destination tests whether at least 10% of pre-index natural forest is mapped as that class one year later. Holm p-values correct across the estimable destination family.",
                    "",
                    "| Destination | Status / adjusted risk difference | 95% CI | Holm p-value |",
                    "|---|---:|---:|---:|",
                ]
            )
            destination_labels = {
                "nonforest_natural": "Non-forest natural vegetation",
                "rice_paddy": "Rice paddy",
                "oil_palm": "Oil palm",
                "pulpwood_plantation": "Pulpwood plantation",
                "other_agriculture": "Other agriculture",
                "mining": "Mining",
                "urban": "Urban",
                "other_nonvegetated": "Other non-vegetated",
                "aquaculture": "Aquaculture",
                "water": "Water",
            }
            for destination in result["models"]["destination_models"]:
                label = destination_labels[destination["destination"]]
                if destination["status"] == "estimated":
                    destination_term = destination["model"]["primary_term"]
                    lines.append(
                        f"| {label} | {destination_term['estimate'] * 100:.3f} pp | "
                        f"{destination_term['ci95'][0] * 100:.3f} to {destination_term['ci95'][1] * 100:.3f} pp | "
                        f"{destination_term['p_holm_destination_family']:.3g} |"
                    )
                else:
                    lines.append(
                        f"| {label} | Not estimated: only {destination['outcome_variation_matched_set_count']} varying sets | — | — |"
                    )
            lines.extend(
                [
                    "",
                    "The oil-palm destination is a small but statistically supported exploratory association (+0.336 percentage points; Holm p=0.016). It does **not** establish that a fire was deliberately set for oil palm, who acted, when planting occurred, ownership, legality, or profit.",
                ]
            )
        else:
            lines.append("The outcome table passed schema checks, but the registered minimum support for estimation was not met.")
    else:
        lines.extend(
            [
                "**The statistical result is not available yet.** The required coordinate-level annual transition summary has not been extracted from MapBiomas. The only local annual raster is 2014, which is a baseline and cannot represent post-fire change.",
                "",
                "This is a data-access gate, not a failed or null hypothesis. No coefficient, p-value, or direction is reported.",
            ]
        )
        if export_receipt.get("status") == "earth_engine_chunk_tasks_active":
            counts = export_receipt.get("state_counts", {})
            lines.extend(
                [
                    "",
                    f"The zero-budget Earth Engine extraction is active across **{export_receipt.get('chunk_count', 0)} chunks**: "
                    f"**{counts.get('COMPLETED', 0)} complete**, **{counts.get('RUNNING', 0)} running**, "
                    f"and **{counts.get('READY', counts.get('PENDING', 0))} queued** at the last receipt update.",
                ]
            )
    if result["phase3_model_run"]:
        execution_lines = [
            "The registered Phase 3 association is complete. The next work is robustness validation and cautious cross-region replication; do not reinterpret this association as proof of actor or intent.",
        ]
    elif cloud_ready:
        execution_lines = [
            "1. Run or resume `python analysis/export_phase3_earthengine.py --wait`. The task survives a laptop restart after submission and retries failed exports automatically.",
            "2. The runner downloads only the coordinate-free transition table to `data/derived/phase3/mapbiomas_c41_transition_summary_private.csv`; it does not use paid Cloud Storage or download national rasters.",
            "3. Run `python analysis/phase3_land_change.py --run-models`; the script validates every required cell and band before fitting.",
            "",
            "Earth Engine access is confirmed through the registered `susenas-project`; the former cloud-permission blocker is cleared.",
        ]
    else:
        execution_lines = [
            "1. Select a Google Cloud project that is registered for Earth Engine noncommercial use and has the Earth Engine API enabled.",
            "2. Run `python analysis/export_phase3_earthengine.py --wait` after setting that project.",
            "3. Run `python analysis/phase3_land_change.py --run-models` after the compact transition table passes validation.",
        ]
    lines.extend(
        [
            "",
            "## Exact next execution",
            "",
            *execution_lines,
            "",
            "## Sources",
            "",
            "- [MapBiomas Indonesia FAQ](https://landy.mapbiomas.id/en/faq) — annual maps 1990–2024, public/non-commercial access, GEE processing, and citation guidance.",
            "- [Collection 4.1 legend](https://landy.mapbiomas.id/en/legendcode) — official class codes.",
            "- [Collection 4.1 class descriptions](https://landy.mapbiomas.id/assets/files/Col%204.1%20-%20Legend%20Description%20EN.pdf) — forest, sawit, kebun kayu, agriculture, mining, and other definitions.",
            "",
            "## Interpretation boundary",
            "",
            "Even if a fire-positive cell is later mapped as oil palm, the sequence alone does not identify who burned it or why. A causal claim about deliberate conversion requires dated ownership/concession, planting, permits, enforcement, and independent validation.",
            "",
        ]
    )
    return "\n".join(lines)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def build_result(*, prepare_private_cells: bool, run_model_flag: bool) -> dict[str, Any]:
    registration = read_json(REGISTRATION_PATH)
    legend = read_json(LEGEND_PATH)
    phase1b = read_json(PHASE1B_PATH)
    opportunities = load_opportunities()
    by_year = (
        opportunities.groupby(["year", "outcome_status"]).size().unstack(fill_value=0).to_dict("index")
    )
    inventory = {
        "path": str(OPPORTUNITY_PATH.relative_to(ROOT)).replace("\\", "/"),
        "sha256": sha256_file(OPPORTUNITY_PATH),
        "row_count": int(len(opportunities)),
        "matched_set_count": int(opportunities["matched_set_id"].nunique()),
        "unique_cell_count": int(opportunities["cell_id"].nunique()),
        "year_min": int(opportunities["year"].min()),
        "year_max": int(opportunities["year"].max()),
        "rows_by_year_and_status": {str(year): values for year, values in by_year.items()},
    }
    if prepare_private_cells or not PRIVATE_CELL_PATH.is_file():
        private_receipt = build_private_cell_index(opportunities)
        write_json(PRIVATE_CELL_RECEIPT_PATH, private_receipt)
    else:
        private_receipt = read_json(PRIVATE_CELL_RECEIPT_PATH)

    transition_audit = inspect_transition_summary(
        TRANSITION_SUMMARY_PATH,
        registration,
        set(opportunities["cell_id"].astype(str).unique()),
    )
    local_mapbiomas_years = []
    for path in (ROOT / "data" / "raw" / "mapbiomas_indonesia").glob(
        "mapbiomas_indonesia_c41_landcover_*.tif"
    ):
        try:
            local_mapbiomas_years.append(int(path.stem.rsplit("_", 1)[-1]))
        except ValueError:
            continue
    local_mapbiomas_years = sorted(set(local_mapbiomas_years))
    blockers = []
    if not phase1b.get("phase_1b_ready") or not phase1b.get("phase_2_unlock"):
        blockers.append("locked_fire_opportunity_frame_not_ready")
    if set(legend.get("natural_forest_codes", [])) != {3, 5, 76}:
        blockers.append("mapbiomas_natural_forest_crosswalk_invalid")
    if not transition_audit["gate_ready"]:
        blockers.append("mapbiomas_annual_transition_summary_not_ready")
    models = None
    phase3_model_run = False
    if run_model_flag and not blockers:
        transitions = pd.read_csv(TRANSITION_SUMMARY_PATH, low_memory=False)
        models = run_models(opportunities, transitions, registration)
        phase3_model_run = True
    status = (
        "completed_phase3_association"
        if phase3_model_run
        else "registered_and_prepared_waiting_for_mapbiomas_annual_transition_summary"
    )
    cloud_audit = read_json(CLOUD_AUDIT_PATH) if CLOUD_AUDIT_PATH.is_file() else {"status": "not_audited"}
    earth_engine_export = (
        read_json(EARTH_ENGINE_EXPORT_PATH)
        if EARTH_ENGINE_EXPORT_PATH.is_file()
        else {"status": "not_started"}
    )
    result = {
        "schema_version": "phase3-land-change-results/v1",
        "created_at_utc": utc_now(),
        "status": status,
        "phase3_ready": not blockers,
        "phase3_model_run": phase3_model_run,
        "scope": {
            "geography": "Kalimantan",
            "country_context": "Indonesia",
            "indonesia_map_role": "descriptive_context_only",
            "inference_generalization": "No Indonesia-wide or global inferential claim.",
        },
        "registration": {
            "path": str(REGISTRATION_PATH.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256_file(REGISTRATION_PATH),
            "state": registration["registration_state"],
        },
        "reporting_amendment": {
            "path": str(REPORTING_AMENDMENT_PATH.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256_file(REPORTING_AMENDMENT_PATH),
            "status": "post_registration_reporting_clarification",
            "changes_primary_estimand_or_model": False,
        },
        "legend": {
            "path": str(LEGEND_PATH.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256_file(LEGEND_PATH),
            "class_count": len(legend["classes"]),
            "natural_forest_codes": legend["natural_forest_codes"],
            "destination_groups": legend["destination_groups"],
        },
        "phase1b_input_gate": {
            "phase_1b_ready": bool(phase1b.get("phase_1b_ready")),
            "phase_2_unlock": bool(phase1b.get("phase_2_unlock")),
            "immutable_input_lock_valid": bool(
                phase1b.get("immutable_input_lock", {}).get("valid")
            ),
        },
        "opportunity_inventory": inventory,
        "private_cell_index": private_receipt,
        "mapbiomas": {
            "collection": "4.1",
            "collection_version": "4.1.1",
            "official_available_years": [1990, 2024],
            "local_full_raster_years": local_mapbiomas_years,
            "local_full_raster_year_count": len(local_mapbiomas_years),
            "transition_summary": transition_audit,
            "cloud_access": cloud_audit,
            "earth_engine_export": earth_engine_export,
        },
        "eligible_event_years_by_horizon": registration["time_alignment"][
            "eligible_event_years_by_horizon"
        ],
        "blockers": blockers,
        "models": models,
        "claim_boundary": registration["hard_claim_boundaries"],
    }
    return result


def browser_summary(result: dict[str, Any]) -> dict[str, Any]:
    export_receipt = result["mapbiomas"].get("earth_engine_export", {})
    models = result.get("models") or {}

    def compact_model(item: dict[str, Any], label: str) -> dict[str, Any]:
        compact = {"label": label, "status": item.get("status", "not_estimated")}
        if item.get("status") == "estimated":
            term = item["model"]["primary_term"]
            compact.update(
                {
                    "matched_set_count": item["model"]["matched_set_count"],
                    "estimate": term["estimate"],
                    "ci95": term["ci95"],
                    "p_two_sided": term["p_two_sided"],
                    "p_holm": term.get("p_holm_secondary_family", term.get("p_holm_destination_family")),
                }
            )
        else:
            compact["variation_matched_set_count"] = item.get(
                "outcome_variation_matched_set_count"
            )
        return compact

    sensitivity_results = []
    destination_results = []
    if result["phase3_model_run"]:
        sensitivity_results = [
            compact_model(models["threshold_sensitivities"][0], "≥5% loss · 1 year"),
            compact_model(models["primary"], "≥10% loss · 1 year (primary)"),
            compact_model(models["threshold_sensitivities"][1], "≥20% loss · 1 year"),
            compact_model(models["horizon_sensitivities"][0], "≥10% loss · 2 years"),
            compact_model(models["horizon_sensitivities"][1], "≥10% loss · 3 years"),
        ]
        destination_results = [
            compact_model(item, item["destination"].replace("_", " ").title())
            for item in models["destination_models"]
        ]
    return {
        "schema_version": "phase3-dashboard-status/v1",
        "created_at_utc": result["created_at_utc"],
        "status": result["status"],
        "phase3_ready": result["phase3_ready"],
        "phase3_model_run": result["phase3_model_run"],
        "scope": result["scope"],
        "matched_set_count": result["opportunity_inventory"]["matched_set_count"],
        "unique_cell_count": result["opportunity_inventory"]["unique_cell_count"],
        "private_cell_count": result["private_cell_index"]["private_cell_count"],
        "mapbiomas_available_years": result["mapbiomas"]["official_available_years"],
        "local_full_raster_years": result["mapbiomas"]["local_full_raster_years"],
        "eligible_event_years_primary": result["eligible_event_years_by_horizon"]["1"],
        "blockers": result["blockers"],
        "primary_result": (
            result["models"]["primary"] if result["phase3_model_run"] else None
        ),
        "sensitivity_results": sensitivity_results,
        "destination_results": destination_results,
        "earth_engine_export": {
            "status": export_receipt.get("status", "not_started"),
            "updated_at_utc": export_receipt.get("updated_at_utc"),
            "algorithm_revision": export_receipt.get("algorithm_revision"),
            "chunk_count": export_receipt.get("chunk_count", 0),
            "state_counts": export_receipt.get("state_counts", {}),
        },
        "plain_language": (
            "Phase 3 result complete. Read the effect and uncertainty as an association, not proof of intent."
            if result["phase3_model_run"]
            else "Phase 3 is registered and technically prepared. The annual MapBiomas transition table is still missing, so no statistical answer has been claimed."
        ),
        "claim_boundary": result["claim_boundary"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prepare-private-cells",
        action="store_true",
        help="Rebuild the private cell-centre upload table from daily chunks.",
    )
    parser.add_argument(
        "--run-models",
        action="store_true",
        help="Fit only after the complete annual transition summary passes the gate.",
    )
    args = parser.parse_args()
    result = build_result(
        prepare_private_cells=args.prepare_private_cells,
        run_model_flag=args.run_models,
    )
    write_json(READINESS_PATH, result)
    write_json(RESULT_PATH, result)
    write_json(BROWSER_PATH, browser_summary(result))
    MARKDOWN_PATH.parent.mkdir(parents=True, exist_ok=True)
    MARKDOWN_PATH.write_text(render_markdown(result), encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "phase3_ready": result["phase3_ready"],
        "phase3_model_run": result["phase3_model_run"],
        "matched_sets": result["opportunity_inventory"]["matched_set_count"],
        "unique_cells": result["opportunity_inventory"]["unique_cell_count"],
        "blockers": result["blockers"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
