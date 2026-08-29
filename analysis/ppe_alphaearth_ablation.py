#!/usr/bin/env python3
"""Run the preregistered prior-year AlphaEarth predictive ablation.

The default development mode performs spatially grouped, recurring-cell-purged
cross-validation on 2018-2022, checks 2023 as a rehearsal, and freezes selected
penalties. ``--locked-test`` can then evaluate 2024-2025 exactly once.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from phase2_environmental import (  # noqa: E402
    apply_standardization,
    build_model_matrix,
    exclude_incomplete_matched_sets,
    fit_standardization,
    load_and_validate_frame,
)
from wildfire_research.alphaearth import ALPHAEARTH_BANDS, normalize_embedding_rows  # noqa: E402
from wildfire_research.matched_prediction import (  # noqa: E402
    assign_spatial_block_folds,
    choose_penalty,
    conditional_ranking_contributions,
    conditional_ranking_metrics,
    fit_ridge_conditional,
    pack_exact_matched_sets,
    purged_fold_sets,
)


REGISTRATION_PATH = ROOT / "config" / "ppe_alphaearth_registration.json"
FEATURE_GATE_PATH = ROOT / "outputs" / "quality" / "ppe_feature_gate.json"
OPPORTUNITY_PATH = ROOT / "data" / "derived" / "viirs" / "opportunity_frame.csv"
EMBEDDING_PATH = (
    ROOT / "data" / "derived" / "ppe" / "alphaearth_prefire_embeddings_private.csv"
)
PRIVATE_CELL_PATH = (
    ROOT / "data" / "derived" / "phase3" / "phase3_cell_centres_private.csv"
)
DEVELOPMENT_PATH = ROOT / "outputs" / "analysis" / "ppe_alphaearth_development.json"
MODEL_LOCK_PATH = ROOT / "outputs" / "locks" / "ppe_alphaearth_model_lock.json"
LOCKED_TEST_PATH = ROOT / "outputs" / "analysis" / "ppe_alphaearth_locked_test.json"
INSIGHT_PATH = ROOT / "outputs" / "insights" / "ppe_alphaearth_predictive_ablation.md"
ALGORITHM_REVISION = "ppe-alphaearth-ridge-conditional-ablation-v1"
FAMILIES = ("explicit", "embedding_only", "combined")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected an object in {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def prepare_frame(registration: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    if read_json(FEATURE_GATE_PATH).get("ready") is not True:
        raise ValueError("PPE feature gate is not ready")
    frame = load_and_validate_frame(OPPORTUNITY_PATH)
    frame, exclusions = exclude_incomplete_matched_sets(frame)
    development_years = registration["validation"]["development_years"]
    stats = fit_standardization(frame, development_years)
    frame = apply_standardization(frame, stats)
    eligible_years = set(registration["temporal_lock"]["eligible_event_years"])
    frame = frame.loc[frame["year"].isin(eligible_years)].copy()

    embeddings = pd.read_csv(
        EMBEDDING_PATH, dtype={"record_id": "string", "cell_id": "string"}
    )
    embeddings = normalize_embedding_rows(embeddings)
    embeddings = embeddings.rename(columns={"event_year": "year"})
    if embeddings.duplicated(["cell_id", "year"]).any():
        raise ValueError("AlphaEarth table contains duplicate cell-year rows")
    merged = frame.merge(
        embeddings[["cell_id", "year", "embedding_year", *ALPHAEARTH_BANDS]],
        on=["cell_id", "year"],
        how="left",
        validate="many_to_one",
        indicator=True,
    )
    incomplete_sets = set(
        merged.loc[
            merged["_merge"].ne("both")
            | merged[list(ALPHAEARTH_BANDS)].isna().any(axis=1),
            "matched_set_id",
        ].astype(str)
    )
    merged = merged.loc[
        ~merged["matched_set_id"].astype(str).isin(incomplete_sets)
    ].drop(columns="_merge")
    if (merged["embedding_year"].astype(int) != merged["year"].astype(int) - 1).any():
        raise ValueError("temporal leakage detected after merging embeddings")

    cells = pd.read_csv(
        PRIVATE_CELL_PATH,
        usecols=["cell_id", "grid_row", "grid_col"],
        dtype={"cell_id": "string"},
    )
    merged = merged.merge(cells, on="cell_id", how="left", validate="many_to_one")
    if merged[["grid_row", "grid_col"]].isna().any().any():
        raise ValueError("model rows lack spatial grid indices")
    merged["spatial_block"] = (
        (merged["grid_row"].astype(int) // 100).astype(str)
        + ":"
        + (merged["grid_col"].astype(int) // 100).astype(str)
    )
    merged = merged.sort_values(
        ["matched_set_id", "outcome"], ascending=[True, False], kind="stable"
    ).reset_index(drop=True)
    sizes = merged.groupby("matched_set_id").size()
    positives = merged.groupby("matched_set_id")["outcome"].sum()
    if not sizes.eq(5).all() or not positives.eq(1).all():
        raise ValueError("prepared ablation frame violates exact 1:4 matched sets")
    audit = {
        "source_row_count": int(len(frame)),
        "retained_row_count": int(len(merged)),
        "retained_matched_set_count": int(merged["matched_set_id"].nunique()),
        "embedding_incomplete_matched_set_count": len(incomplete_sets),
        "phase2_quality_exclusion": exclusions,
        "standardization": stats,
    }
    return merged, audit


def family_matrix(frame: pd.DataFrame, family: str) -> tuple[np.ndarray, list[str]]:
    explicit, explicit_names = build_model_matrix(
        frame, peat_threshold=50, condition="rootzone_dryness_72h_z"
    )
    embedding = frame[list(ALPHAEARTH_BANDS)].to_numpy(float)
    if family == "explicit":
        return explicit, explicit_names
    if family == "embedding_only":
        return embedding, list(ALPHAEARTH_BANDS)
    if family == "combined":
        return np.column_stack([explicit, embedding]), [
            *explicit_names,
            *ALPHAEARTH_BANDS,
        ]
    raise ValueError(f"unknown model family: {family}")


def subset_grouped(
    frame: pd.DataFrame, family: str, set_ids: set[str]
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    subset = frame.loc[frame["matched_set_id"].astype(str).isin(set_ids)].copy()
    matrix, _ = family_matrix(subset, family)
    return pack_exact_matched_sets(subset, matrix)


def cross_validate_family(
    development: pd.DataFrame,
    family: str,
    penalties: list[float],
    folds: int,
) -> dict[str, Any]:
    assignments = assign_spatial_block_folds(development, folds=folds)
    rows = []
    for penalty in penalties:
        fold_rows = []
        for fold in range(folds):
            train_sets, test_sets, purge = purged_fold_sets(
                development, assignments, fold
            )
            x_train, y_train, _ = subset_grouped(development, family, train_sets)
            x_test, y_test, _ = subset_grouped(development, family, test_sets)
            fit = fit_ridge_conditional(x_train, y_train, penalty)
            metrics = conditional_ranking_metrics(x_test, y_test, fit.coefficients)
            fold_rows.append(
                {
                    "fold": fold,
                    "penalty": penalty,
                    **purge,
                    **metrics,
                    "coefficient_l2_norm": float(np.linalg.norm(fit.coefficients)),
                    "iterations": fit.iterations,
                }
            )
        losses = np.asarray([row["conditional_log_loss"] for row in fold_rows])
        rows.append(
            {
                "penalty": penalty,
                "mean_conditional_log_loss": float(losses.mean()),
                "sd_conditional_log_loss_across_folds": float(losses.std(ddof=1)),
                "folds": fold_rows,
            }
        )
    selected = choose_penalty(rows)
    return {
        "family": family,
        "selected_penalty": selected,
        "penalty_results": rows,
        "spatial_block_count": int(development["spatial_block"].nunique()),
        "fold_assignment_rule": "positive-cell 100-km block, balanced deterministically; training sets sharing any test cell are purged",
    }


def fit_and_evaluate(
    training: pd.DataFrame,
    evaluation: pd.DataFrame,
    family: str,
    penalty: float,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    train_matrix, names = family_matrix(training, family)
    x_train, y_train, _ = pack_exact_matched_sets(training, train_matrix)
    fit = fit_ridge_conditional(x_train, y_train, penalty)
    eval_matrix, _ = family_matrix(evaluation, family)
    x_eval, y_eval, _ = pack_exact_matched_sets(evaluation, eval_matrix)
    metrics = conditional_ranking_metrics(x_eval, y_eval, fit.coefficients)
    result = {
        "family": family,
        "penalty": penalty,
        "feature_count": len(names),
        "training_matched_set_count": int(len(x_train)),
        "evaluation": metrics,
        "overfit_diagnostics": {
            "p_over_training_sets": float(len(names) / len(x_train)),
            "coefficient_l2_norm": float(np.linalg.norm(fit.coefficients)),
            "iterations": fit.iterations,
            "gradient_max_abs": fit.gradient_max_abs,
        },
    }
    return result, fit.coefficients, y_eval


def provenance() -> dict[str, Any]:
    paths = {
        "registration": REGISTRATION_PATH,
        "feature_gate": FEATURE_GATE_PATH,
        "opportunity_frame": OPPORTUNITY_PATH,
        "alphaearth_embeddings": EMBEDDING_PATH,
        "private_cell_index": PRIVATE_CELL_PATH,
    }
    return {
        name: {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)}
        for name, path in paths.items()
    }


def run_development(registration: dict[str, Any], frame: pd.DataFrame, audit: dict[str, Any]) -> int:
    validation = registration["validation"]
    development = frame.loc[frame["year"].isin(validation["development_years"])].copy()
    rehearsal = frame.loc[frame["year"].isin(validation["rehearsal_years"])].copy()
    penalties = [float(value) for value in registration["models"]["penalty_grid"]]
    cv = {
        family: cross_validate_family(
            development,
            family,
            [0.0] if family == "explicit" else penalties,
            int(validation["development_folds"]),
        )
        for family in FAMILIES
    }
    rehearsal_results = {}
    for family in FAMILIES:
        result, _, _ = fit_and_evaluate(
            development, rehearsal, family, float(cv[family]["selected_penalty"])
        )
        rehearsal_results[family] = result
    if not all(
        math.isfinite(result["evaluation"]["conditional_log_loss"])
        for result in rehearsal_results.values()
    ):
        raise RuntimeError("rehearsal produced a non-finite metric")

    result = {
        "schema_version": "ppe-alphaearth-development/v1",
        "algorithm_revision": ALGORITHM_REVISION,
        "created_at_utc": utc_now(),
        "status": "development_complete_locked_test_not_accessed",
        "claim_boundary": registration["claim_boundary"],
        "data_audit": audit,
        "cross_validation": cv,
        "rehearsal_2023": rehearsal_results,
        "locked_test_accessed": False,
        "provenance": provenance(),
    }
    write_json_atomic(DEVELOPMENT_PATH, result)
    lock = {
        "schema_version": "ppe-alphaearth-model-lock/v1",
        "algorithm_revision": ALGORITHM_REVISION,
        "frozen_at_utc": utc_now(),
        "status": "frozen_before_locked_test",
        "development_result_sha256": sha256_file(DEVELOPMENT_PATH),
        "selected_penalties": {
            family: float(cv[family]["selected_penalty"]) for family in FAMILIES
        },
        "final_training_years": [
            *validation["development_years"],
            *validation["rehearsal_years"],
        ],
        "locked_test_years": validation["locked_test_years"],
        "provenance": result["provenance"],
        "locked_test_accessed": False,
    }
    write_json_atomic(MODEL_LOCK_PATH, lock)
    print(json.dumps({"status": result["status"], "selected_penalties": lock["selected_penalties"]}, indent=2))
    return 0


def verify_lock(lock: dict[str, Any]) -> None:
    if lock.get("status") != "frozen_before_locked_test" or lock.get("locked_test_accessed") is not False:
        raise ValueError("model lock is not eligible for first locked-test access")
    if lock.get("algorithm_revision") != ALGORITHM_REVISION:
        raise ValueError("model lock algorithm revision changed")
    if lock.get("development_result_sha256") != sha256_file(DEVELOPMENT_PATH):
        raise ValueError("development result changed after model lock")
    current = provenance()
    for key, recorded in lock["provenance"].items():
        if current[key]["sha256"] != recorded["sha256"]:
            raise ValueError(f"locked input changed: {key}")


def bootstrap_improvement(
    baseline: np.ndarray,
    candidate: np.ndarray,
    replicates: int,
) -> dict[str, Any]:
    if baseline.shape != candidate.shape:
        raise ValueError("bootstrap contribution arrays differ")
    rng = np.random.default_rng(20260829)
    n = len(baseline)
    values = np.empty(replicates, dtype=float)
    for index in range(replicates):
        sample = rng.integers(0, n, size=n)
        values[index] = float((baseline[sample] - candidate[sample]).mean())
    observed = float((baseline - candidate).mean())
    return {
        "definition": "positive means lower conditional log loss than explicit covariates",
        "observed_improvement": observed,
        "ci95_percentile": [float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))],
        "replicates": replicates,
        "seed": 20260829,
    }


def run_locked_test(registration: dict[str, Any], frame: pd.DataFrame, audit: dict[str, Any]) -> int:
    if LOCKED_TEST_PATH.exists():
        raise FileExistsError(
            "locked-test output already exists; refusing a second evaluation"
        )
    lock = read_json(MODEL_LOCK_PATH)
    verify_lock(lock)
    training = frame.loc[frame["year"].isin(lock["final_training_years"])].copy()
    evaluation = frame.loc[frame["year"].isin(lock["locked_test_years"])].copy()
    model_results: dict[str, Any] = {}
    contributions: dict[str, dict[str, np.ndarray]] = {}
    for family in FAMILIES:
        result, beta, _ = fit_and_evaluate(
            training, evaluation, family, float(lock["selected_penalties"][family])
        )
        matrix, _ = family_matrix(evaluation, family)
        x_eval, y_eval, _ = pack_exact_matched_sets(evaluation, matrix)
        contributions[family] = conditional_ranking_contributions(x_eval, y_eval, beta)
        model_results[family] = result
    replicates = int(registration["validation"]["bootstrap_replicates"])
    comparisons = {
        family: bootstrap_improvement(
            contributions["explicit"]["log_loss"],
            contributions[family]["log_loss"],
            replicates,
        )
        for family in ("embedding_only", "combined")
    }
    result = {
        "schema_version": "ppe-alphaearth-locked-test/v1",
        "algorithm_revision": ALGORITHM_REVISION,
        "created_at_utc": utc_now(),
        "status": "locked_test_complete",
        "claim_boundary": registration["claim_boundary"],
        "data_audit": audit,
        "models": model_results,
        "conditional_log_loss_improvement_vs_explicit": comparisons,
        "interpretation": "Predictive ablation only; no causal conclusion is licensed by this result.",
        "provenance": provenance(),
        "model_lock_sha256_before_access": sha256_file(MODEL_LOCK_PATH),
    }
    write_json_atomic(LOCKED_TEST_PATH, result)
    lock["locked_test_accessed"] = True
    lock["locked_test_accessed_at_utc"] = utc_now()
    lock["locked_test_result_sha256"] = sha256_file(LOCKED_TEST_PATH)
    lock["status"] = "locked_test_accessed_once"
    write_json_atomic(MODEL_LOCK_PATH, lock)
    write_insight(result)
    print(json.dumps({"status": result["status"], "comparisons": comparisons}, indent=2))
    return 0


def write_insight(result: dict[str, Any]) -> None:
    models = result["models"]
    combined = result["conditional_log_loss_improvement_vs_explicit"]["combined"]
    ci = combined["ci95_percentile"]
    lines = [
        "# Prior-year AlphaEarth predictive ablation",
        "",
        "This is an out-of-time prediction robustness test, not a causal test.",
        "",
        "| Model | Conditional log loss | Top-1 recall | Mean reciprocal rank |",
        "|---|---:|---:|---:|",
    ]
    for family in FAMILIES:
        metrics = models[family]["evaluation"]
        lines.append(
            f"| {family.replace('_', ' ')} | {metrics['conditional_log_loss']:.4f} | "
            f"{metrics['top1_recall_tie_fractional']:.3f} | {metrics['mean_reciprocal_rank']:.3f} |"
        )
    lines.extend(
        [
            "",
            f"Combined-minus-explicit improvement (positive is better): **{combined['observed_improvement']:.4f}** "
            f"(matched-set bootstrap 95% interval {ci[0]:.4f} to {ci[1]:.4f}).",
            "",
            "The embedding always comes from the calendar year before the fire opportunity. Same-year and post-fire features were rejected by the automated leakage gate.",
            "",
            "This comparison cannot identify deliberate burning, plantation expansion, government performance, or any other causal mechanism.",
        ]
    )
    INSIGHT_PATH.parent.mkdir(parents=True, exist_ok=True)
    INSIGHT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--locked-test", action="store_true")
    args = parser.parse_args()
    registration = read_json(REGISTRATION_PATH)
    frame, audit = prepare_frame(registration)
    if args.locked_test:
        return run_locked_test(registration, frame, audit)
    return run_development(registration, frame, audit)


if __name__ == "__main__":
    raise SystemExit(main())
