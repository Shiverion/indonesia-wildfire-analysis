"""Local temporal-support QA for Phase 1 inputs.

This module answers a narrow question: do the downloaded payloads cover the
registered dates/years, and are their temporal semantics documented?  It does
not call a variable valid for a fire event, does not infer missing days, and
does not turn VIIRS positive detections into negative observations.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any


ERA5_RE = re.compile(r"era5_land_(?P<year>\d{4})_(?P<month>\d{2})\.nc$")
CHIRPS_RE = re.compile(r"chirps-v3\.0\.rnl\.(?P<date>\d{4}\.\d{2}\.\d{2})\.cog$")
MOD13_RE = re.compile(r"MOD13Q1\.A(?P<year>\d{4})(?P<doy>\d{3})\.h(?P<h>\d{2})v(?P<v>\d{2})\.061\..+\.hdf$")


def _expected_years(config: dict[str, Any]) -> list[int]:
    split = config.get("time_split", {})
    values: list[int] = []
    for key in ("measurement_calibration", "model_development", "pipeline_rehearsal", "locked_retrospective_test"):
        span = split.get(key, [])
        if isinstance(span, list) and len(span) == 2:
            values.extend(range(int(span[0]), int(span[1]) + 1))
    return sorted(set(values))


def _date_range(start: date, end: date) -> list[date]:
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def _file_payloads(path: Path, suffix: str) -> list[Path]:
    if not path.is_dir():
        return []
    return sorted(entry for entry in path.rglob(f"*{suffix}") if entry.is_file() and entry.stat().st_size > 0)


def check_era5(root: Path, study_years: list[int]) -> dict[str, Any]:
    directory = root / "data" / "raw" / "era5_land"
    files = sorted(path for path in directory.rglob("*.nc") if path.is_file() and path.stat().st_size > 0)
    observed: dict[int, set[int]] = defaultdict(set)
    malformed: list[str] = []
    for path in files:
        match = ERA5_RE.fullmatch(path.name)
        if not match:
            malformed.append(path.relative_to(root).as_posix())
            continue
        year, month = int(match["year"]), int(match["month"])
        if not 1 <= month <= 12:
            malformed.append(path.relative_to(root).as_posix())
        else:
            observed[year].add(month)
    missing_by_year = {
        str(year): [month for month in range(1, 13) if month not in observed.get(year, set())]
        for year in study_years
    }
    complete_years = sorted(year for year, months in observed.items() if months == set(range(1, 13)))
    missing_study_months = any(missing_by_year[str(year)] for year in study_years)
    if not missing_study_months and not malformed and set(study_years).issubset(set(complete_years)):
        status = "study_window_complete"
        note = "All registered monthly payloads are present; event-level UTC lagging remains unvalidated."
    elif complete_years:
        status = "partial_study_window"
        note = "Some registered years are complete, but the full study window and event-level UTC lagging remain unvalidated."
    else:
        status = "missing_or_incomplete_months"
        note = "No complete registered year is available; event-level UTC lagging remains unvalidated."
    manifest_path = directory / "download_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    manifest_variables = manifest.get("variables", [])
    return {
        "status": status,
        "payload_file_count": len(files),
        "observed_years": sorted(observed),
        "months_by_year": {str(year): sorted(months) for year, months in sorted(observed.items())},
        "complete_years": complete_years,
        "study_years": study_years,
        "missing_months_by_study_year": missing_by_year,
        "malformed_files": malformed,
        "manifest_present": manifest_path.is_file(),
        "variables_declared": manifest_variables,
        "temporal_event_lag_validated": False,
        "note": note,
    }


def check_chirps(root: Path, study_years: list[int]) -> dict[str, Any]:
    directory = root / "data" / "raw" / "chirps"
    files = _file_payloads(directory, ".cog")
    observed: list[date] = []
    malformed: list[str] = []
    for path in files:
        match = CHIRPS_RE.fullmatch(path.name)
        if not match:
            malformed.append(path.relative_to(root).as_posix())
            continue
        observed.append(date.fromisoformat(match["date"].replace(".", "-")))
    manifest_path = directory / "download_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    temporal = manifest.get("temporal", [])
    expected = _date_range(date.fromisoformat(temporal[0]), date.fromisoformat(temporal[1])) if len(temporal) == 2 else []
    counts = Counter(observed)
    observed_set = set(observed)
    missing = [entry.isoformat() for entry in expected if entry not in observed_set]
    duplicates = sorted(entry.isoformat() for entry, count in counts.items() if count > 1)
    extra = sorted(entry.isoformat() for entry in observed_set - set(expected))
    covered_years = sorted({entry.year for entry in observed})
    lag_quality_path = root / "outputs" / "quality" / "chirps_lag_features_2015.json"
    lag_output_path = root / "data" / "derived" / "chirps" / "chirps_lag_features_2015.parquet"
    lag_features_validated = False
    lag_report: dict[str, Any] = {}
    if lag_quality_path.is_file() and lag_output_path.is_file():
        try:
            lag_report = json.loads(lag_quality_path.read_text(encoding="utf-8"))
            lag_features_validated = (
                lag_report.get("schema_version") == "chirps-lag-features/v1"
                and int(lag_report.get("row_count", 0)) > 0
                and int(lag_report.get("complete_cutoff_count", 0)) > 0
            )
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            lag_features_validated = False
    if expected and not missing and lag_features_validated:
        status = "support_window_and_partial_lags_complete"
        note = "The declared 2015 support window and source-grid lag cache are complete; other study years and event linkage are absent."
    elif expected and not missing:
        status = "support_window_complete_with_extra_dates"
        note = "The 2015 Jul-Nov support window is complete, but antecedent 1/7/30/90-day extraction has not been run and other study years are absent."
    else:
        status = "missing_or_incomplete_support_window"
        note = "The declared CHIRPS support window is incomplete; no lag feature is valid until every requested day is present."
    return {
        "status": status,
        "payload_file_count": len(files),
        "covered_years": covered_years,
        "manifest_temporal": temporal,
        "expected_date_count": len(expected),
        "observed_date_count": len(observed_set),
        "missing_dates": missing,
        "duplicate_dates": duplicates,
        "extra_dates": extra,
        "malformed_files": malformed,
        "study_years": study_years,
        "study_years_present": sorted(set(covered_years) & set(study_years)),
        "lag_features_validated": lag_features_validated,
        "lag_features_path": lag_output_path.relative_to(root).as_posix() if lag_output_path.is_file() else None,
        "lag_quality_path": lag_quality_path.relative_to(root).as_posix() if lag_quality_path.is_file() else None,
        "lag_report": lag_report,
        "note": note,
    }


def check_mod13(root: Path, study_years: list[int]) -> dict[str, Any]:
    directory = root / "data" / "raw" / "mod13q1" / "MOD13Q1"
    files = _file_payloads(directory, ".hdf")
    composites: set[tuple[int, int]] = set()
    tiles: set[str] = set()
    malformed: list[str] = []
    for path in files:
        match = MOD13_RE.fullmatch(path.name)
        if not match:
            malformed.append(path.relative_to(root).as_posix())
            continue
        composites.add((int(match["year"]), int(match["doy"])))
        tiles.add(f"h{match['h']}v{match['v']}")
    years = sorted({year for year, _ in composites})
    manifest_path = root / "data" / "raw" / "mod13q1" / "download_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    qa_report_path = root / "outputs" / "quality" / "mod13q1_2015_prefire_qa.json"
    qa_report: dict[str, Any] = {}
    if qa_report_path.is_file():
        try:
            qa_report = json.loads(qa_report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            qa_report = {}
    qa_validated = qa_report.get("qa_mask_validated") is True and qa_report.get("status") == "qa_validated_tile_composite_summary"
    prefire_validated = qa_report.get("prefire_support_validated") is True
    status = "qa_validated_summary_only" if qa_validated else ("payload_inventory_only_qa_unvalidated" if files else "missing_payload")
    return {
        "status": status,
        "payload_file_count": len(files),
        "composite_count": len(composites),
        "composite_years": years,
        "study_years": study_years,
        "tiles": sorted(tiles),
        "malformed_files": malformed,
        "manifest_present": manifest_path.is_file(),
        "qa_mask_validated": qa_validated,
        "prefire_support_validated": prefire_validated,
        "qa_report_path": qa_report_path.relative_to(root).as_posix() if qa_report_path.is_file() else None,
        "qa_report": qa_report if qa_report else None,
        "note": (
            "MOD13Q1 EVI/VI Quality SDS rules are validated for the local 2015 tile/composite summary; "
            "event-specific pre-fire support and 2016-2025 coverage are still required."
            if qa_validated else
            "HDF payloads are readable at the file level, but QA SDS extraction and event-specific pre-fire support are still required."
        ),
    }


def check_viirs(root: Path, study_years: list[int]) -> dict[str, Any]:
    pair_path = root / "data" / "derived" / "viirs" / "viirs_pair_index.csv"
    summary_path = root / "data" / "derived" / "viirs" / "viirs_swath_summary.csv"
    rows: list[dict[str, str]] = []
    if pair_path.is_file():
        with pair_path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    paired = [row for row in rows if row.get("pair_status") == "paired"]
    dates = [row.get("acquisition_utc", "")[:10] for row in paired if row.get("acquisition_utc")]
    years = sorted({int(value[:4]) for value in dates if value[:4].isdigit()})
    summary_rows = 0
    failed = 0
    if summary_path.is_file():
        with summary_path.open(newline="", encoding="utf-8") as handle:
            summary_rows = sum(1 for _ in csv.DictReader(handle))
    quality_path = root / "outputs" / "quality" / "viirs_swath_summary.json"
    if quality_path.is_file():
        quality = json.loads(quality_path.read_text(encoding="utf-8"))
        failed = int(quality.get("summary", {}).get("swaths_failed", 0))
    return {
        "status": "paired_swath_screening_only" if paired and failed == 0 else "missing_or_failed_pairs",
        "pair_index_present": pair_path.is_file(),
        "paired_swath_count": len(paired),
        "screened_swath_count": summary_rows,
        "swaths_failed": failed,
        "observed_years": years,
        "study_years": study_years,
        "acquisition_dates_first": min(dates) if dates else None,
        "acquisition_dates_last": max(dates) if dates else None,
        "negative_frame_ready": False,
        "denominator_ready": False,
        "temporal_opportunity_validated": False,
        "note": "Paired geolocation screening is complete for a 2015 subset; no pixel is labelled a negative observation or valid opportunity.",
    }


def run_temporal_qa(root: Path) -> dict[str, Any]:
    config = json.loads((root / "config" / "study.json").read_text(encoding="utf-8"))
    study_years = _expected_years(config)
    assets = {
        "era5_land": check_era5(root, study_years),
        "chirps": check_chirps(root, study_years),
        "prefire_vegetation": check_mod13(root, study_years),
        "viirs_outcome_and_opportunity": check_viirs(root, study_years),
    }
    return {
        "schema_version": "phase1-temporal-qa/v1",
        "study_id": config.get("study_id"),
        "study_years": study_years,
        "assets": assets,
        "denominator_ready": False,
        "phase_1_unlock": False,
        "status": "present_inputs_need_temporal_and_opportunity_validation",
        "acceptance_rule": "No outcome, covariate, or model is unlocked by file presence alone; every event requires pre-cutoff support and VIIRS processed opportunity coverage.",
    }
