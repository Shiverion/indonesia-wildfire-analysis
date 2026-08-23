"""Evidence-bounded descriptive reports from validated protocol inputs."""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .enso import RoniRecord


@dataclass(frozen=True)
class EnoEpisode:
    state: str
    start_date: date
    end_date: date
    record_count: int
    peak_anomaly_c: float


def read_roni_csv(path: Path) -> list[RoniRecord]:
    records: list[RoniRecord] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            records.append(
                RoniRecord(
                    season=row["season"],
                    season_year=int(row["season_year"]),
                    end_date=date.fromisoformat(row["end_date"]),
                    anomaly_c=float(row["anomaly_c"]),
                )
            )
    if not records:
        raise ValueError(f"No RONI records found in {path}")
    return sorted(records, key=lambda record: record.end_date)


def _state(anomaly_c: float) -> str:
    if anomaly_c >= 0.5:
        return "El Niño threshold"
    if anomaly_c <= -0.5:
        return "La Niña threshold"
    return "neutral"


def classify_episodes(records: list[RoniRecord], minimum_records: int = 5) -> list[EnoEpisode]:
    """Identify CPC-style threshold runs; this is descriptive, not an outcome model."""
    episodes: list[EnoEpisode] = []
    run: list[RoniRecord] = []
    run_state: str | None = None
    for record in records:
        state = _state(record.anomaly_c)
        if state == "neutral":
            if run and len(run) >= minimum_records:
                episodes.append(_episode_from_run(run_state, run))
            run, run_state = [], None
            continue
        expected_days = (record.end_date - run[-1].end_date).days if run else None
        if run_state == state and expected_days is not None and 25 <= expected_days <= 35:
            run.append(record)
        else:
            if run and len(run) >= minimum_records:
                episodes.append(_episode_from_run(run_state, run))
            run, run_state = [record], state
    if run and len(run) >= minimum_records:
        episodes.append(_episode_from_run(run_state, run))
    return episodes


def _episode_from_run(state: str | None, run: list[RoniRecord]) -> EnoEpisode:
    if state is None:
        raise ValueError("Cannot construct an episode without a state")
    values = [record.anomaly_c for record in run]
    peak = max(values) if state == "El Niño threshold" else min(values)
    return EnoEpisode(state, run[0].end_date, run[-1].end_date, len(run), peak)


def _fire_season_context(records: list[RoniRecord], years: range) -> dict[int, list[RoniRecord]]:
    by_year: dict[int, list[RoniRecord]] = defaultdict(list)
    for record in records:
        # Fire season is July–November UTC. A RONI season ending in Aug–Nov is fully
        # available before the next month and is the informative descriptive context.
        if record.end_date.year in years and record.end_date.month in {8, 9, 10, 11}:
            by_year[record.end_date.year].append(record)
    return by_year


def build_enso_context_markdown(records: list[RoniRecord]) -> str:
    """Build a descriptive ENSO report without implying a human-fire estimate."""
    episodes = classify_episodes(records)
    season_context = _fire_season_context(records, range(2015, 2026))
    relevant = [record for record in records if date(2015, 1, 1) <= record.end_date <= date(2025, 12, 31)]
    max_record = max(relevant, key=lambda record: record.anomaly_c)
    min_record = min(relevant, key=lambda record: record.anomaly_c)

    lines = [
        "# ENSO Context Insight — Kalimantan Wildfire Protocol",
        "",
        "## Scope",
        "",
        "This report describes the openly retrieved NOAA CPC RONI climate series. It does **not** test the human-accessibility wildfire hypothesis, because no validated fire-observation, dated-accessibility, or transformation panel is present yet.",
        "",
        "## Descriptive result",
        "",
        f"Across 2015–2025, the highest three-month RONI value was **{max_record.anomaly_c:.2f} °C** ({max_record.season} {max_record.season_year}, ending {max_record.end_date.isoformat()}); the lowest was **{min_record.anomaly_c:.2f} °C** ({min_record.season} {min_record.season_year}, ending {min_record.end_date.isoformat()}). This confirms that the planned study window spans materially different basin-scale ENSO states.",
        "",
        "## July–November fire-season ENSO context",
        "",
        "| Year | Mean RONI across Aug–Nov completed seasons (°C) | Minimum | Maximum | Interpretation |",
        "|---:|---:|---:|---:|---|",
    ]
    for year in range(2015, 2026):
        values = season_context.get(year, [])
        if not values:
            lines.append(f"| {year} | — | — | — | missing |")
            continue
        anomalies = [record.anomaly_c for record in values]
        mean_value = sum(anomalies) / len(anomalies)
        classification = _state(mean_value)
        lines.append(
            f"| {year} | {mean_value:.2f} | {min(anomalies):.2f} | {max(anomalies):.2f} | {classification} |"
        )
    lines.extend([
        "",
        "## Threshold episodes overlapping the study era",
        "",
        "| State | Start | End | Consecutive overlapping seasons | Peak anomaly (°C) |",
        "|---|---|---|---:|---:|",
    ])
    for episode in episodes:
        if episode.end_date < date(2012, 1, 1):
            continue
        lines.append(
            f"| {episode.state} | {episode.start_date.isoformat()} | {episode.end_date.isoformat()} | {episode.record_count} | {episode.peak_anomaly_c:.2f} |"
        )
    lines.extend([
        "",
        "## Interpretation and guardrail",
        "",
        "The series supports stratifying or interacting an eventual accessibility contrast by ENSO state. It cannot itself explain spatial variation inside an exact-overpass matched risk set, because every cell in that set shares the same acquisition time and RONI value. Local rainfall, drought, VPD, and wind remain the spatially varying mechanism variables. Any claim that ENSO changed fire requires the separate complete panel and its stated temporal-block uncertainty; any claim that accessibility caused fire still requires the locked measurement and exposure gates.",
        "",
        "## Provenance",
        "",
        "Source: NOAA CPC ERSSTv6 RONI raw text archived under `data/raw/enso/RONI.ascii.txt`. See `outputs/quality/roni_fetch.json` for retrieval time and SHA-256. Recent values may be revised by CPC; this report is a frozen retrospective retrieval.",
        "",
    ])
    return "\n".join(lines)
