#!/usr/bin/env python3
"""Fit the frozen Phase 2 environmental matched-risk-set models.

The estimator is a conditional logistic likelihood for exactly one fire-positive
cell and four valid negative cells per matched set.  It reports two-way
cell/date cluster-robust uncertainty because cells can recur and conditions on
the same day can share residual weather structure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import logsumexp
from scipy.stats import norm


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wildfire_research.quality import verify_immutable_lock


DEFAULT_FRAME = ROOT / "data" / "derived" / "viirs" / "opportunity_frame.csv"
DEFAULT_REGISTRATION = ROOT / "config" / "phase2_registration.json"
DEFAULT_SPECIFICATION = ROOT / "config" / "phase2_model_specification.json"
DEFAULT_INPUT_LOCK = ROOT / "outputs" / "locks" / "locked_test_inputs.json"
DEFAULT_PHASE1B = ROOT / "outputs" / "quality" / "phase1b_readiness.json"
DEFAULT_JSON = ROOT / "outputs" / "analysis" / "phase2_environmental_results.json"
DEFAULT_MARKDOWN = ROOT / "outputs" / "insights" / "phase2_environmental_association.md"
DEFAULT_BROWSER_JSON = ROOT / "apps" / "evidence-explorer" / "data" / "phase2-environmental.json"

REQUIRED_COLUMNS = {
    "forest_fraction",
    "peat_extent_percent",
    "chirps_precip_1d_mm",
    "chirps_precip_7d_mm",
    "chirps_precip_30d_mm",
    "chirps_precip_90d_mm",
    "evi_prefire",
    "matched_set_id",
    "outcome_status",
    "cell_id",
    "acquisition_utc",
    "valid_opportunity",
    "quality_pass",
    "era5_vpd_mean_72h_kpa",
    "era5_wind_max_24h_ms",
    "era5_rootzone_soil_water_mean_72h",
    "weather_support_status",
    "history_fallback_used",
}

BASE_FEATURES = (
    "forest_fraction_z",
    "log_chirps_precip_7d_z",
    "log_chirps_precip_30d_z",
    "evi_prefire_z",
    "era5_vpd_72h_z",
    "era5_wind_24h_z",
    "rootzone_dryness_72h_z",
)

RAW_TRANSFORMS = {
    "forest_fraction_z": ("forest_fraction", "identity", 1.0),
    "log_chirps_precip_7d_z": ("chirps_precip_7d_mm", "log1p", 1.0),
    "log_chirps_precip_30d_z": ("chirps_precip_30d_mm", "log1p", 1.0),
    "evi_prefire_z": ("evi_prefire", "identity", 1.0),
    "era5_vpd_72h_z": ("era5_vpd_mean_72h_kpa", "identity", 1.0),
    "era5_wind_24h_z": ("era5_wind_max_24h_ms", "identity", 1.0),
    "rootzone_dryness_72h_z": ("era5_rootzone_soil_water_mean_72h", "identity", -1.0),
}

CONDITION_LABELS = {
    "rootzone_dryness_72h_z": "drier root-zone soil over the prior 72 h",
    "era5_vpd_72h_z": "higher VPD over the prior 72 h",
    "era5_wind_24h_z": "higher maximum wind over the prior 24 h",
    "low_evi_prefire_z": "lower pre-fire EVI",
}


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


def _as_bool(series: pd.Series, name: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(bool)
    normalized = series.astype(str).str.strip().str.lower()
    bad = ~normalized.isin({"true", "false", "1", "0"})
    if bad.any():
        raise ValueError(f"{name} contains invalid boolean values")
    return normalized.isin({"true", "1"})


def load_and_validate_frame(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, low_memory=False)
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(f"Phase 2 frame is missing columns: {', '.join(missing)}")
    frame = frame.copy()
    frame["valid_opportunity"] = _as_bool(frame["valid_opportunity"], "valid_opportunity")
    frame["quality_pass"] = _as_bool(frame["quality_pass"], "quality_pass")
    frame["history_fallback_used"] = _as_bool(frame["history_fallback_used"], "history_fallback_used")
    if not frame["valid_opportunity"].all() or not frame["quality_pass"].all():
        raise ValueError("Phase 2 frame contains rows that are not valid, quality-passing opportunities")
    if (frame["weather_support_status"] != "complete_pre_event").any():
        raise ValueError("Phase 2 frame contains incomplete pre-event weather support")
    labels = set(frame["outcome_status"].unique())
    if labels != {"positive", "negative"}:
        raise ValueError(f"Unexpected outcome labels: {sorted(labels)}")
    frame["outcome"] = (frame["outcome_status"] == "positive").astype(np.int8)
    frame["date"] = frame["acquisition_utc"].astype(str).str.slice(0, 10)
    frame["year"] = pd.to_numeric(frame["date"].str.slice(0, 4), errors="raise").astype(int)
    numeric_columns = sorted(
        {item[0] for item in RAW_TRANSFORMS.values()}
        | {
            "peat_extent_percent",
            "chirps_precip_1d_mm",
            "chirps_precip_90d_mm",
        }
    )
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
        if not np.isfinite(frame[column].to_numpy(dtype=float)).all():
            raise ValueError(f"{column} contains missing or non-finite values")
    if ((frame["peat_extent_percent"] < 0) | (frame["peat_extent_percent"] > 100)).any():
        raise ValueError("peat_extent_percent must stay within 0-100")
    sizes = frame.groupby("matched_set_id", sort=False).size()
    positives = frame.groupby("matched_set_id", sort=False)["outcome"].sum()
    if not sizes.eq(5).all() or not positives.eq(1).all():
        raise ValueError("Every matched set must contain exactly one case and four controls")
    if frame.duplicated(["matched_set_id", "cell_id"]).any():
        raise ValueError("A cell appears more than once inside a matched set")
    return frame.sort_values(["matched_set_id", "outcome"], ascending=[True, False], kind="stable").reset_index(drop=True)


def exclude_incomplete_matched_sets(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Apply the pre-fit fail-closed amendment without mutating locked inputs."""

    rainfall = [
        "chirps_precip_1d_mm",
        "chirps_precip_7d_mm",
        "chirps_precip_30d_mm",
        "chirps_precip_90d_mm",
    ]
    model_columns = sorted({item[0] for item in RAW_TRANSFORMS.values()} | {"peat_extent_percent"})
    matrix = frame[model_columns].to_numpy(dtype=float)
    invalid_nonfinite = ~np.isfinite(matrix).all(axis=1)
    invalid_rainfall = frame[rainfall].lt(0).any(axis=1).to_numpy()
    invalid_evi = frame["evi_prefire"].le(-9000).to_numpy()
    invalid = invalid_nonfinite | invalid_rainfall | invalid_evi
    excluded_ids = sorted(frame.loc[invalid, "matched_set_id"].astype(str).unique().tolist())
    excluded_dates = sorted(frame.loc[frame["matched_set_id"].isin(excluded_ids), "date"].unique().tolist())
    filtered = frame.loc[~frame["matched_set_id"].isin(excluded_ids)].copy().reset_index(drop=True)
    return filtered, {
        "rule": "exclude the entire matched set for a negative CHIRPS lag, EVI <= -9000, or non-finite required covariate",
        "invalid_source_row_count": int(invalid.sum()),
        "excluded_matched_set_count": len(excluded_ids),
        "excluded_row_count": int(len(frame) - len(filtered)),
        "excluded_dates": excluded_dates,
        "excluded_matched_set_ids": excluded_ids,
        "imputed_value_count": 0,
    }


