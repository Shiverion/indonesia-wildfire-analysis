"""Conservative prediction helpers for exact one-case matched sets."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import logsumexp


@dataclass(frozen=True)
class RidgeConditionalFit:
    coefficients: np.ndarray
    penalty: float
    converged: bool
    iterations: int
    objective: float
    gradient_max_abs: float


def pack_exact_matched_sets(
    frame: pd.DataFrame,
    matrix: np.ndarray,
    *,
    set_column: str = "matched_set_id",
    outcome_column: str = "outcome",
    expected_size: int = 5,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Pack rows into exact matched sets without relying on input row order."""

    if len(frame) != len(matrix):
        raise ValueError("frame and matrix row counts differ")
    if not {set_column, outcome_column}.issubset(frame):
        raise ValueError("frame is missing matched-set identifiers or outcomes")
    working = frame[[set_column, outcome_column]].copy()
    working["_row"] = np.arange(len(working))
    groups = list(working.groupby(set_column, sort=True))
    if not groups:
        raise ValueError("no matched sets are available")
    x_groups: list[np.ndarray] = []
    y_groups: list[np.ndarray] = []
    set_ids: list[str] = []
    for set_id, group in groups:
        if len(group) != expected_size or int(group[outcome_column].sum()) != 1:
            raise ValueError(
                f"matched set {set_id!r} must have {expected_size} rows and one case"
            )
        rows = group["_row"].to_numpy(int)
        x_groups.append(np.asarray(matrix[rows], dtype=float))
        y_groups.append(group[outcome_column].to_numpy(float))
        set_ids.append(str(set_id))
    x = np.stack(x_groups)
    y = np.stack(y_groups)
    if not np.isfinite(x).all():
        raise ValueError("model matrix contains missing or non-finite values")
    return x, y, np.asarray(set_ids, dtype=str)


def ridge_conditional_objective(
    beta: np.ndarray,
    x_grouped: np.ndarray,
    y_grouped: np.ndarray,
    penalty: float,
) -> tuple[float, np.ndarray]:
    if penalty < 0:
        raise ValueError("penalty must be non-negative")
    eta = np.einsum("ngp,p->ng", x_grouped, beta)
    log_denom = logsumexp(eta, axis=1)
    case_eta = np.sum(eta * y_grouped, axis=1)
    probabilities = np.exp(eta - log_denom[:, None])
    negative_log_likelihood = float(-(case_eta - log_denom).sum())
    gradient = -np.sum(
        np.einsum("ng,ngp->np", y_grouped - probabilities, x_grouped), axis=0
    )
    objective = negative_log_likelihood + 0.5 * penalty * float(beta @ beta)
    return objective, gradient + penalty * beta


def fit_ridge_conditional(
    x_grouped: np.ndarray,
    y_grouped: np.ndarray,
    penalty: float,
) -> RidgeConditionalFit:
    """Fit an L2-regularized conditional scoring model."""

    if x_grouped.ndim != 3 or y_grouped.shape != x_grouped.shape[:2]:
        raise ValueError("invalid grouped matrix/outcome dimensions")
    result = minimize(
        ridge_conditional_objective,
        np.zeros(x_grouped.shape[2], dtype=float),
        args=(x_grouped, y_grouped, float(penalty)),
        jac=True,
        method="L-BFGS-B",
        options={"maxiter": 1500, "ftol": 1e-12, "gtol": 1e-7},
    )
    beta = np.asarray(result.x, dtype=float)
    objective, gradient = ridge_conditional_objective(
        beta, x_grouped, y_grouped, float(penalty)
    )
    gradient_max = float(np.max(np.abs(gradient)))
    converged = bool(result.success or gradient_max < 1e-5)
    total_iterations = int(result.nit)
    if not converged:
        # This is a numerical fallback to the same registered objective, not a
        # change in features, penalty, split, or estimand. It is especially
        # useful for an unpenalized fold with near-separation.
        fallback = minimize(
            ridge_conditional_objective,
            beta,
            args=(x_grouped, y_grouped, float(penalty)),
            jac=True,
            method="BFGS",
            options={"maxiter": 3000, "gtol": 1e-6},
        )
        beta = np.asarray(fallback.x, dtype=float)
        objective, gradient = ridge_conditional_objective(
            beta, x_grouped, y_grouped, float(penalty)
        )
        gradient_max = float(np.max(np.abs(gradient)))
        converged = bool(fallback.success or gradient_max < 1e-5)
        total_iterations += int(fallback.nit)
        result = fallback
    if not converged:
        raise RuntimeError(
            f"ridge conditional fit failed: {result.message}; max gradient={gradient_max:.3g}"
        )
    return RidgeConditionalFit(
        coefficients=beta,
        penalty=float(penalty),
        converged=converged,
        iterations=total_iterations,
        objective=float(objective),
        gradient_max_abs=gradient_max,
    )


