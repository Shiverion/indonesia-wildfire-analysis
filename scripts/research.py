#!/usr/bin/env python3
"""Command line entry point for the reproducible research scaffold."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wildfire_research.enso import DEFAULT_RONI_URL, fetch_roni, write_roni_artifacts
from wildfire_research.explorer import write_explorer_artifacts
from wildfire_research.insights import build_enso_context_markdown, read_roni_csv
from wildfire_research.gwis import (
    DEFAULT_GWIS_URL,
    build_gwis_context_markdown,
    fetch_gwis,
    read_gwis_csv,
    write_gwis_artifacts,
)
from wildfire_research.ledger import append_phase_entry, verify_phase_ledger
from wildfire_research.protocol import validate_protocol, write_validation_report
from wildfire_research.quality import create_immutable_lock, verify_immutable_lock
from wildfire_research.sipongi import (
    DEFAULT_EXCLUDED_SIPONGI_YEARS,
    DEFAULT_SIPONGI_URL,
    build_sipongi_context_markdown,
    build_sipongi_from_local_raw,
    fetch_sipongi_fire_season,
    fetch_sipongi_monitoring_snapshot,
    read_sipongi_csv,
)
from wildfire_research.temporal_qa import run_temporal_qa
from wildfire_research.phase1b import build_phase1b_readiness
from wildfire_research.mapbiomas import write_mapbiomas_preflight
from wildfire_research.synthesis import build_preliminary_synthesis_markdown


RAW_RONI = ROOT / "data" / "raw" / "enso" / "RONI.ascii.txt"
DERIVED_RONI = ROOT / "data" / "derived" / "enso" / "roni_seasons.csv"
RONI_METADATA = ROOT / "outputs" / "quality" / "roni_fetch.json"
VALIDATION_REPORT = ROOT / "outputs" / "quality" / "protocol_validation.json"
ENSO_INSIGHT_REPORT = ROOT / "outputs" / "insights" / "enso_context.md"
RAW_GWIS = ROOT / "data" / "raw" / "gwis" / "GLOBFIRE_burned_area_full_dataset_2002_2024.zip"
DERIVED_GWIS = ROOT / "data" / "derived" / "gwis" / "kalimantan_monthly_burned_area.csv"
GWIS_METADATA = ROOT / "outputs" / "quality" / "gwis_fetch.json"
GWIS_INSIGHT_REPORT = ROOT / "outputs" / "insights" / "gwis_enso_context.md"
RAW_SIPONGI = ROOT / "data" / "raw" / "sipongi"
DERIVED_SIPONGI = ROOT / "data" / "derived" / "sipongi" / "kalimantan_sipongi_jul-nov.csv"
SIPONGI_METADATA = ROOT / "outputs" / "quality" / "sipongi_fetch.json"
SIPONGI_INSIGHT_REPORT = ROOT / "outputs" / "insights" / "sipongi_enso_context.md"
SYNTHESIS_INSIGHT_REPORT = ROOT / "outputs" / "insights" / "preliminary_synthesis.md"
PHASE_LEDGER = ROOT / "outputs" / "ledger" / "phase_ledger.jsonl"
TEST_LOCK = ROOT / "outputs" / "locks" / "locked_test_inputs.json"
EXPLORER_OUTPUT_DIR = ROOT / "outputs" / "evidence-explorer"


def fetch_roni_command(url: str) -> int:
    payload, resolved_url = fetch_roni(url)
    records = write_roni_artifacts(payload, resolved_url, RAW_RONI, DERIVED_RONI, RONI_METADATA)
    print(f"Fetched {len(records)} RONI records from {resolved_url}")
    print(f"Raw: {RAW_RONI.relative_to(ROOT)}")
    print(f"Derived: {DERIVED_RONI.relative_to(ROOT)}")
    print(f"Provenance: {RONI_METADATA.relative_to(ROOT)}")
    return 0


def build_enso_command() -> int:
    if not RAW_RONI.exists():
        raise FileNotFoundError(f"Raw RONI file is missing: {RAW_RONI}. Run `fetch-roni` first.")
    payload = RAW_RONI.read_bytes()
    records = write_roni_artifacts(payload, DEFAULT_RONI_URL, RAW_RONI, DERIVED_RONI, RONI_METADATA)
    print(f"Built {len(records)} local RONI records from {RAW_RONI.relative_to(ROOT)}")
    return 0


def validate_command() -> int:
    report = validate_protocol(ROOT)
    write_validation_report(report, VALIDATION_REPORT)
    print(json.dumps({
        "result": report["result"],
        "phase_1_ready": report["phase_1_ready"],
        "error_count": len(report["errors"]),
        "warning_count": len(report["warnings"]),
        "report": str(VALIDATION_REPORT.relative_to(ROOT)),
    }, indent=2))
    return 0 if report["result"] == "pass" else 1


def status_command() -> int:
    report = validate_protocol(ROOT)
    print(f"Phase 0 protocol/provenance: implemented")
    print(f"Open ENSO source fetched: {'yes' if RAW_RONI.exists() else 'no'}")
    print(f"Phase 1 measurement gate: {'ready' if report['phase_1_ready'] else 'blocked'}")
    for row in report["phase_1_gates"]:
        state = "ready" if row["gate_ready"] else "blocked"
        print(f"- {row['asset_id']}: {state} ({row['manifest_status']})")
    return 0


def build_chirps_lags_command(output: Path | None = None, quality: Path | None = None) -> int:
    """Build the available complete source-grid CHIRPS lag cache."""
    from build_chirps_lag_features import build

    report = build(ROOT, output_path=output, quality_path=quality)
    print(json.dumps({
        "output": report["output"],
        "row_count": report["row_count"],
        "complete_cutoff_count": report["complete_cutoff_count"],
        "study_window": report["support_window"],
        "phase_1b_unlock": False,
    }, indent=2))
    return 0


def report_enso_command() -> int:
    if not DERIVED_RONI.exists():
        raise FileNotFoundError(f"Derived RONI table is missing: {DERIVED_RONI}. Run `fetch-roni` first.")
    report = build_enso_context_markdown(read_roni_csv(DERIVED_RONI))
    ENSO_INSIGHT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    ENSO_INSIGHT_REPORT.write_text(report, encoding="utf-8")
    print(f"Wrote evidence-bounded ENSO context report: {ENSO_INSIGHT_REPORT.relative_to(ROOT)}")
    return 0


def fetch_gwis_command(url: str) -> int:
    payload, resolved_url = fetch_gwis(url)
    rows = write_gwis_artifacts(payload, resolved_url, RAW_GWIS, DERIVED_GWIS, GWIS_METADATA)
    print(f"Fetched and filtered {len(rows)} Kalimantan GWIS rows from {resolved_url}")
    print(f"Raw: {RAW_GWIS.relative_to(ROOT)}")
    print(f"Derived: {DERIVED_GWIS.relative_to(ROOT)}")
    print(f"Provenance: {GWIS_METADATA.relative_to(ROOT)}")
    return 0


def report_gwis_command() -> int:
    if not DERIVED_GWIS.exists():
        raise FileNotFoundError(f"Derived GWIS table is missing: {DERIVED_GWIS}. Run `fetch-gwis` first.")
    if not DERIVED_RONI.exists():
        raise FileNotFoundError(f"Derived RONI table is missing: {DERIVED_RONI}. Run `fetch-roni` first.")
    report = build_gwis_context_markdown(read_gwis_csv(DERIVED_GWIS), read_roni_csv(DERIVED_RONI))
    GWIS_INSIGHT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    GWIS_INSIGHT_REPORT.write_text(report, encoding="utf-8")
    print(f"Wrote aggregate burned-area context report: {GWIS_INSIGHT_REPORT.relative_to(ROOT)}")
    return 0


def fetch_sipongi_command(
    *,
    start_year: int,
    end_year: int,
    url: str,
    overwrite: bool,
    delay_seconds: float,
    granularity: str,
    validation_retries: int,
    excluded_years: list[int],
) -> int:
    records, evidence = fetch_sipongi_fire_season(
        root=ROOT,
        raw_root=RAW_SIPONGI,
        derived_csv_path=DERIVED_SIPONGI,
        metadata_path=SIPONGI_METADATA,
        start_year=start_year,
        end_year=end_year,
        base_url=url,
        request_granularity=granularity,
        overwrite=overwrite,
        request_delay_seconds=delay_seconds,
        validation_retries=validation_retries,
        excluded_years=excluded_years,
        progress=lambda message: print(message, flush=True),
    )
    downloaded = sum(not item.reused_local_file for item in evidence)
    print(f"Prepared {len(records):,} SiPongi portal records from {len(evidence)} province-month files ({downloaded} downloaded).")
    print(f"Raw: {RAW_SIPONGI.relative_to(ROOT)}")
    print(f"Derived: {DERIVED_SIPONGI.relative_to(ROOT)}")
    print(f"Provenance: {SIPONGI_METADATA.relative_to(ROOT)}")
    return 0


def fetch_sipongi_snapshot_command(
    *,
    through_date: date,
    url: str,
    delay_seconds: float,
    validation_retries: int,
) -> int:
    records, evidence, derived_path, metadata_path = fetch_sipongi_monitoring_snapshot(
        root=ROOT,
        raw_root=RAW_SIPONGI,
        through_date=through_date,
        base_url=url,
        request_delay_seconds=delay_seconds,
        validation_retries=validation_retries,
        progress=lambda message: print(message, flush=True),
    )
    print(f"Prepared immutable SiPongi partial snapshot with {len(records):,} portal records from {len(evidence)} province responses.")
    print(f"Derived: {derived_path.relative_to(ROOT)}")
    print(f"Provenance: {metadata_path.relative_to(ROOT)}")
    return 0


def report_sipongi_command() -> int:
    if not DERIVED_SIPONGI.exists():
        raise FileNotFoundError(f"Derived SiPongi table is missing: {DERIVED_SIPONGI}. Run `fetch-sipongi` first.")
    if not DERIVED_RONI.exists():
        raise FileNotFoundError(f"Derived RONI table is missing: {DERIVED_RONI}. Run `fetch-roni` first.")
    metadata = json.loads(SIPONGI_METADATA.read_text(encoding="utf-8")) if SIPONGI_METADATA.exists() else {}
    excluded_years = metadata.get("query_scope", {}).get("excluded_years", DEFAULT_EXCLUDED_SIPONGI_YEARS)
    report = build_sipongi_context_markdown(
        read_sipongi_csv(DERIVED_SIPONGI),
        read_roni_csv(DERIVED_RONI),
        excluded_years=excluded_years,
    )
    SIPONGI_INSIGHT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    SIPONGI_INSIGHT_REPORT.write_text(report, encoding="utf-8")
    print(f"Wrote sensor-stratified SiPongi context report: {SIPONGI_INSIGHT_REPORT.relative_to(ROOT)}")
    return 0


def build_sipongi_command(start_year: int, end_year: int, url: str, excluded_years: list[int]) -> int:
    records, evidence = build_sipongi_from_local_raw(
        root=ROOT,
        raw_root=RAW_SIPONGI,
        derived_csv_path=DERIVED_SIPONGI,
        metadata_path=SIPONGI_METADATA,
        start_year=start_year,
        end_year=end_year,
        base_url=url,
        excluded_years=excluded_years,
    )
    print(f"Rebuilt {len(records):,} validated SiPongi portal records from {len(evidence)} selected raw files.")
    print(f"Derived: {DERIVED_SIPONGI.relative_to(ROOT)}")
    print(f"Provenance: {SIPONGI_METADATA.relative_to(ROOT)}")
    return 0


def report_synthesis_command() -> int:
    required = (DERIVED_RONI, DERIVED_GWIS, DERIVED_SIPONGI)
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Cannot build preliminary synthesis; missing: {', '.join(missing)}")
    protocol_report = validate_protocol(ROOT)
    report = build_preliminary_synthesis_markdown(
        roni_records=read_roni_csv(DERIVED_RONI),
        gwis_rows=read_gwis_csv(DERIVED_GWIS),
        sipongi_records=read_sipongi_csv(DERIVED_SIPONGI),
        protocol_report=protocol_report,
    )
    SYNTHESIS_INSIGHT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    SYNTHESIS_INSIGHT_REPORT.write_text(report, encoding="utf-8")
    print(f"Wrote evidence-bounded preliminary synthesis: {SYNTHESIS_INSIGHT_REPORT.relative_to(ROOT)}")
    return 0


def build_explorer_command() -> int:
    """Build an offline descriptive visualization without unlocking Phase 1."""
    html_path, bundle_path, bundle = write_explorer_artifacts(ROOT, EXPLORER_OUTPUT_DIR)
    print(json.dumps({
        "html": str(html_path.relative_to(ROOT)),
        "bundle": str(bundle_path.relative_to(ROOT)),
        "primary_association": bundle["display_status"]["primary_association"],
        "phase_1_ready": bundle["display_status"]["phase_1_ready"],
        "sipongi_records_aggregated": bundle["quality"]["sipongi"]["record_count"],
        "raw_si_pongi_records_embedded": bundle["quality"]["sipongi"]["raw_records_embedded"],
    }, indent=2))
    return 0


def condition_audit_command() -> int:
    """Audit the condition-specific peat vulnerability inputs locally."""
    from condition_phase_audit import run

    report = run()
    print(json.dumps({
        "output": str((ROOT / "outputs" / "quality" / "condition_phase_audit.json").relative_to(ROOT)),
        "status": report["status"],
        "condition_phase_ready": report["condition_phase_ready"],
        "assets": {key: value["status"] for key, value in report["assets"].items()},
    }, indent=2))
    return 0 if report["condition_phase_ready"] else 2


def temporal_qa_command() -> int:
    """Run local temporal-support and VIIRS opportunity QA."""
    from datetime import datetime, timezone

    report = run_temporal_qa(ROOT)
    report["validated_at_utc"] = datetime.now(timezone.utc).isoformat()
    output = ROOT / "outputs" / "quality" / "temporal_support_qa.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output.relative_to(ROOT)),
        "status": report["status"],
        "phase_1_unlock": report["phase_1_unlock"],
        "assets": {key: value["status"] for key, value in report["assets"].items()},
    }, indent=2))
    return 0


def phase1b_audit_command() -> int:
    """Run Phase 1B closure checks without network calls or model fitting."""
    report = build_phase1b_readiness(ROOT)
    output = ROOT / "outputs" / "quality" / "phase1b_readiness.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output.relative_to(ROOT)),
        "status": report["status"],
        "phase_1b_ready": report["phase_1b_ready"],
        "phase_2_unlock": report["phase_2_unlock"],
        "workstreams": {key: value["status"] for key, value in report["workstreams"].items()},
    }, indent=2))
    return 0


def mapbiomas_preflight_command() -> int:
    """Validate the local, frozen MapBiomas 2014 export hand-off."""
    report = write_mapbiomas_preflight(ROOT)
    print(json.dumps({
        "output": "outputs/quality/mapbiomas_2014_preflight.json",
        "status": report["status"],
        "ready": report["ready"],
        "errors": report["errors"],
        "next_action": report["next_action"],
    }, indent=2, ensure_ascii=False))
    return 0 if report["ready"] else 2


def log_phase_command(phase: str, status: str, note: str, evidence: list[str]) -> int:
    entry = append_phase_entry(PHASE_LEDGER, phase=phase, status=status, note=note, evidence=evidence)
    print(json.dumps({"sequence": entry["sequence"], "entry_sha256": entry["entry_sha256"], "ledger": str(PHASE_LEDGER.relative_to(ROOT))}, indent=2))
    return 0


def verify_ledger_command() -> int:
    result = verify_phase_ledger(PHASE_LEDGER)
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


def lock_test_command() -> int:
    phase1b = build_phase1b_readiness(ROOT)
    if not phase1b["phase_1b_ready"]:
        print("Refusing to create locked-test archive: the environmental Phase 1B gates are not ready.")
        print(json.dumps({
            "phase_1b_ready": phase1b["phase_1b_ready"],
            "phase_1b_workstreams": {key: value["status"] for key, value in phase1b["workstreams"].items()},
        }, indent=2))
        return 2
    sources = [
        "config/study.json",
        "config/phase2_registration.json",
        "data/manifests/assets.json",
        "data/raw/era5_land/download_manifest.json",
        "data/derived/mapbiomas",
        "data/derived/viirs/opportunity_frame.csv",
        "outputs/quality/daily_risk_set_frame.json",
        "outputs/quality/mapbiomas_2014_preflight.json",
        "outputs/quality/mapbiomas_2014_forest_mask.json",
        "outputs/quality/mapbiomas_2014_forest_fraction_1km.json",
        "outputs/quality/peat_sensitivity_provenance.json",
        "scripts/build_gee_daily_risk_sets.py",
        "scripts/finalize_daily_risk_sets.py",
        "scripts/research.py",
        "src/wildfire_research",
    ]
    lock = create_immutable_lock(
        ROOT,
        TEST_LOCK,
        sources,
        label="pre-unlock 2024-2025 locked retrospective test archive",
    )
    print(json.dumps({"lock": str(TEST_LOCK.relative_to(ROOT)), "lock_sha256": lock["lock_sha256"], "file_count": lock["file_count"]}, indent=2))
    return 0


def verify_test_lock_command() -> int:
    result = verify_immutable_lock(ROOT, TEST_LOCK)
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    fetch_parser = subparsers.add_parser("fetch-roni", help="download and derive NOAA CPC RONI")
    fetch_parser.add_argument("--url", default=DEFAULT_RONI_URL, help="official RONI URL; override only for an archived mirror")
    subparsers.add_parser("build-enso", help="derive seasonal RONI table from local raw source")
    subparsers.add_parser("validate", help="validate protocol and data manifest gates")
    subparsers.add_parser("status", help="print concise implementation status")
    chirps_lag_parser = subparsers.add_parser("build-chirps-lags", help="derive complete source-grid CHIRPS 1/7/30/90-day lags")
    chirps_lag_parser.add_argument("--output", type=Path)
    chirps_lag_parser.add_argument("--quality", type=Path)
    subparsers.add_parser("report-enso", help="write a descriptive, non-causal ENSO context report")
    gwis_parser = subparsers.add_parser("fetch-gwis", help="download and filter anonymous GWIS aggregate burned-area data")
    gwis_parser.add_argument("--url", default=DEFAULT_GWIS_URL, help="official GWIS ZIP URL; override only for an archived mirror")
    subparsers.add_parser("report-gwis", help="write a bounded GWIS burned-area/ENSO context report")
    sipongi_parser = subparsers.add_parser("fetch-sipongi", help="download/resume SiPongi July-November portal records for descriptive use")
    sipongi_parser.add_argument("--start-year", type=int, default=2015)
    sipongi_parser.add_argument("--end-year", type=int, default=2025)
    sipongi_parser.add_argument("--url", default=DEFAULT_SIPONGI_URL, help="SiPongi TXT download endpoint; preserve a provenance record if overridden")
    sipongi_parser.add_argument("--overwrite", action="store_true", help="replace existing raw province-month responses")
    sipongi_parser.add_argument("--delay-seconds", type=float, default=0.35, help="sequential delay after each downloaded request")
    sipongi_parser.add_argument("--granularity", choices=("month", "season"), default="month", help="one query per province-month (default) or per province fire season")
    sipongi_parser.add_argument("--validation-retries", type=int, default=1, help="re-fetch a response that fails geography/schema validation before failing")
    sipongi_parser.add_argument("--exclude-years", type=int, nargs="*", default=list(DEFAULT_EXCLUDED_SIPONGI_YEARS), help="known-invalid archive years to skip rather than treat as zero")
    sipongi_snapshot_parser = subparsers.add_parser("fetch-sipongi-snapshot", help="create an immutable partial SiPongi monitoring snapshot through a closed portal day")
    sipongi_snapshot_parser.add_argument("--through-date", type=date.fromisoformat, required=True, help="last closed Asia/Jakarta portal-reporting date, YYYY-MM-DD")
    sipongi_snapshot_parser.add_argument("--url", default=DEFAULT_SIPONGI_URL, help="SiPongi TXT download endpoint")
    sipongi_snapshot_parser.add_argument("--delay-seconds", type=float, default=0.35, help="sequential delay after each province response")
    sipongi_snapshot_parser.add_argument("--validation-retries", type=int, default=1, help="re-fetch a response that fails geography/schema validation before failing")
    sipongi_build_parser = subparsers.add_parser("build-sipongi", help="rebuild a complete, monthly-preferred SiPongi descriptive table from validated local raw chunks")
    sipongi_build_parser.add_argument("--start-year", type=int, default=2015)
    sipongi_build_parser.add_argument("--end-year", type=int, default=2025)
    sipongi_build_parser.add_argument("--url", default=DEFAULT_SIPONGI_URL)
    sipongi_build_parser.add_argument("--exclude-years", type=int, nargs="*", default=list(DEFAULT_EXCLUDED_SIPONGI_YEARS), help="known-invalid archive years to skip rather than treat as zero")
    subparsers.add_parser("report-synthesis", help="write a bounded cross-source insight report without estimating the central hypothesis")
    subparsers.add_parser("build-explorer", help="build an offline, aggregate-only Evidence Explorer (auxiliary Phase 0.5)")
    subparsers.add_parser("condition-audit", help="audit local condition-specific peat vulnerability inputs without network calls")
    subparsers.add_parser("temporal-qa", help="audit temporal support and VIIRS opportunity readiness without network calls")
    subparsers.add_parser("phase1b-audit", help="close Phase 1B temporal and VIIRS denominator gates without network calls")
    subparsers.add_parser("mapbiomas-preflight", help="validate the frozen MapBiomas Indonesia Collection 4.1 2014 export")
    subparsers.add_parser("report-sipongi", help="write a sensor-stratified, non-causal SiPongi context report")
    log_parser = subparsers.add_parser("log-phase", help="append a hash-linked implementation-phase entry")
    log_parser.add_argument("--phase", required=True)
    log_parser.add_argument("--status", required=True)
    log_parser.add_argument("--note", required=True)
    log_parser.add_argument("--evidence", nargs="*", default=[])
    subparsers.add_parser("verify-ledger", help="verify the hash-linked implementation ledger")
    subparsers.add_parser("lock-test", help="freeze validated pre-unlock inputs for the 2024-2025 test")
    subparsers.add_parser("verify-test-lock", help="verify the immutable locked-test input archive")
    args = parser.parse_args()
    if args.command == "fetch-roni":
        return fetch_roni_command(args.url)
    if args.command == "build-enso":
        return build_enso_command()
    if args.command == "validate":
        return validate_command()
    if args.command == "status":
        return status_command()
    if args.command == "build-chirps-lags":
        return build_chirps_lags_command(args.output, args.quality)
    if args.command == "report-enso":
        return report_enso_command()
    if args.command == "fetch-gwis":
        return fetch_gwis_command(args.url)
    if args.command == "report-gwis":
        return report_gwis_command()
    if args.command == "fetch-sipongi":
        return fetch_sipongi_command(
            start_year=args.start_year,
            end_year=args.end_year,
            url=args.url,
            overwrite=args.overwrite,
            delay_seconds=args.delay_seconds,
            granularity=args.granularity,
            validation_retries=args.validation_retries,
            excluded_years=args.exclude_years,
        )
    if args.command == "fetch-sipongi-snapshot":
        return fetch_sipongi_snapshot_command(
            through_date=args.through_date,
            url=args.url,
            delay_seconds=args.delay_seconds,
            validation_retries=args.validation_retries,
        )
    if args.command == "report-sipongi":
        return report_sipongi_command()
    if args.command == "build-sipongi":
        return build_sipongi_command(args.start_year, args.end_year, args.url, args.exclude_years)
    if args.command == "report-synthesis":
        return report_synthesis_command()
    if args.command == "build-explorer":
        return build_explorer_command()
    if args.command == "condition-audit":
        return condition_audit_command()
    if args.command == "temporal-qa":
        return temporal_qa_command()
    if args.command == "phase1b-audit":
        return phase1b_audit_command()
    if args.command == "mapbiomas-preflight":
        return mapbiomas_preflight_command()
    if args.command == "log-phase":
        return log_phase_command(args.phase, args.status, args.note, args.evidence)
    if args.command == "verify-ledger":
        return verify_ledger_command()
    if args.command == "lock-test":
        return lock_test_command()
    if args.command == "verify-test-lock":
        return verify_test_lock_command()
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