def fit_standardization(frame: pd.DataFrame, reference_years: Iterable[int]) -> dict[str, dict[str, float | str]]:
    reference = frame[frame["year"].isin(list(reference_years))]
    if reference.empty:
        raise ValueError("Standardization reference years have no rows")
    stats: dict[str, dict[str, float | str]] = {}
    for feature, (column, transform, direction) in RAW_TRANSFORMS.items():
        values = reference[column].to_numpy(dtype=float)
        if transform == "log1p":
            if (values < 0).any():
                raise ValueError(f"{column} contains negative values before log1p")
            values = np.log1p(values)
        mean = float(values.mean())
        std = float(values.std(ddof=0))
        if not math.isfinite(std) or std <= 0:
            raise ValueError(f"{column} has zero or invalid reference variance")
        stats[feature] = {
            "source": column,
            "transform": transform,
            "direction": float(direction),
            "mean": mean,
            "std": std,
        }
    return stats


def apply_standardization(frame: pd.DataFrame, stats: dict[str, dict[str, float | str]]) -> pd.DataFrame:
    result = frame.copy()
    for feature, values in stats.items():
        source = str(values["source"])
        raw = result[source].to_numpy(dtype=float)
        if values["transform"] == "log1p":
            raw = np.log1p(raw)
        result[feature] = float(values["direction"]) * (
            (raw - float(values["mean"])) / float(values["std"])
        )
    result["low_evi_prefire_z"] = -result["evi_prefire_z"]
    return result


def build_model_matrix(
    frame: pd.DataFrame,
    *,
    peat_threshold: int,
    condition: str,
) -> tuple[np.ndarray, list[str]]:
    if condition not in set(BASE_FEATURES) | {"low_evi_prefire_z"}:
        raise ValueError(f"Unsupported condition: {condition}")
    peat_name = f"peat_ge_{peat_threshold}pct"
    interaction_name = f"{peat_name}_x_{condition}"
    peat = (frame["peat_extent_percent"].to_numpy(dtype=float) >= peat_threshold).astype(float)
    matrix = np.column_stack(
        [frame[name].to_numpy(dtype=float) for name in BASE_FEATURES]
        + [peat, peat * frame[condition].to_numpy(dtype=float)]
    )
    names = [*BASE_FEATURES, peat_name, interaction_name]
    if not np.isfinite(matrix).all():
        raise ValueError("Model matrix contains missing or non-finite values")
    return matrix, names


