"""Create an explicitly descriptive summary of the local 2015 pilot table."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from scipy.stats import mannwhitneyu


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "derived" / "pilot" / "pilot_event_level_2015.csv"
OUTPUT_JSON = ROOT / "outputs" / "quality" / "pilot_2015_descriptive_stats.json"
OUTPUT_MD = ROOT / "outputs" / "insights" / "pilot_2015_environment.md"


METRICS = {
    "era5_vpd_mean_24h_kpa": "ERA5 regional mean VPD, prior 24 h (kPa)",
    "era5_wind_max_24h_ms": "ERA5 regional maximum wind, prior 24 h (m/s)",
    "era5_rain_24h_mm": "ERA5 regional rainfall, prior 24 h (mm)",
    "era5_soil_water_mean_24h": "ERA5 layer-1 soil water, prior 24 h",
    "prefire_evi_mean_qa": "MOD13Q1 QA tile-summary EVI (not event-cell linked)",
}


def _summary(frame: pd.DataFrame, column: str) -> dict[str, object]:
    usable = frame[["outcome_status", column]].dropna()
    positive = usable.loc[usable["outcome_status"] == "positive", column].astype(float)
    negative = usable.loc[usable["outcome_status"] == "negative", column].astype(float)
    result: dict[str, object] = {
        "n_positive": int(len(positive)),
        "n_negative": int(len(negative)),
        "positive_median": float(positive.median()) if len(positive) else None,
        "negative_median": float(negative.median()) if len(negative) else None,
        "median_difference_positive_minus_negative": float(positive.median() - negative.median()) if len(positive) and len(negative) else None,
        "status": "descriptive_only",
    }
    if len(positive) >= 5 and len(negative) >= 5:
        test = mannwhitneyu(positive, negative, alternative="two-sided")
        result["exploratory_mann_whitney_u"] = float(test.statistic)
        result["exploratory_p_value"] = float(test.pvalue)
        result["p_value_interpretation"] = "screening statistic only; no multiple-testing or opportunity-denominator correction"
    else:
        result["exploratory_p_value"] = None
        result["p_value_interpretation"] = "not computed: fewer than five observations in one outcome group"
    return result


def build() -> dict[str, object]:
    if not INPUT.is_file():
        raise FileNotFoundError(INPUT)
    frame = pd.read_csv(INPUT)
    complete_weather = frame[frame["weather_support_status"] == "complete_pre_cutoff_72h"].copy()
    metrics = {
        column: {"label": label, **_summary(complete_weather, column)}
        for column, label in METRICS.items()
        if column in complete_weather.columns
    }
    report = {
        "schema_version": "pilot-descriptive-stats/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "exploratory_descriptive_not_phase2",
        "input": str(INPUT.relative_to(ROOT)),
        "outcome_definition": "an overpass is positive when at least one valid diagnostic cell has a VIIRS fire pixel; this is not a canonical fire-occurrence denominator",
        "summary": {
            "all_events": int(len(frame)),
            "complete_weather_events": int(len(complete_weather)),
            "positive_events": int((frame["outcome_status"] == "positive").sum()),
            "negative_events": int((frame["outcome_status"] == "negative").sum()),
        },
        "metrics": metrics,
        "guardrails": [
            "This table is a 2015 diagnostic subset, not the registered 2015-2025 opportunity frame.",
            "ERA5 values are regional means and MOD13Q1 values are tile summaries; neither is cell-specific.",
            "CHIRPS and peat are not spatially linked in this table.",
            "Exploratory p-values are screening values only and do not establish significance or causality.",
            "No claim about government mitigation, commercial actors, plantations, or peat vulnerability is made.",
        ],
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# 2015 local environmental pilot",
        "",
        "> Exploratory descriptive output only. It is not the Phase 2 model and does not establish causality.",
        "",
        f"The table contains **{report['summary']['all_events']}** diagnostic overpass-events; **{report['summary']['complete_weather_events']}** have complete 72-hour ERA5 support. The diagnostic outcome is positive when at least one valid cell contains a fire pixel.",
        "",
        "| Measure | Positive median | Negative median | Difference | Screening p-value |",
        "|---|---:|---:|---:|---:|",
    ]
    for column, item in metrics.items():
        p = item.get("exploratory_p_value")
        lines.append(
            f"| {item['label']} | {item['positive_median'] if item['positive_median'] is not None else '—'} | {item['negative_median'] if item['negative_median'] is not None else '—'} | {item['median_difference_positive_minus_negative'] if item['median_difference_positive_minus_negative'] is not None else '—'} | {p if p is not None else '—'} |"
        )
    lines.extend([
        "",
        "## Interpretation boundary",
        "",
        "These comparisons describe this small, observation-selected diagnostic subset. They do not correct for satellite opportunity, cloud, spatial clustering, or cell-level exposure. CHIRPS and peat were intentionally left unlinked rather than imputed. The results therefore cannot answer whether peat is more vulnerable, whether El Niño caused the events, or whether an actor caused them.",
    ])
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    report = build()
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
