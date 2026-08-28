#!/usr/bin/env python3
"""Run publication-facing diagnostics without changing the frozen Phase 3 primary model.

These analyses are explicitly diagnostic or sensitivity analyses. They audit
selection, influential matched sets, temporal heterogeneity, spatial
dependence, a conditional-logit alternative, a continuous outcome, and a
pre-exposure negative-control outcome. None replaces the registered primary
adjusted risk difference.
"""

from __future__ import annotations

import json
import math
import sys
import warnings
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
import pandas as pd
from scipy.stats import norm
from statsmodels.discrete.conditional_models import ConditionalLogit

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import analysis.phase3_land_change as phase3


RESULT_PATH = ROOT / "outputs" / "analysis" / "phase3_publication_robustness.json"
REPORT_PATH = ROOT / "outputs" / "insights" / "phase3_publication_robustness.md"
FIGURE_ROOT = ROOT / "publication" / "figures"
TABLE_ROOT = ROOT / "publication" / "tables"
BROWSER_PATH = ROOT / "apps" / "evidence-explorer" / "data" / "phase3-status.json"


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def _candidate_primary_frame(
    opportunities: pd.DataFrame,
    transitions: pd.DataFrame,
    registration: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return row-level candidates and one non-exclusive reason row per set."""

    pieces: list[pd.DataFrame] = []
    for year in registration["time_alignment"]["eligible_event_years_by_horizon"]["1"]:
        source = opportunities[opportunities["year"] == year].copy()
        columns = {
            f"pre_natural_fraction_{year}": "pre_natural_fraction",
            f"pre_observed_fraction_{year}": "pre_observed_fraction",
            f"post_observed_fraction_{year}_h1": "post_observed_fraction",
            f"loss_fraction_cell_{year}_h1": "transition_fraction_cell",
        }
        lookup = transitions[["cell_id", *columns]].rename(columns=columns)
        pieces.append(source.merge(lookup, on="cell_id", how="left", validate="many_to_one"))
    frame = pd.concat(pieces, ignore_index=True)
    numeric_columns = [
        "pre_natural_fraction",
        "pre_observed_fraction",
        "post_observed_fraction",
        "transition_fraction_cell",
    ]
    numeric = frame[numeric_columns].apply(pd.to_numeric, errors="coerce")
    finite = np.isfinite(numeric.to_numpy(dtype=float)).all(axis=1)
    pre_min = float(registration["eligibility"]["pre_index_minimum_natural_forest_fraction"])
    observed_min = float(registration["eligibility"]["minimum_pre_and_followup_observed_fraction"])
    reason_flags = pd.DataFrame(
        {
            "nonfinite_transition_input": ~finite,
            "pre_index_forest_below_70_percent": finite & (numeric["pre_natural_fraction"] < pre_min),
            "pre_map_observed_below_95_percent": finite & (numeric["pre_observed_fraction"] < observed_min),
            "followup_map_observed_below_95_percent": finite & (numeric["post_observed_fraction"] < observed_min),
            "transition_fraction_out_of_range": finite
            & (
                (numeric["transition_fraction_cell"] < 0)
                | (numeric["transition_fraction_cell"] > numeric["pre_natural_fraction"] + 1e-8)
            ),
            "negative_chirps_sentinel": frame[["chirps_precip_7d_mm", "chirps_precip_30d_mm"]]
            .lt(0)
            .any(axis=1),
        },
        index=frame.index,
    )
    set_flags = reason_flags.assign(matched_set_id=frame["matched_set_id"].astype(str)).groupby(
        "matched_set_id", sort=False
    ).any()
    set_flags["excluded"] = set_flags.any(axis=1)
    frame["included_primary"] = ~frame["matched_set_id"].astype(str).map(set_flags["excluded"])
    return frame, set_flags.reset_index()


def _standardized_mean_difference(included: pd.Series, excluded: pd.Series) -> float | None:
    left = pd.to_numeric(included, errors="coerce").dropna().to_numpy(dtype=float)
    right = pd.to_numeric(excluded, errors="coerce").dropna().to_numpy(dtype=float)
    if len(left) < 2 or len(right) < 2:
        return None
    pooled = math.sqrt((left.var(ddof=1) + right.var(ddof=1)) / 2)
    if not math.isfinite(pooled) or pooled == 0:
        return 0.0 if float(left.mean()) == float(right.mean()) else None
    return float((left.mean() - right.mean()) / pooled)


def attrition_audit(candidate: pd.DataFrame, set_flags: pd.DataFrame) -> dict[str, Any]:
    cases = candidate[candidate["fire_positive"] == 1].copy()
    variables = [
        "forest_fraction",
        "peat_extent_percent",
        "chirps_precip_7d_mm",
        "chirps_precip_30d_mm",
        "evi_prefire",
        "era5_vpd_mean_72h_kpa",
        "era5_wind_max_24h_ms",
        "era5_rootzone_soil_water_mean_72h",
        "pre_natural_fraction",
    ]
    comparisons: list[dict[str, Any]] = []
    for variable in variables:
        kept = pd.to_numeric(cases.loc[cases["included_primary"], variable], errors="coerce")
        dropped = pd.to_numeric(cases.loc[~cases["included_primary"], variable], errors="coerce")
        comparisons.append(
            {
                "variable": variable,
                "included_mean": float(kept.mean()),
                "included_median": float(kept.median()),
                "excluded_mean": float(dropped.mean()),
                "excluded_median": float(dropped.median()),
                "standardized_mean_difference": _standardized_mean_difference(kept, dropped),
            }
        )
    finite_smd = [
        abs(item["standardized_mean_difference"])
        for item in comparisons
        if item["standardized_mean_difference"] is not None
    ]
    years = (
        cases.groupby(["year", "included_primary"]).size().unstack(fill_value=0).reset_index()
    )
    for value in (False, True):
        if value not in years:
            years[value] = 0
    years = years.rename(columns={False: "excluded_sets", True: "included_sets"})
    years["candidate_sets"] = years["included_sets"] + years["excluded_sets"]
    years["included_share"] = years["included_sets"] / years["candidate_sets"]
    reason_counts = {
        column: int(set_flags[column].sum())
        for column in set_flags.columns
        if column not in {"matched_set_id", "excluded"}
    }
    included = int((~set_flags["excluded"]).sum())
    excluded = int(set_flags["excluded"].sum())
    return {
        "candidate_matched_set_count": int(len(set_flags)),
        "included_matched_set_count": included,
        "excluded_matched_set_count": excluded,
        "excluded_share": excluded / len(set_flags),
        "reason_counts_nonexclusive": reason_counts,
        "case_covariate_comparisons": comparisons,
        "maximum_absolute_standardized_mean_difference": max(finite_smd) if finite_smd else None,
        "variables_above_abs_smd_0_10": [
            item["variable"]
            for item in comparisons
            if item["standardized_mean_difference"] is not None
            and abs(item["standardized_mean_difference"]) > 0.10
        ],
        "year_flow": years.to_dict("records"),
    }


def _within_design(
    frame: pd.DataFrame, outcome_column: str
) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    work, _ = phase3._standardize_covariates(frame, range(2015, 2023))
    features = ["fire_positive", *[f"{item[0]}_z" for item in phase3.MODEL_COVARIATES]]
    groups = work["matched_set_id"].astype(str).to_numpy()
    y = pd.to_numeric(work[outcome_column], errors="raise").to_numpy(dtype=float)
    x = work[features].to_numpy(dtype=float)
    y_within = y - pd.Series(y).groupby(groups, sort=False).transform("mean").to_numpy()
    x_within = np.empty_like(x)
    for index in range(x.shape[1]):
        x_within[:, index] = x[:, index] - pd.Series(x[:, index]).groupby(
            groups, sort=False
        ).transform("mean").to_numpy()
    bread = np.linalg.pinv(x_within.T @ x_within, rcond=1e-12)
    beta = bread @ (x_within.T @ y_within)
    residual = y_within - x_within @ beta
    return work, x_within, beta, residual, bread


def influence_audit(primary_frame: pd.DataFrame) -> dict[str, Any]:
    work, x_within, _, residual, _ = _within_design(primary_frame, "land_change_outcome")
    scores = x_within * residual[:, None]
    grouped = (
        pd.DataFrame(scores)
        .assign(matched_set_id=work["matched_set_id"].astype(str).to_numpy())
        .groupby("matched_set_id", sort=False)
        .sum()
    )
    norms = pd.Series(np.linalg.norm(grouped.to_numpy(dtype=float), axis=1), index=grouped.index)
    sensitivities = []
    for share in (0.005, 0.01):
        count = max(1, int(math.ceil(len(norms) * share)))
        excluded_ids = set(norms.nlargest(count).index)
        reduced = primary_frame[~primary_frame["matched_set_id"].astype(str).isin(excluded_ids)]
        model = phase3.fit_within_set_lpm(reduced, outcome_column="land_change_outcome")
        sensitivities.append(
            {
                "excluded_top_score_share": share,
                "excluded_matched_set_count": count,
                "remaining_matched_set_count": model["matched_set_count"],
                "primary_term": model["primary_term"],
            }
        )
    return {
        "diagnostic": "matched-set score-norm influence screening",
        "matched_set_count": int(len(norms)),
        "score_norm_quantiles": {
            "p50": float(norms.quantile(0.50)),
            "p90": float(norms.quantile(0.90)),
            "p95": float(norms.quantile(0.95)),
            "p99": float(norms.quantile(0.99)),
            "maximum": float(norms.max()),
        },
        "exclusion_sensitivities": sensitivities,
        "set_identifiers_released": False,
    }


def conditional_logit_sensitivity(primary_frame: pd.DataFrame) -> dict[str, Any]:
    work, _ = phase3._standardize_covariates(primary_frame, range(2015, 2023))
    features = ["fire_positive", *[f"{item[0]}_z" for item in phase3.MODEL_COVARIATES]]
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        model = ConditionalLogit(
            work["land_change_outcome"].astype(float),
            work[features],
            groups=work["matched_set_id"].astype(str),
        )
        fitted = model.fit(method="bfgs", maxiter=300, disp=False)
    coefficient = float(fitted.params["fire_positive"])
    standard_error = float(fitted.bse["fire_positive"])
    return {
        "model": "conditional logistic regression with matched-set conditional likelihood",
        "effect_measure": "conditional odds ratio",
        "input_matched_set_count": int(work["matched_set_id"].nunique()),
        "outcome_variation_matched_set_count": int(
            work.groupby("matched_set_id")["land_change_outcome"].nunique().gt(1).sum()
        ),
        "coefficient": coefficient,
        "standard_error": standard_error,
        "odds_ratio": math.exp(coefficient),
        "ci95": [
            math.exp(coefficient - 1.96 * standard_error),
            math.exp(coefficient + 1.96 * standard_error),
        ],
        "p_two_sided": float(2 * norm.sf(abs(coefficient / standard_error))),
        "converged": bool(
            np.isfinite(fitted.params.to_numpy(dtype=float)).all()
            and np.isfinite(fitted.bse.to_numpy(dtype=float)).all()
        ),
        "convergence_check": "Finite parameter and standard-error vectors; this statsmodels result class does not expose an optimizer convergence flag.",
        "warning_messages": sorted({str(item.message) for item in captured}),
        "uncertainty_limit": "Model-based standard error; used only as an alternative-estimator sensitivity, not a replacement for the registered two-way clustered risk difference.",
    }


def temporal_sensitivities(primary_frame: pd.DataFrame) -> dict[str, Any]:
    by_year = []
    for year, subset in primary_frame.groupby("year", sort=True):
        model = phase3.fit_within_set_lpm(
            subset.copy(), outcome_column="land_change_outcome", reference_years=[int(year)]
        )
        by_year.append(
            {
                "year": int(year),
                "matched_set_count": model["matched_set_count"],
                "outcome_variation_matched_set_count": model[
                    "outcome_variation_matched_set_count"
                ],
                "primary_term": model["primary_term"],
            }
        )
    leave_one_year_out = []
    for year in sorted(primary_frame["year"].unique()):
        subset = primary_frame[primary_frame["year"] != year]
        model = phase3.fit_within_set_lpm(subset, outcome_column="land_change_outcome")
        leave_one_year_out.append(
            {
                "excluded_year": int(year),
                "matched_set_count": model["matched_set_count"],
                "primary_term": model["primary_term"],
            }
        )
    estimates = [item["primary_term"]["estimate"] for item in by_year]
    leave_out_estimates = [item["primary_term"]["estimate"] for item in leave_one_year_out]
    return {
        "year_specific": by_year,
        "year_specific_estimate_range": [min(estimates), max(estimates)],
        "leave_one_year_out": leave_one_year_out,
        "leave_one_year_out_estimate_range": [min(leave_out_estimates), max(leave_out_estimates)],
    }


def spatial_cluster_sensitivities(primary_frame: pd.DataFrame) -> list[dict[str, Any]]:
    coordinates = pd.read_csv(phase3.PRIVATE_CELL_PATH, usecols=["cell_id", "grid_row", "grid_col"])
    frame = primary_frame.merge(coordinates, on="cell_id", how="left", validate="many_to_one")
    if frame[["grid_row", "grid_col"]].isna().any().any():
        raise ValueError("Spatial-cluster sensitivity is missing private grid coordinates")
    work, x_within, beta, residual, bread = _within_design(frame, "land_change_outcome")
    results = []
    for kilometres in (25, 50, 100):
        blocks = (
            (frame["grid_row"].astype(int) // kilometres).astype(str)
            + ":"
            + (frame["grid_col"].astype(int) // kilometres).astype(str)
        )
        block_meat, block_clusters = phase3._cluster_meat(x_within, residual, blocks)
        date_meat, date_clusters = phase3._cluster_meat(x_within, residual, work["date"])
        intersection = blocks + "|" + work["date"].astype(str)
        intersection_meat, intersection_clusters = phase3._cluster_meat(
            x_within, residual, intersection
        )
        covariance = bread @ (block_meat + date_meat - intersection_meat) @ bread
        covariance = (covariance + covariance.T) / 2
        diagonal = np.diag(covariance)
        if not np.isfinite(diagonal).all() or (diagonal <= 0).any():
            raise ValueError(f"Invalid {kilometres}-km block/date covariance")
        standard_error = float(math.sqrt(diagonal[0]))
        estimate = float(beta[0])
        results.append(
            {
                "block_size_km": kilometres,
                "spatial_block_count": block_clusters,
                "date_cluster_count": date_clusters,
                "block_date_cluster_count": intersection_clusters,
                "estimate": estimate,
                "standard_error": standard_error,
                "ci95": [estimate - 1.96 * standard_error, estimate + 1.96 * standard_error],
                "p_two_sided": float(2 * norm.sf(abs(estimate / standard_error))),
                "coordinates_released": False,
            }
        )
    return results


def pre_exposure_negative_control(
    opportunities: pd.DataFrame,
    transitions: pd.DataFrame,
    registration: dict[str, Any],
) -> dict[str, Any]:
    """Use the registered t-2 one-year pair as a fully pre-index outcome.

    For an event in year t, the t-2/h1 field spans maps t-3 to t-1 and
    therefore ends before the index fire year. Event years begin at 2017 so
    every requested source field exists.
    """

    shifted = opportunities[opportunities["year"].between(2017, 2023)].copy()
    shifted["original_event_year"] = shifted["year"]
    shifted["year"] = shifted["year"] - 2
    frame, flow = phase3.build_horizon_frame(
        shifted,
        transitions,
        registration,
        horizon=1,
        threshold=0.10,
    )
    frame["year"] = frame["original_event_year"]
    model = phase3.fit_within_set_lpm(frame, outcome_column="land_change_outcome")
    post_frame, _ = phase3.build_horizon_frame(
        opportunities,
        transitions,
        registration,
        horizon=1,
        threshold=0.10,
    )
    post_frame = post_frame[post_frame["year"].between(2017, 2023)].copy()
    common = post_frame.merge(
        frame[["opportunity_id", "land_change_outcome", "transition_share_preforest"]],
        on="opportunity_id",
        how="inner",
        validate="one_to_one",
        suffixes=("_post", "_pre"),
    )
    complete_sizes = common.groupby("matched_set_id", sort=False).size()
    complete_sets = set(complete_sizes[complete_sizes == 5].index.astype(str))
    common = common[common["matched_set_id"].astype(str).isin(complete_sets)].copy()
    common["binary_post_minus_pre"] = (
        common["land_change_outcome_post"] - common["land_change_outcome_pre"]
    )
    common["continuous_post_minus_pre"] = (
        common["transition_share_preforest_post"]
        - common["transition_share_preforest_pre"]
    )
    binary_change = phase3.fit_within_set_lpm(
        common, outcome_column="binary_post_minus_pre"
    )
    continuous_change = phase3.fit_within_set_lpm(
        common, outcome_column="continuous_post_minus_pre"
    )
    binary_change["model"] = "within-matched-set post-minus-pre binary-outcome contrast"
    continuous_change["model"] = "within-matched-set post-minus-pre continuous-loss-share contrast"
    return {
        "status": "estimated_post_registration_diagnostic",
        "definition": "At least 10% natural-forest loss in a map interval ending before the index fire year (t-3 to t-1).",
        "flow": flow,
        "model": model,
        "common_support_post_minus_pre": {
            "matched_set_count": int(common["matched_set_id"].nunique()),
            "row_count": int(len(common)),
            "binary_outcome_model": binary_change,
            "continuous_loss_share_model": continuous_change,
            "interpretation_rule": "This post-minus-pre contrast asks whether the later association exceeds the pre-existing difference on common support. It is a diagnostic difference-in-differences form, not a causal estimator because parallel trends are not established.",
        },
        "interpretation_rule": "A positive association suggests pre-existing conversion trajectory or residual confounding; it does not negate temporal ordering of the primary outcome but weakens causal interpretations.",
    }


def transition_mass_audit(
    transitions: pd.DataFrame, registration: dict[str, Any]
) -> dict[str, Any]:
    residuals = []
    pair_count = 0
    for horizon_text, years in registration["time_alignment"]["eligible_event_years_by_horizon"].items():
        horizon = int(horizon_text)
        for year in years:
            loss = pd.to_numeric(
                transitions[f"loss_fraction_cell_{year}_h{horizon}"], errors="coerce"
            ).to_numpy(dtype=float)
            destinations = np.zeros(len(transitions), dtype=float)
            for destination in phase3.DESTINATIONS:
                destinations += pd.to_numeric(
                    transitions[f"to_{destination}_fraction_cell_{year}_h{horizon}"],
                    errors="coerce",
                ).to_numpy(dtype=float)
            residuals.append(loss - destinations)
            pair_count += 1
    values = np.concatenate(residuals)
    absolute = np.abs(values)
    return {
        "annual_horizon_pair_count": pair_count,
        "cell_pair_count": int(len(values)),
        "maximum_absolute_loss_minus_destination_mass": float(absolute.max()),
        "p99_absolute_loss_minus_destination_mass": float(np.quantile(absolute, 0.99)),
        "count_above_1e_8": int((absolute > 1e-8).sum()),
        "status": "passed_internal_mass_balance" if not (absolute > 1e-8).any() else "failed_internal_mass_balance",
        "external_ground_truth_limit": "This checks internal transition accounting only; it is not independent validation of MapBiomas classification accuracy.",
    }


def _effect_rows(registered_result: dict[str, Any]) -> list[dict[str, Any]]:
    models = registered_result["models"]
    sources = [
        ("Primary: ≥10%, 1 year", models["primary"]),
        ("≥5%, 1 year", models["threshold_sensitivities"][0]),
        ("≥20%, 1 year", models["threshold_sensitivities"][1]),
        ("≥10%, 2 years", models["horizon_sensitivities"][0]),
        ("≥10%, 3 years", models["horizon_sensitivities"][1]),
    ]
    rows = []
    for label, item in sources:
        term = item["model"]["primary_term"]
        rows.append(
            {
                "analysis": label,
                "matched_sets": item["model"]["matched_set_count"],
                "adjusted_risk_difference_pp": term["estimate"] * 100,
                "ci95_low_pp": term["ci95"][0] * 100,
                "ci95_high_pp": term["ci95"][1] * 100,
                "p_two_sided": term["p_two_sided"],
            }
        )
    return rows


def write_tables(registered_result: dict[str, Any], robustness: dict[str, Any]) -> None:
    TABLE_ROOT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(_effect_rows(registered_result)).to_csv(
        TABLE_ROOT / "table1_primary_and_registered_sensitivities.csv", index=False
    )
    destination_rows = []
    for item in registered_result["models"]["destination_models"]:
        row = {
            "destination": item["destination"],
            "status": item["status"],
            "variation_matched_sets": item.get("outcome_variation_matched_set_count"),
        }
        if item["status"] == "estimated":
            term = item["model"]["primary_term"]
            row.update(
                {
                    "matched_sets": item["model"]["matched_set_count"],
                    "adjusted_risk_difference_pp": term["estimate"] * 100,
                    "ci95_low_pp": term["ci95"][0] * 100,
                    "ci95_high_pp": term["ci95"][1] * 100,
                    "p_two_sided": term["p_two_sided"],
                    "p_holm": term["p_holm_destination_family"],
                }
            )
        destination_rows.append(row)
    pd.DataFrame(destination_rows).to_csv(
        TABLE_ROOT / "table2_exploratory_destinations.csv", index=False
    )
    pd.DataFrame(robustness["attrition"]["case_covariate_comparisons"]).to_csv(
        TABLE_ROOT / "table_s1_included_vs_excluded.csv", index=False
    )
    year_rows = []
    for item in robustness["temporal"]["year_specific"]:
        term = item["primary_term"]
        year_rows.append(
            {
                "year": item["year"],
                "matched_sets": item["matched_set_count"],
                "variation_sets": item["outcome_variation_matched_set_count"],
                "adjusted_risk_difference_pp": term["estimate"] * 100,
                "ci95_low_pp": term["ci95"][0] * 100,
                "ci95_high_pp": term["ci95"][1] * 100,
                "p_two_sided": term["p_two_sided"],
            }
        )
    pd.DataFrame(year_rows).to_csv(TABLE_ROOT / "table_s2_year_specific.csv", index=False)


def _save_figure(fig: plt.Figure, stem: str) -> None:
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE_ROOT / f"{stem}.png", dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(FIGURE_ROOT / f"{stem}.svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def write_figures(registered_result: dict[str, Any], robustness: dict[str, Any]) -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.titleweight": "bold",
        }
    )
    effect = pd.DataFrame(_effect_rows(registered_result)).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    y = np.arange(len(effect))
    x = effect["adjusted_risk_difference_pp"].to_numpy()
    low = effect["ci95_low_pp"].to_numpy()
    high = effect["ci95_high_pp"].to_numpy()
    ax.errorbar(x, y, xerr=[x - low, high - x], fmt="o", color="#9b4f1d", ecolor="#36584a", capsize=3)
    ax.axvline(0, color="#4d4d4d", linewidth=0.8)
    ax.set_yticks(y, effect["analysis"])
    ax.set_xlabel("Adjusted risk difference (percentage points)")
    ax.set_title("Registered threshold and follow-up sensitivities")
    ax.grid(axis="x", color="#dddddd", linewidth=0.6)
    _save_figure(fig, "figure2_registered_sensitivities")

    destinations = []
    for item in registered_result["models"]["destination_models"]:
        if item["status"] != "estimated":
            continue
        term = item["model"]["primary_term"]
        destinations.append(
            {
                "label": item["destination"].replace("_", " ").title(),
                "estimate": term["estimate"] * 100,
                "low": term["ci95"][0] * 100,
                "high": term["ci95"][1] * 100,
            }
        )
    destination = pd.DataFrame(destinations).sort_values("estimate")
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    y = np.arange(len(destination))
    x = destination["estimate"].to_numpy()
    low = destination["low"].to_numpy()
    high = destination["high"].to_numpy()
    ax.errorbar(x, y, xerr=[x - low, high - x], fmt="o", color="#9b4f1d", ecolor="#36584a", capsize=3)
    ax.axvline(0, color="#4d4d4d", linewidth=0.8)
    ax.set_yticks(y, destination["label"])
    ax.set_xlabel("Adjusted risk difference (percentage points)")
    ax.set_title("Exploratory one-year destination associations")
    ax.grid(axis="x", color="#dddddd", linewidth=0.6)
    _save_figure(fig, "figure3_exploratory_destinations")

    years = robustness["temporal"]["year_specific"]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    labels = [str(item["year"]) for item in years]
    x = np.array([item["primary_term"]["estimate"] * 100 for item in years])
    low = np.array([item["primary_term"]["ci95"][0] * 100 for item in years])
    high = np.array([item["primary_term"]["ci95"][1] * 100 for item in years])
    y = np.arange(len(years))[::-1]
    ax.errorbar(x, y, xerr=[x - low, high - x], fmt="o", color="#9b4f1d", ecolor="#36584a", capsize=3)
    ax.axvline(0, color="#4d4d4d", linewidth=0.8)
    ax.set_yticks(y, labels)
    ax.set_xlabel("Adjusted risk difference (percentage points)")
    ax.set_ylabel("Index-fire year")
    ax.set_title("Year-specific Phase 3 estimates")
    ax.grid(axis="x", color="#dddddd", linewidth=0.6)
    _save_figure(fig, "figure4_year_specific_estimates")

    attrition = robustness["attrition"]
    values = [
        registered_result["opportunity_inventory"]["matched_set_count"],
        attrition["candidate_matched_set_count"],
        attrition["included_matched_set_count"],
    ]
    labels = ["Locked exact 1:4 sets", "Eligible event years 2015–2023", "Complete forest/support sets"]
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    bars = ax.barh(np.arange(3)[::-1], values, color=["#36584a", "#6f806f", "#9b4f1d"])
    ax.set_yticks(np.arange(3)[::-1], labels)
    ax.set_xlabel("Matched sets")
    ax.set_title("Phase 3 analytical selection flow")
    ax.bar_label(bars, labels=[f"{value:,}" for value in values], padding=4)
    ax.set_xlim(0, max(values) * 1.15)
    _save_figure(fig, "figure1_selection_flow")


def update_browser_summary(robustness: dict[str, Any]) -> None:
    """Expose only compact, coordinate-free publication diagnostics to the UI."""

    browser = phase3.read_json(BROWSER_PATH)
    negative = robustness["negative_control"]
    browser["publication_robustness"] = {
        "status": "complete",
        "attrition": {
            "candidate_matched_set_count": robustness["attrition"][
                "candidate_matched_set_count"
            ],
            "included_matched_set_count": robustness["attrition"][
                "included_matched_set_count"
            ],
            "excluded_share": robustness["attrition"]["excluded_share"],
            "maximum_absolute_standardized_mean_difference": robustness["attrition"][
                "maximum_absolute_standardized_mean_difference"
            ],
        },
        "negative_control": {
            "matched_set_count": negative["model"]["matched_set_count"],
            "estimate": negative["model"]["primary_term"]["estimate"],
            "ci95": negative["model"]["primary_term"]["ci95"],
            "p_two_sided": negative["model"]["primary_term"]["p_two_sided"],
        },
        "common_support_post_minus_pre": {
            "matched_set_count": negative["common_support_post_minus_pre"][
                "matched_set_count"
            ],
            "estimate": negative["common_support_post_minus_pre"][
                "binary_outcome_model"
            ]["primary_term"]["estimate"],
            "ci95": negative["common_support_post_minus_pre"][
                "binary_outcome_model"
            ]["primary_term"]["ci95"],
            "p_two_sided": negative["common_support_post_minus_pre"][
                "binary_outcome_model"
            ]["primary_term"]["p_two_sided"],
        },
        "interpretation": "The positive pre-exposure contrast indicates residual baseline trajectory or confounding. The primary result remains a temporal association and must not be presented as causal.",
    }
    BROWSER_PATH.write_text(json.dumps(browser, indent=2) + "\n", encoding="utf-8")


def render_report(registered_result: dict[str, Any], robustness: dict[str, Any]) -> str:
    primary = registered_result["models"]["primary"]["model"]["primary_term"]
    attrition = robustness["attrition"]
    conditional = robustness["alternative_estimators"]["conditional_logit"]
    continuous = robustness["alternative_estimators"]["continuous_loss_share"]
    placebo = robustness["negative_control"]
    placebo_term = placebo["model"]["primary_term"]
    post_minus_pre = placebo["common_support_post_minus_pre"]["binary_outcome_model"]["primary_term"]
    influence = robustness["influence"]["exclusion_sensitivities"]
    spatial = robustness["spatial_cluster_sensitivities"]
    lines = [
        "# Phase 3 publication robustness audit",
        "",
        f"**Generated:** {robustness['created_at_utc']}",
        "**Scope:** Kalimantan baseline-natural-forest cells only; all analyses are associations.",
        "",
        "## Technical summary",
        "",
        f"The frozen primary estimate remains **{primary['estimate'] * 100:.2f} percentage points** (95% CI {primary['ci95'][0] * 100:.2f} to {primary['ci95'][1] * 100:.2f}). Threshold, horizon, influence-screening, spatial-cluster, and alternative-estimator checks retain a positive fire-to-later-forest-loss association. However, the pre-exposure negative control is also reported below and must constrain causal interpretation.",
        "",
        "## Attrition is material and now quantified",
        "",
        f"Of {attrition['candidate_matched_set_count']:,} temporally eligible sets, {attrition['excluded_matched_set_count']:,} ({attrition['excluded_share'] * 100:.1f}%) failed complete forest/observation support and {attrition['included_matched_set_count']:,} were analyzed. The maximum absolute included-versus-excluded standardized mean difference across audited case-row variables is {attrition['maximum_absolute_standardized_mean_difference']:.3f}. Variables above |0.10|: {', '.join(attrition['variables_above_abs_smd_0_10']) or 'none'}.",
        "",
        "The exclusion percentage is not hidden or treated as missing-at-random proof. Table S1 contains mean, median, and standardized differences, and the machine-readable receipt records non-exclusive exclusion reasons by year.",
        "",
        "## Influence and alternative estimators retain the direction",
        "",
        f"After excluding the top 0.5% and 1% of matched sets by model score norm, adjusted estimates were {influence[0]['primary_term']['estimate'] * 100:.2f} and {influence[1]['primary_term']['estimate'] * 100:.2f} points. Conditional logistic regression produced an odds ratio of {conditional['odds_ratio']:.2f} (model-based 95% CI {conditional['ci95'][0]:.2f}–{conditional['ci95'][1]:.2f}); it is a scale sensitivity, not a replacement for the registered risk difference. The adjusted continuous loss-share difference was {continuous['primary_term']['estimate'] * 100:.2f} points.",
        "",
        "## Coarser spatial clustering does not erase statistical support",
        "",
        "| Spatial cluster | Estimate | 95% CI | p-value |",
        "|---|---:|---:|---:|",
    ]
    for item in spatial:
        lines.append(
            f"| {item['block_size_km']} km block + date | {item['estimate'] * 100:.2f} pp | {item['ci95'][0] * 100:.2f} to {item['ci95'][1] * 100:.2f} pp | {item['p_two_sided']:.3g} |"
        )
    lines.extend(
        [
            "",
            "These sandwich-covariance checks address residual dependence at coarser scales, but they do not remove unmeasured spatial confounding.",
            "",
            "## The pre-exposure negative control limits causal interpretation",
            "",
            f"The diagnostic outcome ending before the index fire produced an adjusted difference of **{placebo_term['estimate'] * 100:.2f} points** (95% CI {placebo_term['ci95'][0] * 100:.2f} to {placebo_term['ci95'][1] * 100:.2f}; p={placebo_term['p_two_sided']:.3g}) across {placebo['model']['matched_set_count']:,} complete sets. A positive result would indicate that fire-positive cells were already on a different land-change trajectory; a null result would reduce, but not eliminate, that concern.",
            "",
            f"On {placebo['common_support_post_minus_pre']['matched_set_count']:,} sets with both intervals observed, the post-minus-pre diagnostic contrast was **{post_minus_pre['estimate'] * 100:.2f} points** (95% CI {post_minus_pre['ci95'][0] * 100:.2f} to {post_minus_pre['ci95'][1] * 100:.2f}; p={post_minus_pre['p_two_sided']:.3g}). This asks whether the later difference exceeds the pre-existing difference, but it is not causal because parallel trends are not established.",
            "",
            "## MapBiomas accounting passes internally, not against ground truth",
            "",
            f"Across {robustness['transition_mass_audit']['cell_pair_count']:,} cell–horizon records, the maximum absolute difference between total forest loss and the sum of registered destination masses was {robustness['transition_mass_audit']['maximum_absolute_loss_minus_destination_mass']:.3g}; {robustness['transition_mass_audit']['count_above_1e_8']:,} exceeded 1e-8. This verifies accounting consistency only. Independent classification-accuracy validation remains a limitation for the manuscript.",
            "",
            "## Publication decision",
            "",
            "The result is suitable for a Kalimantan association manuscript after the negative-control result, attrition comparison, and measurement limitation are carried into the abstract, results, and discussion. It is not suitable for an Indonesia-wide, global, deliberate-burning, actor-attribution, or government-performance claim.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    registered_result = phase3.read_json(phase3.RESULT_PATH)
    if not registered_result.get("phase3_model_run"):
        raise RuntimeError("Run the registered Phase 3 model before publication diagnostics")
    opportunities = phase3.load_opportunities()
    transitions = pd.read_csv(phase3.TRANSITION_SUMMARY_PATH, low_memory=False)
    registration = phase3.read_json(phase3.REGISTRATION_PATH)
    primary_frame, _ = phase3.build_horizon_frame(
        opportunities, transitions, registration, horizon=1, threshold=0.10
    )
    candidate, set_flags = _candidate_primary_frame(opportunities, transitions, registration)
    continuous = phase3.fit_within_set_lpm(
        primary_frame, outcome_column="transition_share_preforest"
    )
    continuous["model"] = "within-matched-set linear model for continuous loss share"
    robustness = {
        "schema_version": "phase3-publication-robustness/v1",
        "created_at_utc": phase3.utc_now(),
        "scope": {
            "geography": "Kalimantan",
            "generalization": "No Indonesia-wide or global inferential claim",
            "claim_type": "post-registration diagnostics and association sensitivities",
        },
        "registered_primary_result_sha256": phase3.sha256_file(phase3.RESULT_PATH),
        "attrition": attrition_audit(candidate, set_flags),
        "influence": influence_audit(primary_frame),
        "alternative_estimators": {
            "conditional_logit": conditional_logit_sensitivity(primary_frame),
            "continuous_loss_share": continuous,
        },
        "temporal": temporal_sensitivities(primary_frame),
        "spatial_cluster_sensitivities": spatial_cluster_sensitivities(primary_frame),
        "negative_control": pre_exposure_negative_control(
            opportunities, transitions, registration
        ),
        "transition_mass_audit": transition_mass_audit(transitions, registration),
        "claim_boundary": registered_result["claim_boundary"],
    }
    robustness = _json_ready(robustness)
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(robustness, indent=2) + "\n", encoding="utf-8")
    write_tables(registered_result, robustness)
    write_figures(registered_result, robustness)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(render_report(registered_result, robustness), encoding="utf-8")
    update_browser_summary(robustness)
    print(
        json.dumps(
            {
                "status": "complete",
                "scope": robustness["scope"]["geography"],
                "excluded_share": robustness["attrition"]["excluded_share"],
                "conditional_logit_or": robustness["alternative_estimators"]["conditional_logit"]["odds_ratio"],
                "negative_control_estimate": robustness["negative_control"]["model"]["primary_term"]["estimate"],
                "figures": len(list(FIGURE_ROOT.glob("*.png"))),
                "tables": len(list(TABLE_ROOT.glob("*.csv"))),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