def conditional_objective(beta: np.ndarray, x_grouped: np.ndarray, y_grouped: np.ndarray) -> tuple[float, np.ndarray]:
    eta = np.einsum("ngp,p->ng", x_grouped, beta)
    log_denom = logsumexp(eta, axis=1)
    case_eta = np.sum(eta * y_grouped, axis=1)
    probabilities = np.exp(eta - log_denom[:, None])
    gradient = np.sum(
        np.einsum("ng,ngp->np", y_grouped - probabilities, x_grouped),
        axis=0,
    )
    return float(-(case_eta - log_denom).sum()), -gradient


def _information_matrix(x_grouped: np.ndarray, probabilities: np.ndarray) -> np.ndarray:
    means = np.einsum("ng,ngp->np", probabilities, x_grouped)
    second = np.einsum("ng,ngp,ngq->npq", probabilities, x_grouped, x_grouped)
    covariance = second - np.einsum("np,nq->npq", means, means)
    return covariance.sum(axis=0)


def _cluster_meat(scores: np.ndarray, labels: pd.Series) -> tuple[np.ndarray, int]:
    codes, uniques = pd.factorize(labels.astype(str), sort=False)
    group_count = len(uniques)
    if group_count < 2:
        raise ValueError("Cluster-robust covariance requires at least two clusters")
    sums = np.zeros((group_count, scores.shape[1]), dtype=float)
    np.add.at(sums, codes, scores)
    meat = sums.T @ sums
    n, p = scores.shape
    correction = (group_count / (group_count - 1)) * ((n - 1) / max(n - p, 1))
    return correction * meat, group_count


def _wald_rows(
    beta: np.ndarray,
    covariance: np.ndarray,
    names: list[str],
) -> list[dict[str, Any]]:
    se = np.sqrt(np.diag(covariance))
    rows: list[dict[str, Any]] = []
    for index, name in enumerate(names):
        estimate = float(beta[index])
        standard_error = float(se[index])
        z = estimate / standard_error if standard_error > 0 else math.nan
        p = float(2 * norm.sf(abs(z))) if math.isfinite(z) else None
        rows.append(
            {
                "term": name,
                "log_odds": estimate,
                "standard_error": standard_error,
                "odds_ratio": float(math.exp(estimate)),
                "ci95": [
                    float(math.exp(estimate - 1.96 * standard_error)),
                    float(math.exp(estimate + 1.96 * standard_error)),
                ],
                "z": float(z) if math.isfinite(z) else None,
                "p_two_sided": p,
            }
        )
    return rows