def conditional_ranking_metrics(
    x_grouped: np.ndarray,
    y_grouped: np.ndarray,
    beta: np.ndarray,
) -> dict[str, float | int]:
    contributions = conditional_ranking_contributions(x_grouped, y_grouped, beta)
    return {
        "matched_set_count": int(len(contributions["log_loss"])),
        "conditional_log_loss": float(contributions["log_loss"].mean()),
        "top1_recall_tie_fractional": float(contributions["top1_credit"].mean()),
        "mean_reciprocal_rank": float(
            contributions["reciprocal_rank"].mean()
        ),
    }


def conditional_ranking_contributions(
    x_grouped: np.ndarray,
    y_grouped: np.ndarray,
    beta: np.ndarray,
) -> dict[str, np.ndarray]:
    """Return per-matched-set metric contributions for clustered bootstrap."""

    eta = np.einsum("ngp,p->ng", x_grouped, beta)
    probabilities = np.exp(eta - logsumexp(eta, axis=1)[:, None])
    case_index = y_grouped.argmax(axis=1)
    case_probability = probabilities[np.arange(len(probabilities)), case_index]
    case_score = eta[np.arange(len(eta)), case_index]
    greater = (eta > case_score[:, None] + 1e-12).sum(axis=1)
    tied = (np.abs(eta - case_score[:, None]) <= 1e-12).sum(axis=1)
    top1_credit = np.where(greater == 0, 1.0 / tied, 0.0)
    average_rank = 1.0 + greater + (tied - 1) / 2.0
    return {
        "log_loss": -np.log(np.clip(case_probability, 1e-15, 1.0)),
        "top1_credit": top1_credit,
        "reciprocal_rank": 1.0 / average_rank,
    }


def assign_spatial_block_folds(
    frame: pd.DataFrame,
    *,
    folds: int,
    set_column: str = "matched_set_id",
    outcome_column: str = "outcome",
    block_column: str = "spatial_block",
) -> pd.DataFrame:
    """Assign positive-cell 100-km blocks to size-balanced deterministic folds."""

    if folds < 2:
        raise ValueError("folds must be at least two")
    cases = frame.loc[frame[outcome_column].eq(1), [set_column, block_column]].copy()
    if cases[set_column].duplicated().any():
        raise ValueError("each matched set must have exactly one positive row")
    counts = (
        cases.groupby(block_column, sort=True)
        .size()
        .rename("matched_set_count")
        .reset_index()
        .sort_values(["matched_set_count", block_column], ascending=[False, True])
    )
    if len(counts) < folds:
        raise ValueError("fewer spatial blocks than requested folds")
    loads = [0] * folds
    block_to_fold: dict[str, int] = {}
    for row in counts.itertuples(index=False):
        fold = min(range(folds), key=lambda value: (loads[value], value))
        block_to_fold[str(getattr(row, block_column))] = fold
        loads[fold] += int(row.matched_set_count)
    cases["fold"] = cases[block_column].astype(str).map(block_to_fold).astype(int)
    return cases.rename(columns={block_column: "case_spatial_block"}).reset_index(drop=True)


def purged_fold_sets(
    frame: pd.DataFrame,
    assignments: pd.DataFrame,
    fold: int,
    *,
    set_column: str = "matched_set_id",
    cell_column: str = "cell_id",
) -> tuple[set[str], set[str], dict[str, int]]:
    """Return train/test sets after removing every train set sharing a test cell."""

    mapping = assignments.set_index(set_column)["fold"]
    test_sets = set(mapping.index[mapping.eq(fold)].astype(str))
    candidate_train = set(mapping.index[~mapping.eq(fold)].astype(str))
    if not test_sets or not candidate_train:
        raise ValueError(f"fold {fold} has no test or candidate training sets")
    set_values = frame[set_column].astype(str)
    test_cells = set(frame.loc[set_values.isin(test_sets), cell_column].astype(str))
    shared_train_sets = set(
        frame.loc[
            set_values.isin(candidate_train)
            & frame[cell_column].astype(str).isin(test_cells),
            set_column,
        ].astype(str)
    )
    train_sets = candidate_train - shared_train_sets
    train_cells = set(frame.loc[set_values.isin(train_sets), cell_column].astype(str))
    if train_cells & test_cells:
        raise RuntimeError("spatial fold purge failed to separate recurring cells")
    return train_sets, test_sets, {
        "candidate_training_set_count": len(candidate_train),
        "purged_training_set_count": len(shared_train_sets),
        "retained_training_set_count": len(train_sets),
        "test_set_count": len(test_sets),
        "test_cell_count": len(test_cells),
    }


def choose_penalty(
    rows: Iterable[dict[str, float]],
    *,
    metric: str = "mean_conditional_log_loss",
) -> float:
    """Choose minimum loss; exact ties select the larger (more conservative) penalty."""

    values = list(rows)
    if not values:
        raise ValueError("penalty results must not be empty")
    best = min(values, key=lambda row: (float(row[metric]), -float(row["penalty"])))
    return float(best["penalty"])
