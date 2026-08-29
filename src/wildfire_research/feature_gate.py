"""Fail-closed feature eligibility checks for predictive wildfire extensions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


REQUIRED_FIELDS = {
    "name",
    "required",
    "source_family",
    "provenance_url",
    "license",
    "temporal_relation",
    "available_before_prediction_cutoff",
    "minimum_lag_years",
    "mathematical_component_of_target",
    "shared_data_generation_with_target",
    "causal_position",
    "allowed_tasks",
    "priority_scores",
}


@dataclass(frozen=True)
class FeatureDecision:
    """Auditable decision for one candidate feature family."""

    name: str
    decision: str
    priority_score: float
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["reasons"] = list(self.reasons)
        return result


def weighted_priority_score(
    scores: Mapping[str, Any], weights: Mapping[str, Any]
) -> float:
    """Return a 0-100 weighted score, failing closed on malformed inputs."""

    if not weights:
        raise ValueError("priority_weights must not be empty")
    missing = set(weights) - set(scores)
    if missing:
        raise ValueError(f"missing priority score(s): {sorted(missing)}")

    weighted = 0.0
    maximum = 0.0
    for key, raw_weight in weights.items():
        weight = float(raw_weight)
        value = float(scores[key])
        if weight <= 0:
            raise ValueError(f"weight for {key!r} must be positive")
        if not 0 <= value <= 5:
            raise ValueError(f"score for {key!r} must be between 0 and 5")
        weighted += weight * value
        maximum += weight * 5.0
    return round(100.0 * weighted / maximum, 2)


def evaluate_feature(
    candidate: Mapping[str, Any],
    target: Mapping[str, Any],
    gate: Mapping[str, Any],
) -> FeatureDecision:
    """Evaluate provenance, temporal leakage, source sharing, and causal ordering."""

    name = str(candidate.get("name", "<unnamed>"))
    reasons: list[str] = []
    missing = sorted(REQUIRED_FIELDS - set(candidate))
    if missing:
        reasons.append(f"missing required field(s): {', '.join(missing)}")

    if not str(candidate.get("provenance_url", "")).startswith("https://"):
        reasons.append("provenance_url must be a non-empty HTTPS URL")
    if not str(candidate.get("license", "")).strip():
        reasons.append("license is missing")
    if candidate.get("mathematical_component_of_target") is not False:
        reasons.append("feature is a mathematical component or direct proxy of the target")
    if candidate.get("shared_data_generation_with_target") is not False:
        reasons.append("feature shares a data-generation or imputation path with the target")

    allowed_temporal = set(target.get("allowed_temporal_relations", ()))
    temporal_relation = candidate.get("temporal_relation")
    if temporal_relation not in allowed_temporal:
        reasons.append(f"temporal relation {temporal_relation!r} is not allowed")
    if candidate.get("available_before_prediction_cutoff") is not True:
        reasons.append("feature is not available before the prediction cutoff")

    minimum_lag = candidate.get("minimum_lag_years")
    try:
        minimum_lag_value = float(minimum_lag)
    except (TypeError, ValueError):
        reasons.append("minimum_lag_years must be numeric")
    else:
        if temporal_relation == "prior_calendar_year" and minimum_lag_value < 1:
            reasons.append("prior-calendar-year features require at least a one-year lag")

    allowed_causal = set(gate.get("allowed_causal_positions", ()))
    causal_position = candidate.get("causal_position")
    if causal_position not in allowed_causal:
        reasons.append(f"causal position {causal_position!r} is not eligible")

    try:
        priority_score = weighted_priority_score(
            candidate.get("priority_scores", {}), gate.get("priority_weights", {})
        )
    except (TypeError, ValueError) as exc:
        priority_score = 0.0
        reasons.append(str(exc))
    minimum_score = float(gate.get("minimum_priority_score", 100.0))
    if priority_score < minimum_score:
        reasons.append(
            f"priority score {priority_score:.2f} is below the {minimum_score:.2f} threshold"
        )

    return FeatureDecision(
        name=name,
        decision="reject" if reasons else "pass",
        priority_score=priority_score,
        reasons=tuple(reasons),
    )


def audit_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Audit a complete manifest and summarize required-feature readiness."""

    target = manifest.get("target", {})
    gate = manifest.get("gate", {})
    candidate_rows = list(manifest.get("candidates", ()))
    negative_rows = list(manifest.get("negative_controls", ()))

    candidates = [evaluate_feature(row, target, gate) for row in candidate_rows]
    negative_controls = [evaluate_feature(row, target, gate) for row in negative_rows]
    required_rejections = [
        decision.name
        for row, decision in zip(candidate_rows, candidates, strict=True)
        if bool(row.get("required")) and decision.decision != "pass"
    ]
    negative_controls_caught = all(
        decision.decision == "reject" for decision in negative_controls
    )

    return {
        "schema_version": "ppe-feature-gate-audit/v1",
        "ready": not required_rejections and negative_controls_caught,
        "required_rejections": required_rejections,
        "negative_controls_caught": negative_controls_caught,
        "candidates": [decision.to_dict() for decision in candidates],
        "negative_controls": [decision.to_dict() for decision in negative_controls],
    }