def fit_conditional_model(
    frame: pd.DataFrame,
    *,
    peat_threshold: int,
    condition: str,
    label: str,
) -> dict[str, Any]:
    if frame.empty:
        raise ValueError(f"Model {label} has no rows")
    matrix, names = build_model_matrix(frame, peat_threshold=peat_threshold, condition=condition)
    y = frame["outcome"].to_numpy(dtype=float)
    group_size = 5
    if len(frame) % group_size:
        raise ValueError("Model rows cannot be reshaped into five-row matched sets")
    x_grouped = matrix.reshape(-1, group_size, matrix.shape[1])
    y_grouped = y.reshape(-1, group_size)
    result = minimize(
        conditional_objective,
        np.zeros(matrix.shape[1], dtype=float),
        args=(x_grouped, y_grouped),
        jac=True,
        method="BFGS",
        options={"gtol": 1e-7, "maxiter": 800},
    )
    beta = np.asarray(result.x, dtype=float)
    eta = np.einsum("ngp,p->ng", x_grouped, beta)
    probabilities = np.exp(eta - logsumexp(eta, axis=1)[:, None])
    information = _information_matrix(x_grouped, probabilities)
    bread = np.linalg.pinv(information, rcond=1e-12)
    row_scores = matrix * (y - probabilities.reshape(-1))[:, None]
    cell_meat, cell_clusters = _cluster_meat(row_scores, frame["cell_id"])
    date_meat, date_clusters = _cluster_meat(row_scores, frame["date"])
    intersection = frame["cell_id"].astype(str) + "|" + frame["date"].astype(str)
    intersection_meat, intersection_clusters = _cluster_meat(row_scores, intersection)
    two_way_meat = cell_meat + date_meat - intersection_meat
    covariance = bread @ two_way_meat @ bread
    covariance = (covariance + covariance.T) / 2
    covariance_method = "two_way_cell_and_date_cluster_robust"
    covariance_warning = None
    if not np.isfinite(np.diag(covariance)).all() or (np.diag(covariance) <= 0).any():
        covariance = bread @ cell_meat @ bread
        covariance = (covariance + covariance.T) / 2
        covariance_method = "cell_cluster_robust_fallback"
        covariance_warning = "Two-way covariance had a non-positive or invalid diagonal; cell-only covariance was used."
    coefficients = _wald_rows(beta, covariance, names)
    interaction_term = f"peat_ge_{peat_threshold}pct_x_{condition}"
    interaction = next(row for row in coefficients if row["term"] == interaction_term)
    gradient_norm = float(np.max(np.abs(conditional_objective(beta, x_grouped, y_grouped)[1])))
    converged = bool(result.success or gradient_norm < 1e-5)
    if not converged:
        raise RuntimeError(
            f"Model {label} did not converge: {result.message}; max gradient={gradient_norm:.3g}"
        )
    peat = (frame["peat_extent_percent"] >= peat_threshold).astype(int)
    mixed_sets = int(
        pd.DataFrame({"set": frame["matched_set_id"], "peat": peat})
        .groupby("set", sort=False)["peat"]
        .nunique()
        .gt(1)
        .sum()
    )
    return {
        "label": label,
        "status": "estimated",
        "model": "conditional logistic regression; matched-set intercept conditioned out",
        "peat_threshold_percent": peat_threshold,
        "condition": condition,
        "condition_label": CONDITION_LABELS[condition],
        "row_count": int(len(frame)),
        "case_count": int(frame["outcome"].sum()),
        "control_count": int((1 - frame["outcome"]).sum()),
        "matched_set_count": int(frame["matched_set_id"].nunique()),
        "acquisition_date_count": int(frame["date"].nunique()),
        "unique_cell_count": int(frame["cell_id"].nunique()),
        "mixed_peat_matched_set_count": mixed_sets,
        "history_fallback_row_count": int(frame["history_fallback_used"].sum()),
        "convergence": {
            "converged": converged,
            "optimizer_success": bool(result.success),
            "message": str(result.message),
            "iterations": int(getattr(result, "nit", 0)),
            "max_abs_gradient": gradient_norm,
            "information_condition_number": float(np.linalg.cond(information)),
        },
        "uncertainty": {
            "method": covariance_method,
            "cell_clusters": cell_clusters,
            "date_clusters": date_clusters,
            "cell_date_clusters": intersection_clusters,
            "warning": covariance_warning,
        },
        "log_likelihood": float(-result.fun),
        "interaction": interaction,
        "coefficients": coefficients,
        "_beta": beta,
        "_feature_names": names,
    }


def evaluate_predictions(
    frame: pd.DataFrame,
    beta: np.ndarray,
    *,
    peat_threshold: int,
    condition: str,
    label: str,
) -> dict[str, Any]:
    matrix, _ = build_model_matrix(frame, peat_threshold=peat_threshold, condition=condition)
    y = frame["outcome"].to_numpy(dtype=float).reshape(-1, 5)
    eta = (matrix @ beta).reshape(-1, 5)
    probabilities = np.exp(eta - logsumexp(eta, axis=1)[:, None])
    case_index = y.argmax(axis=1)
    case_probabilities = probabilities[np.arange(len(probabilities)), case_index]
    case_scores = eta[np.arange(len(eta)), case_index]
    greater = (eta > case_scores[:, None] + 1e-12).sum(axis=1)
    tied = (np.abs(eta - case_scores[:, None]) <= 1e-12).sum(axis=1)
    top1_credit = np.where(greater == 0, 1.0 / tied, 0.0)
    average_rank = 1.0 + greater + (tied - 1) / 2.0
    log_loss = float(-np.log(np.clip(case_probabilities, 1e-15, 1.0)).mean())
    uniform_log_loss = float(math.log(5))
    return {
        "label": label,
        "year_min": int(frame["year"].min()),
        "year_max": int(frame["year"].max()),
        "matched_set_count": int(len(probabilities)),
        "conditional_log_loss": log_loss,
        "uniform_log_loss": uniform_log_loss,
        "log_loss_improvement_vs_uniform": uniform_log_loss - log_loss,
        "top1_recall_tie_fractional": float(top1_credit.mean()),
        "uniform_expected_top1_recall": 0.2,
        "mean_reciprocal_rank": float((1.0 / average_rank).mean()),
        "top5_recall": 1.0,
        "top5_interpretation": "structurally non-informative because every sampled matched set contains five cells",
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


def _distribution_rows(frame: pd.DataFrame) -> list[dict[str, Any]]:
    columns = [
        "peat_extent_percent",
        "chirps_precip_7d_mm",
        "chirps_precip_30d_mm",
        "evi_prefire",
        "era5_vpd_mean_72h_kpa",
        "era5_wind_max_24h_ms",
        "era5_rootzone_soil_water_mean_72h",
    ]
    rows: list[dict[str, Any]] = []
    for column in columns:
        for outcome, subset in frame.groupby("outcome_status", sort=True):
            values = subset[column].to_numpy(dtype=float)
            rows.append(
                {
                    "variable": column,
                    "outcome": str(outcome),
                    "n": int(len(values)),
                    "mean": float(values.mean()),
                    "median": float(np.median(values)),
                    "standard_deviation": float(values.std(ddof=1)),
                    "p25": float(np.quantile(values, 0.25)),
                    "p75": float(np.quantile(values, 0.75)),
                    "p05": float(np.quantile(values, 0.05)),
                    "p95": float(np.quantile(values, 0.95)),
                }
            )
    return rows


def _public_model(model: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in model.items() if not key.startswith("_")}


def _interpret_primary(interaction: dict[str, Any]) -> dict[str, str]:
    low, high = interaction["ci95"]
    estimate = interaction["odds_ratio"]
    if low > 1:
        classification = "statistically_detectable_higher_under_dryness"
        text = "The matched-set data support a higher peat-associated detection-odds gradient as root-zone soil becomes drier."
    elif high < 1:
        classification = "statistically_detectable_lower_under_dryness"
        text = "The matched-set data support a lower peat-associated detection-odds gradient as root-zone soil becomes drier."
    else:
        classification = "inconclusive"
        text = "The interval includes no interaction, so this analysis does not establish that drier root-zone soil changes the peat-associated detection-odds gradient."
    return {
        "classification": classification,
        "plain_language": text,
        "effect_definition": f"Interaction OR {estimate:.3f} per one development-period SD increase in dryness, comparing ≥50% versus <50% peat extent.",
    }


def run_analysis(
    *,
    frame_path: Path = DEFAULT_FRAME,
    registration_path: Path = DEFAULT_REGISTRATION,
    specification_path: Path = DEFAULT_SPECIFICATION,
    input_lock_path: Path = DEFAULT_INPUT_LOCK,
    phase1b_path: Path = DEFAULT_PHASE1B,
) -> dict[str, Any]:
    for path in (frame_path, registration_path, specification_path, input_lock_path, phase1b_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    phase1b = read_json(phase1b_path)
    if phase1b.get("phase_1b_ready") is not True or phase1b.get("phase_2_unlock") is not True:
        raise RuntimeError("Phase 2 is still locked by the Phase 1B readiness artifact")
    lock = verify_immutable_lock(ROOT, input_lock_path)
    if lock.get("valid") is not True:
        raise RuntimeError(f"Immutable input lock is invalid: {lock.get('reason')}")
    registration = read_json(registration_path)
    specification = read_json(specification_path)
    if specification.get("schema_version") != "environmental-phase2-model-specification/v1":
        raise ValueError("Unsupported Phase 2 model specification")
    locked_frame = load_and_validate_frame(frame_path)
    frame, prefit_qa = exclude_incomplete_matched_sets(locked_frame)
    expected_years = registration["study_years"]
    if sorted(frame["year"].unique().tolist()) != expected_years:
        raise ValueError("Frame years differ from the registered study years")
    reference_years = specification["design"]["standardization_reference_years"]
    standardization = fit_standardization(frame, reference_years)
    analysis = apply_standardization(frame, standardization)

    primary = fit_conditional_model(
        analysis,
        peat_threshold=50,
        condition="rootzone_dryness_72h_z",
        label="primary_full_2015_2025",
    )
    fallback_sets = analysis.loc[analysis["history_fallback_used"], "matched_set_id"].unique()
    no_fallback_frame = analysis[~analysis["matched_set_id"].isin(fallback_sets)].copy()
    fallback_exclusion = fit_conditional_model(
        no_fallback_frame,
        peat_threshold=50,
        condition="rootzone_dryness_72h_z",
        label="mandatory_exclude_history_fallback",
    )
    threshold_models = [
        fit_conditional_model(
            analysis,
            peat_threshold=threshold,
            condition="rootzone_dryness_72h_z",
            label=f"peat_threshold_{threshold}pct",
        )
        for threshold in (25, 75)
    ]
    locked_test = fit_conditional_model(
        analysis[analysis["year"].isin([2024, 2025])].copy(),
        peat_threshold=50,
        condition="rootzone_dryness_72h_z",
        label="locked_test_2024_2025_association",
    )
    secondary = [
        fit_conditional_model(
            analysis,
            peat_threshold=50,
            condition=condition,
            label=f"secondary_{condition}",
        )
        for condition in ("era5_vpd_72h_z", "era5_wind_24h_z", "low_evi_prefire_z")
    ]
    adjusted = holm_adjust([float(model["interaction"]["p_two_sided"]) for model in secondary])
    for model, p_adjusted in zip(secondary, adjusted, strict=True):
        model["interaction"]["p_holm_three_secondary_conditions"] = p_adjusted

    development = analysis[analysis["year"].isin([2018, 2019, 2020, 2021, 2022])].copy()
    predictive_fit = fit_conditional_model(
        development,
        peat_threshold=50,
        condition="rootzone_dryness_72h_z",
        label="prediction_development_fit_2018_2022",
    )
    predictive_beta = predictive_fit["_beta"]
    prediction = {
        "fit": _public_model(predictive_fit),
        "evaluations": [
            evaluate_predictions(
                analysis[analysis["year"].isin(years)].copy(),
                predictive_beta,
                peat_threshold=50,
                condition="rootzone_dryness_72h_z",
                label=label,
            )
            for label, years in (
                ("development_2018_2022", [2018, 2019, 2020, 2021, 2022]),
                ("rehearsal_2023", [2023]),
                ("locked_test_2024_2025", [2024, 2025]),
            )
        ],
    }

    result = {
        "schema_version": "environmental-phase2-results/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "completed_environmental_association",
        "phase": "Phase 2 -- environmental matched-risk-set association",
        "track_id": "environmental_daily_grid",
        "scope": "Kalimantan baseline-natural-forest cells, July-November 2015-2025",
        "human_access_confirmatory_track_status": "not_identifiable_missing_dated_exposure",
        "provenance": {
            "input_frame": frame_path.relative_to(ROOT).as_posix(),
            "input_frame_sha256": sha256_file(frame_path),
            "input_registration": registration_path.relative_to(ROOT).as_posix(),
            "input_registration_sha256": sha256_file(registration_path),
            "model_specification": specification_path.relative_to(ROOT).as_posix(),
            "model_specification_sha256": sha256_file(specification_path),
            "immutable_input_lock": {
                "path": input_lock_path.relative_to(ROOT).as_posix(),
                "valid_at_fit": True,
                "lock_sha256": lock.get("lock_sha256"),
                "inventory_sha256": lock.get("recorded_inventory_sha256"),
                "file_count": lock.get("recorded_file_count"),
            },
        },
        "data_summary": {
            "locked_input_row_count": int(len(locked_frame)),
            "row_count": int(len(analysis)),
            "case_count": int(analysis["outcome"].sum()),
            "control_count": int((1 - analysis["outcome"]).sum()),
            "matched_set_count": int(analysis["matched_set_id"].nunique()),
            "unique_cell_count": int(analysis["cell_id"].nunique()),
            "acquisition_date_count": int(analysis["date"].nunique()),
            "history_fallback_row_count": int(analysis["history_fallback_used"].sum()),
            "year_counts": [
                {
                    "year": int(year),
                    "rows": int(len(group)),
                    "cases": int(group["outcome"].sum()),
                    "matched_sets": int(group["matched_set_id"].nunique()),
                }
                for year, group in analysis.groupby("year", sort=True)
            ],
            "distributions": _distribution_rows(analysis),
        },
        "pre_fit_data_quality": prefit_qa,
        "standardization": standardization,
        "primary_model": _public_model(primary),
        "primary_interpretation": _interpret_primary(primary["interaction"]),
        "mandatory_sensitivities": {
            "exclude_history_fallback": _public_model(fallback_exclusion),
            "peat_thresholds": [_public_model(model) for model in threshold_models],
            "locked_test_period": _public_model(locked_test),
        },
        "secondary_condition_models": [_public_model(model) for model in secondary],
        "prediction": prediction,
        "interpretation_guardrails": specification["interpretation_rules"],
        "next_phase": "Phase 3 may prepare the fire-to-land-change association, while Phase 2 can add separately registered drainage and ENSO interaction sensitivities.",
    }
    return result


def _fmt(value: float | None, digits: int = 3) -> str:
    return "NA" if value is None else f"{value:.{digits}f}"


def render_markdown(result: dict[str, Any]) -> str:
    primary = result["primary_model"]["interaction"]
    fallback = result["mandatory_sensitivities"]["exclude_history_fallback"]["interaction"]
    locked = result["mandatory_sensitivities"]["locked_test_period"]["interaction"]
    prediction = {row["label"]: row for row in result["prediction"]["evaluations"]}
    lines = [
        "# Phase 2 environmental association",
        "",
        f"**Status:** complete for the registered environmental daily-grid track. **Human-access/intent/governance status:** still not identifiable.",
        "",
        "## Question answered",
        "",
        "Within exact daily 1:4 matched sets of baseline-natural-forest cells in Kalimantan, does the peat-associated fire-detection gradient change when pre-event environmental conditions are more adverse? The primary test is peat extent ≥50% interacted with drier ERA5-Land root-zone soil over the prior 72 hours.",
        "",
        "This is a within-matched-set association for detectable first-observed fire, not absolute ignition probability, burned area, peat condition, deliberate burning, plantation expansion, or government performance.",
        "",
        "## Primary result",
        "",
        f"- Interaction odds ratio: **{_fmt(primary['odds_ratio'])}** per one development-period SD increase in dryness.",
        f"- 95% CI: **{_fmt(primary['ci95'][0])}–{_fmt(primary['ci95'][1])}**; two-sided p = **{_fmt(primary['p_two_sided'])}**.",
        f"- Interpretation: {result['primary_interpretation']['plain_language']}",
        f"- Support: {result['primary_model']['matched_set_count']:,} matched sets; {result['primary_model']['mixed_peat_matched_set_count']:,} contain both ≥50% and <50% peat cells.",
        "",
        "The interaction odds ratio compares how the odds change with dryness in cells above versus below the peat threshold. It is not the overall odds ratio for all peatland and does not show that every mapped peat cell burned.",
        "",
        "## Mandatory robustness checks",
        "",
        "| Check | Interaction OR | 95% CI | p | Matched sets |",
        "|---|---:|---:|---:|---:|",
        f"| Primary, all registered days | {_fmt(primary['odds_ratio'])} | {_fmt(primary['ci95'][0])}–{_fmt(primary['ci95'][1])} | {_fmt(primary['p_two_sided'])} | {result['primary_model']['matched_set_count']:,} |",
        f"| Exclude fallback-history dates | {_fmt(fallback['odds_ratio'])} | {_fmt(fallback['ci95'][0])}–{_fmt(fallback['ci95'][1])} | {_fmt(fallback['p_two_sided'])} | {result['mandatory_sensitivities']['exclude_history_fallback']['matched_set_count']:,} |",
    ]
    for model in result["mandatory_sensitivities"]["peat_thresholds"]:
        effect = model["interaction"]
        lines.append(
            f"| Peat threshold ≥{model['peat_threshold_percent']}% | {_fmt(effect['odds_ratio'])} | {_fmt(effect['ci95'][0])}–{_fmt(effect['ci95'][1])} | {_fmt(effect['p_two_sided'])} | {model['matched_set_count']:,} |"
        )
    lines.extend(
        [
            f"| Locked 2024–2025 only | {_fmt(locked['odds_ratio'])} | {_fmt(locked['ci95'][0])}–{_fmt(locked['ci95'][1])} | {_fmt(locked['p_two_sided'])} | {result['mandatory_sensitivities']['locked_test_period']['matched_set_count']:,} |",
            "",
            "Threshold and fallback runs are robustness checks. They cannot be selected after the fact to replace the registered ≥50% primary result.",
            "",
            "## Other peat-condition interactions",
            "",
            "| Condition (one adverse SD) | Interaction OR | 95% CI | raw p | Holm p |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for model in result["secondary_condition_models"]:
        effect = model["interaction"]
        lines.append(
            f"| {model['condition_label']} | {_fmt(effect['odds_ratio'])} | {_fmt(effect['ci95'][0])}–{_fmt(effect['ci95'][1])} | {_fmt(effect['p_two_sided'])} | {_fmt(effect['p_holm_three_secondary_conditions'])} |"
        )
    test = prediction["locked_test_2024_2025"]
    rehearsal = prediction["rehearsal_2023"]
    lines.extend(
        [
            "",
            "## Held-out prediction check",
            "",
            "The frozen model was fitted only on 2018–2022, rehearsed on 2023, then evaluated on the locked 2024–2025 sets.",
            "",
            "| Split | Conditional log loss | Uniform log loss | Improvement | Top-1 recall | MRR |",
            "|---|---:|---:|---:|---:|---:|",
            f"| 2023 rehearsal | {_fmt(rehearsal['conditional_log_loss'])} | {_fmt(rehearsal['uniform_log_loss'])} | {_fmt(rehearsal['log_loss_improvement_vs_uniform'])} | {_fmt(rehearsal['top1_recall_tie_fractional'])} | {_fmt(rehearsal['mean_reciprocal_rank'])} |",
            f"| 2024–2025 locked test | {_fmt(test['conditional_log_loss'])} | {_fmt(test['uniform_log_loss'])} | {_fmt(test['log_loss_improvement_vs_uniform'])} | {_fmt(test['top1_recall_tie_fractional'])} | {_fmt(test['mean_reciprocal_rank'])} |",
            "",
            "Top-5 recall is exactly 1 by construction because the stored design contains one case among five sampled cells; it is therefore not used as evidence of predictive skill.",
            "",
            "## Data and uncertainty",
            "",
            f"The analysis contains {result['data_summary']['row_count']:,} rows: {result['data_summary']['case_count']:,} cases and {result['data_summary']['control_count']:,} controls in {result['data_summary']['matched_set_count']:,} exact matched sets. Uncertainty is clustered by recurring cell and acquisition date. The Phase 1B input lock was valid at fit time.",
            "",
            "## Boundaries",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in result["interpretation_guardrails"])
    lines.extend(
        [
            "",
            "## Next work",
            "",
            result["next_phase"],
            "",
        ]
    )
    return "\n".join(lines)


def browser_summary(result: dict[str, Any]) -> dict[str, Any]:
    primary = result["primary_model"]["interaction"]
    test = next(row for row in result["prediction"]["evaluations"] if row["label"] == "locked_test_2024_2025")
    sensitivities = [
        {
            "label": "Exclude fallback-history dates",
            "odds_ratio": result["mandatory_sensitivities"]["exclude_history_fallback"]["interaction"]["odds_ratio"],
            "ci95": result["mandatory_sensitivities"]["exclude_history_fallback"]["interaction"]["ci95"],
            "p_two_sided": result["mandatory_sensitivities"]["exclude_history_fallback"]["interaction"]["p_two_sided"],
        }
    ]
    sensitivities.extend(
        {
            "label": f"Peat threshold ≥{model['peat_threshold_percent']}%",
            "odds_ratio": model["interaction"]["odds_ratio"],
            "ci95": model["interaction"]["ci95"],
            "p_two_sided": model["interaction"]["p_two_sided"],
        }
        for model in result["mandatory_sensitivities"]["peat_thresholds"]
    )
    locked = result["mandatory_sensitivities"]["locked_test_period"]
    sensitivities.append(
        {
            "label": "Locked 2024–2025 association",
            "odds_ratio": locked["interaction"]["odds_ratio"],
            "ci95": locked["interaction"]["ci95"],
            "p_two_sided": locked["interaction"]["p_two_sided"],
        }
    )
    return {
        "schema_version": result["schema_version"],
        "created_at_utc": result["created_at_utc"],
        "status": result["status"],
        "scope": result["scope"],
        "human_access_confirmatory_track_status": result["human_access_confirmatory_track_status"],
        "data_summary": {
            key: result["data_summary"][key]
            for key in ("row_count", "case_count", "control_count", "matched_set_count", "history_fallback_row_count")
        },
        "pre_fit_excluded_matched_set_count": result["pre_fit_data_quality"]["excluded_matched_set_count"],
        "primary": {
            "label": "Peat ≥50% × drier root-zone soil (72 h)",
            "odds_ratio": primary["odds_ratio"],
            "ci95": primary["ci95"],
            "p_two_sided": primary["p_two_sided"],
            "classification": result["primary_interpretation"]["classification"],
            "interpretation": result["primary_interpretation"]["plain_language"],
            "mixed_peat_matched_set_count": result["primary_model"]["mixed_peat_matched_set_count"],
        },
        "sensitivities": sensitivities,
        "secondary_conditions": [
            {
                "label": model["condition_label"],
                "odds_ratio": model["interaction"]["odds_ratio"],
                "ci95": model["interaction"]["ci95"],
                "p_holm": model["interaction"]["p_holm_three_secondary_conditions"],
            }
            for model in result["secondary_condition_models"]
        ],
        "locked_test_prediction": {
            "conditional_log_loss": test["conditional_log_loss"],
            "uniform_log_loss": test["uniform_log_loss"],
            "top1_recall": test["top1_recall_tie_fractional"],
            "mean_reciprocal_rank": test["mean_reciprocal_rank"],
        },
        "interpretation_guardrails": result["interpretation_guardrails"],
    }


def write_outputs(result: dict[str, Any], json_path: Path, markdown_path: Path, browser_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    browser_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(result), encoding="utf-8")
    browser_path.write_text(json.dumps(browser_summary(result), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frame", type=Path, default=DEFAULT_FRAME)
    parser.add_argument("--registration", type=Path, default=DEFAULT_REGISTRATION)
    parser.add_argument("--specification", type=Path, default=DEFAULT_SPECIFICATION)
    parser.add_argument("--input-lock", type=Path, default=DEFAULT_INPUT_LOCK)
    parser.add_argument("--phase1b", type=Path, default=DEFAULT_PHASE1B)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--browser-json", type=Path, default=DEFAULT_BROWSER_JSON)
    args = parser.parse_args()
    result = run_analysis(
        frame_path=args.frame,
        registration_path=args.registration,
        specification_path=args.specification,
        input_lock_path=args.input_lock,
        phase1b_path=args.phase1b,
    )
    write_outputs(result, args.json, args.markdown, args.browser_json)
    primary = result["primary_model"]["interaction"]
    print(
        json.dumps(
            {
                "status": result["status"],
                "primary_interaction_or": primary["odds_ratio"],
                "primary_ci95": primary["ci95"],
                "primary_p_two_sided": primary["p_two_sided"],
                "classification": result["primary_interpretation"]["classification"],
                "json": str(args.json.relative_to(ROOT)),
                "markdown": str(args.markdown.relative_to(ROOT)),
                "browser_json": str(args.browser_json.relative_to(ROOT)),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
