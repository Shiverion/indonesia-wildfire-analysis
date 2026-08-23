"""Offline, evidence-bounded visualization bundle for the descriptive tracks.

The explorer deliberately aggregates the local descriptive inputs before they
reach the browser.  In particular, it never embeds SiPongi row coordinates,
administrative labels below province, timestamps, or raw provider responses.
It is an auxiliary Phase 0.5 artifact and must not be used as a fire-risk or
causal-association display.
"""

from __future__ import annotations

import hashlib
import csv
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .enso import RoniRecord
from .gwis import GwisMonthlyRecord
from .ledger import verify_phase_ledger
from .protocol import validate_protocol
from .sipongi import KALIMANTAN_PROVINCES, SipongiRecord


FIRE_SEASON_MONTHS = (7, 8, 9, 10, 11)
RONI_CONTEXT_MONTHS = (8, 9, 10, 11)
SIPONGI_DISPLAY_PLATFORMS = ("NASA-MODIS", "S-NPP", "NOAA-20", "Other / unknown")
SENSITIVE_BROWSER_FIELDS = {
    "district",
    "subdistrict",
    "village",
    "latitude",
    "longitude",
    "reported_time",
    "source_file",
    "source_sha256",
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def _read_peat_fire_analysis(root: Path) -> dict[str, Any] | None:
    """Load the global peat/fire comparison as country aggregates only.

    This is intentionally a separate descriptive module from the Kalimantan
    province globe.  The browser receives no point coordinates, raw FIRMS
    rows, source file names, or per-detection timestamps.
    """
    analysis_path = root / "outputs" / "quality" / "peat_fire_2024_global.json"
    country_path = root / "outputs" / "quality" / "peat_fire_2024_global_country.csv"
    if not analysis_path.is_file() or not country_path.is_file():
        return None
    analysis = _read_json(analysis_path)
    try:
        primary_threshold = 50
        summary = analysis["summaries"][str(primary_threshold)]
        primary_model = analysis["models"][str(primary_threshold)]
        countries: list[dict[str, Any]] = []
        with country_path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("firm_file") in {None, "", "None"}:
                    continue
                land = float(row.get("land_area_km2") or 0)
                peat_area = float(row.get(f"peat_{primary_threshold}_area_km2") or 0)
                nonpeat_area = float(row.get(f"nonpeat_{primary_threshold}_area_km2") or 0)
                peat_count = int(float(row.get(f"peat_{primary_threshold}_count") or 0))
                nonpeat_count = int(float(row.get(f"nonpeat_{primary_threshold}_count") or 0))
                if land <= 0:
                    continue
                countries.append({
                    "country_id": row.get("country_id", ""),
                    "country": row.get("country", ""),
                    "land_area_km2": round(land, 3),
                    "peat_share_percent": round(100 * peat_area / land, 3),
                    "peat_area_km2": round(peat_area, 3),
                    "nonpeat_area_km2": round(nonpeat_area, 3),
                    "peat_detection_count": peat_count,
                    "nonpeat_detection_count": nonpeat_count,
                    "peat_detection_rate_per_1000_km2": round(1000 * peat_count / peat_area, 6) if peat_area > 0 else None,
                    "nonpeat_detection_rate_per_1000_km2": round(1000 * nonpeat_count / nonpeat_area, 6) if nonpeat_area > 0 else None,
                    "total_detection_rate_per_1000_km2": round(1000 * (peat_count + nonpeat_count) / land, 6),
                })
        thresholds = []
        for threshold in (25, 50, 75):
            model = analysis["models"][str(threshold)]
            test = analysis["summaries"][str(threshold)]["global_rate_test"]
            thresholds.append({
                "threshold_percent": threshold,
                "definition": analysis["summaries"][str(threshold)]["peat_definition"],
                "matched_country_count": analysis["summaries"][str(threshold)]["matched_country_count"],
                "crude_rate_ratio": test.get("rate_ratio_peat_over_nonpeat"),
                "fixed_effect_rate_ratio": model.get("rate_ratio"),
                "fixed_effect_ci95": model.get("ci95"),
                "fixed_effect_p_two_sided": model.get("p_two_sided"),
                "bonferroni_p_three_thresholds": model.get("p_two_sided_bonferroni_three_thresholds"),
            })
        return {
            "schema_version": "peat-fire-vulnerability/v1",
            "status": analysis.get("status"),
            "analysis_year": analysis["fire_source"]["year"],
            "analysis_retrieved_at_utc": analysis.get("analysis_retrieved_at_utc"),
            "peat_release_date": analysis["peat_source"]["release_date"],
            "peat_reference_period": analysis["peat_source"]["reference_period"],
            "primary_threshold_percent": primary_threshold,
            "fire_metric": analysis["fire_source"]["metric"],
            "fire_filter": analysis["fire_source"]["filter"],
            "matched_country_count": summary["matched_country_count"],
            "primary_global_rate_ratio": summary["global_rate_test"].get("rate_ratio_peat_over_nonpeat"),
            "primary_fixed_effect_model": primary_model,
            "threshold_sensitivity": thresholds,
            "countries": countries,
            "interpretation_guardrails": analysis.get("interpretation_guardrails", []),
            "source_links": {
                "peat": analysis["peat_source"].get("source_url"),
                "fire": analysis["fire_source"].get("source_url"),
                "boundaries": analysis["country_geometry"].get("source_url"),
            },
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid peat/fire analysis artifact: {exc}") from exc


def _read_condition_phase_audit(root: Path) -> dict[str, Any] | None:
    """Expose only the condition audit status, never raw provider payloads."""
    path = root / "outputs" / "quality" / "condition_phase_audit.json"
    if not path.is_file():
        return None
    audit = _read_json(path)
    assets = audit.get("assets", {})
    if not isinstance(assets, dict):
        raise ValueError("Condition audit assets must be an object")
    return {
        "schema_version": audit.get("schema_version"),
        "status": audit.get("status"),
        "condition_phase_ready": audit.get("condition_phase_ready") is True,
        "assets": {str(key): str(value.get("status", "unknown")) for key, value in assets.items() if isinstance(value, dict)},
        "temporal_support": {
            "status": str(audit.get("temporal_support_qa", {}).get("status", "not_run")),
            "phase_1_unlock": audit.get("temporal_support_qa", {}).get("phase_1_unlock") is True,
            "assets": {
                str(key): str(value.get("status", "unknown"))
                for key, value in audit.get("temporal_support_qa", {}).get("assets", {}).items()
                if isinstance(value, dict)
            },
        },
        "required_interactions": list(audit.get("required_interactions", [])),
    }


def _platform_group(satellite: str) -> str:
    normalized = satellite.upper().replace("_", "-")
    if "MODIS" in normalized:
        return "NASA-MODIS"
    if "NOAA-20" in normalized or "NOAA20" in normalized:
        return "NOAA-20"
    if "NPP" in normalized:
        return "S-NPP"
    return "Other / unknown"


def _mean_roni_by_year(records: list[RoniRecord]) -> dict[int, float]:
    values: dict[int, list[float]] = defaultdict(list)
    for record in records:
        if record.end_date.month in RONI_CONTEXT_MONTHS:
            values[record.end_date.year].append(record.anomaly_c)
    return {year: statistics.fmean(anomalies) for year, anomalies in values.items()}


def _provenance_row(
    *,
    identifier: str,
    label: str,
    metadata: dict[str, Any],
    derived_path: Path,
    display_path: str,
    access_note: str,
    distribution: str,
) -> dict[str, Any]:
    """Select traceable metadata without exposing raw portal records."""
    return {
        "id": identifier,
        "label": label,
        "source_url": metadata.get("source_url", "not recorded"),
        "retrieved_at_utc": metadata.get("retrieved_at_utc", "not recorded"),
        "raw_sha256": metadata.get("raw_sha256") or metadata.get("raw_inventory_sha256", "not recorded"),
        "derived_path": display_path,
        "derived_sha256": _sha256_file(derived_path),
        "record_count": metadata.get("record_count", "not recorded"),
        "distribution": distribution,
        "access_note": access_note,
        "analysis_limit": metadata.get("analysis_limit", "See the source-specific limitation in the method."),
    }


def _assert_browser_safe(bundle: dict[str, Any]) -> None:
    """Refuse accidental inclusion of record-level sensitive fields in the bundle."""
    serialized = json.dumps(bundle, sort_keys=True).casefold()
    leaked = sorted(field for field in SENSITIVE_BROWSER_FIELDS if f'"{field}"' in serialized)
    if leaked:
        raise ValueError(f"Explorer bundle contains prohibited record-level fields: {', '.join(leaked)}")


def _validate_browser_bundle(bundle: dict[str, Any]) -> None:
    """Apply a few high-value integrity checks before exposing an artifact."""
    _assert_browser_safe(bundle)
    annual = bundle["sipongi_annual"]
    monthly = bundle["sipongi_monthly"]
    excluded_years = set(bundle["quality"]["sipongi"].get("excluded_years", []))
    if any(row["year"] in excluded_years for row in annual + monthly):
        raise ValueError(f"Quarantined/unvalidated SiPongi archive years must not enter the explorer: {sorted(excluded_years)}")
    annual_total = sum(row["record_count"] for row in annual)
    monthly_total = sum(row["record_count"] for row in monthly)
    expected_total = bundle["quality"]["sipongi"]["record_count"]
    if annual_total != expected_total or monthly_total != expected_total:
        raise ValueError("SiPongi aggregate counts do not conserve the validated source record count")
    if any(row["burned_area_ha"] is not None and row["burned_area_ha"] < 0 for row in bundle["gwis_legacy_monthly"]):
        raise ValueError("GWIS explorer bundle contains a negative burned-area value")
    snapshot = bundle.get("sipongi_current_snapshot")
    if snapshot is not None:
        _validate_current_sipongi_snapshot(snapshot)
    peat_fire = bundle.get("peat_fire_comparison")
    if peat_fire is not None:
        _validate_peat_fire_comparison(peat_fire)
    condition_audit = bundle.get("condition_phase_audit")
    if condition_audit is not None:
        if condition_audit.get("schema_version") != "condition-phase-audit/v1":
            raise ValueError("Condition phase audit has an unsupported schema")
        if condition_audit.get("condition_phase_ready") is not False:
            raise ValueError("Condition phase audit cannot unlock the browser explorer")


def _validate_peat_fire_comparison(value: dict[str, Any]) -> None:
    """Validate global peat/fire aggregates before browser exposure."""
    if value.get("status") != "exploratory_association_not_causal":
        raise ValueError("Peat/fire comparison must remain explicitly exploratory and non-causal")
    if value.get("analysis_year") != 2024 or value.get("peat_reference_period") != "2000-2020":
        raise ValueError("Peat/fire comparison has an unexpected analysis/reference period")
    countries = value.get("countries")
    if not isinstance(countries, list) or len(countries) < 100:
        raise ValueError("Peat/fire comparison must contain the matched global country aggregates")
    forbidden = {"latitude", "longitude", "acq_time", "reported_time", "source_file", "source_sha256", "firm_file"}
    serialized = json.dumps(value, sort_keys=True).casefold()
    leaked = sorted(field for field in forbidden if f'"{field}"' in serialized)
    if leaked:
        raise ValueError(f"Peat/fire comparison contains prohibited detection-level fields: {', '.join(leaked)}")
    for row in countries:
        for field in ("land_area_km2", "peat_share_percent", "peat_area_km2", "nonpeat_area_km2"):
            if not isinstance(row.get(field), (int, float)) or row[field] < 0:
                raise ValueError(f"Peat/fire country row has invalid {field}")
    thresholds = value.get("threshold_sensitivity")
    if not isinstance(thresholds, list) or [row.get("threshold_percent") for row in thresholds] != [25, 50, 75]:
        raise ValueError("Peat/fire comparison must include ordered 25/50/75 percent sensitivities")


def _validate_current_sipongi_snapshot(snapshot: dict[str, Any]) -> None:
    """Reject a partial snapshot that could masquerade as a full archive year."""
    season = snapshot.get("season", {})
    guardrail = snapshot.get("comparison_guardrail", {})
    validation = snapshot.get("validation", {})
    if snapshot.get("status") != "validated_partial" or season.get("complete") is not False:
        raise ValueError("SiPongi current snapshot must be explicitly validated and partial")
    required_false = (
        "included_in_annual_archive",
        "eligible_for_year_slider",
        "eligible_for_annual_chart",
        "comparable_to_completed_jul_nov_seasons",
    )
    if any(guardrail.get(key) is not False for key in required_false):
        raise ValueError("SiPongi current snapshot lost a required comparison guardrail")
    if validation.get("raw_records_embedded") is not False or validation.get("has_observation_denominator") is not False:
        raise ValueError("SiPongi current snapshot must remain aggregate-only without an observation denominator")
    if validation.get("expected_province_responses") != len(KALIMANTAN_PROVINCES):
        raise ValueError("SiPongi current snapshot has the wrong expected province count")
    if validation.get("validated_province_responses") != len(KALIMANTAN_PROVINCES):
        raise ValueError("SiPongi current snapshot lacks a validated province response")
    counts = snapshot.get("province_platform_counts")
    if not isinstance(counts, list):
        raise ValueError("SiPongi current snapshot has no aggregate province-platform counts")
    expected_pairs = {(province, platform) for province in KALIMANTAN_PROVINCES.values() for platform in SIPONGI_DISPLAY_PLATFORMS}
    actual_pairs = {(row.get("province"), row.get("platform")) for row in counts if isinstance(row, dict)}
    if actual_pairs != expected_pairs or len(counts) != len(expected_pairs):
        raise ValueError("SiPongi current snapshot must be dense across five provinces and fixed platform groups")
    if any(not isinstance(row.get("record_count"), int) or row["record_count"] < 0 for row in counts):
        raise ValueError("SiPongi current snapshot has an invalid aggregate record count")
    if sum(row["record_count"] for row in counts) != snapshot.get("total_record_count"):
        raise ValueError("SiPongi current snapshot counts do not conserve the total")


def _build_current_sipongi_snapshot(
    records: list[SipongiRecord],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Aggregate one validated partial monitor without exposing record-level data."""
    if metadata.get("status") != "validated_partial":
        raise ValueError("SiPongi monitoring metadata is not a validated partial snapshot")
    season = metadata.get("season")
    guardrail = metadata.get("comparison_guardrail")
    validation = metadata.get("validation")
    if not isinstance(season, dict) or not isinstance(guardrail, dict) or not isinstance(validation, dict):
        raise ValueError("SiPongi monitoring metadata is missing its required guardrails")
    try:
        start_date = datetime.fromisoformat(season["start_date"]).date()
        through_date = datetime.fromisoformat(metadata["through_date"]).date()
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("SiPongi monitoring metadata has invalid dates") from exc
    if season.get("complete") is not False or through_date < start_date:
        raise ValueError("SiPongi monitoring snapshot cannot be a complete or reversed season")
    files = metadata.get("files")
    file_provinces = [item.get("province_id") for item in files] if isinstance(files, list) else []
    if sorted(file_provinces) != sorted(KALIMANTAN_PROVINCES):
        raise ValueError("SiPongi monitoring snapshot does not contain exactly one validated file per province")
    if any(item.get("rejected_response_count") for item in files):
        raise ValueError("SiPongi monitoring snapshot has a rejected province response")
    if any(record.reported_date < start_date or record.reported_date > through_date for record in records):
        raise ValueError("SiPongi monitoring records exceed their declared closed-day window")
    if metadata.get("record_count") != len(records):
        raise ValueError("SiPongi monitoring records do not match their frozen provenance count")

    counts: Counter[tuple[str, str]] = Counter()
    for record in records:
        counts[(record.province, _platform_group(record.satellite))] += 1
    province_platform_counts = [
        {"province": province, "platform": platform, "record_count": counts[(province, platform)]}
        for province in KALIMANTAN_PROVINCES.values()
        for platform in SIPONGI_DISPLAY_PLATFORMS
    ]
    snapshot = {
        "snapshot_id": metadata.get("snapshot_id"),
        "status": "validated_partial",
        "season": season,
        "through_date": through_date.isoformat(),
        "retrieved_at_utc": metadata.get("retrieved_at_utc"),
        "time_basis": metadata.get("time_basis"),
        "metric": "positive portal records",
        "comparison_guardrail": guardrail,
        "validation": {
            "expected_province_responses": validation.get("expected_province_responses"),
            "validated_province_responses": validation.get("validated_province_responses"),
            "raw_inventory_sha256": validation.get("raw_inventory_sha256"),
            "provider_configuration_sha256": validation.get("provider_configuration_sha256"),
            "province_catalogue_sha256": validation.get("province_catalogue_sha256"),
            "raw_records_embedded": False,
            "has_observation_denominator": False,
        },
        "total_record_count": len(records),
        "province_platform_counts": province_platform_counts,
    }
    _validate_current_sipongi_snapshot(snapshot)
    return snapshot


def build_explorer_bundle(
    *,
    roni_records: list[RoniRecord],
    gwis_rows: list[GwisMonthlyRecord],
    sipongi_records: list[SipongiRecord],
    protocol_report: dict[str, Any],
    provenance: list[dict[str, Any]],
    ledger_state: dict[str, Any],
    sipongi_excluded_years: tuple[int, ...] = (2024,),
    sipongi_snapshot_records: list[SipongiRecord] | None = None,
    sipongi_snapshot_metadata: dict[str, Any] | None = None,
    peat_fire_comparison: dict[str, Any] | None = None,
    condition_phase_audit: dict[str, Any] | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Create a small, browser-safe aggregate bundle from validated local data."""
    if not roni_records or not gwis_rows or not sipongi_records:
        raise ValueError("Explorer requires non-empty RONI, GWIS, and SiPongi inputs")

    if (sipongi_snapshot_records is None) != (sipongi_snapshot_metadata is None):
        raise ValueError("SiPongi current snapshot records and metadata must be supplied together")

    generated_at = generated_at or datetime.now(timezone.utc)
    roni_by_year = _mean_roni_by_year(roni_records)
    latest_roni = max(roni_records, key=lambda record: record.end_date)

    # GWIS has only observed admin-1/month rows. Absence is retained as
    # unknown coverage rather than silently turned into a zero outcome. A dense
    # source-row matrix is included for auditability, with null values for
    # rows absent from the source archive.
    all_gwis_index = {(row.gid_1, row.year, row.month): row for row in gwis_rows}
    gwis_gids = sorted({row.gid_1 for row in gwis_rows})
    gwis_province_by_gid = {row.gid_1: row.province for row in gwis_rows}
    gwis_legacy_monthly: list[dict[str, Any]] = []
    for year in range(min(row.year for row in gwis_rows), max(row.year for row in gwis_rows) + 1):
        for month in range(1, 13):
            for gid in gwis_gids:
                row = all_gwis_index.get((gid, year, month))
                gwis_legacy_monthly.append({
                    "gid_1": gid,
                    "province": gwis_province_by_gid[gid],
                    "year": year,
                    "month": month,
                    "burned_area_ha": None if row is None else row.burned_area_ha,
                    "fire_count": None if row is None else row.fire_count,
                    "source_row_present": row is not None,
                })
    gwis_by_year: dict[int, list[GwisMonthlyRecord]] = defaultdict(list)
    gwis_by_year_province: dict[tuple[int, str, str], list[GwisMonthlyRecord]] = defaultdict(list)
    for row in gwis_rows:
        if row.month in FIRE_SEASON_MONTHS:
            gwis_by_year[row.year].append(row)
            gwis_by_year_province[(row.year, row.gid_1, row.province)].append(row)

    gwis_annual: list[dict[str, Any]] = []
    for year in sorted(gwis_by_year):
        rows = gwis_by_year[year]
        gwis_annual.append({
            "year": year,
            "burned_area_ha": round(sum(row.burned_area_ha for row in rows), 3),
            "fire_count": sum(row.fire_count for row in rows),
            "observed_province_month_rows": len({(row.gid_1, row.month) for row in rows}),
            "expected_province_month_rows": 20,
            "roni_aug_nov_c": round(roni_by_year[year], 3) if year in roni_by_year else None,
        })

    gwis_province: list[dict[str, Any]] = []
    for (year, gid, province), rows in sorted(gwis_by_year_province.items()):
        gwis_province.append({
            "year": year,
            "gid_1": gid,
            "province": province,
            "burned_area_ha": round(sum(row.burned_area_ha for row in rows), 3),
            "fire_count": sum(row.fire_count for row in rows),
            "observed_months": len({row.month for row in rows}),
            "expected_months": len(FIRE_SEASON_MONTHS),
        })

    # The SiPongi source is represented only as province/year/month/platform
    # counts.  No points, local administrative labels, or raw timestamps go to
    # the browser because source redistribution terms remain unresolved.
    sipongi_grouped: Counter[tuple[int, int, str, str]] = Counter()
    sipongi_annual_grouped: Counter[tuple[int, str, str]] = Counter()
    sipongi_quality_grouped: dict[tuple[int, int, str, str, str], dict[str, Any]] = {}
    for record in sipongi_records:
        if record.reported_date.month not in FIRE_SEASON_MONTHS:
            raise ValueError("Explorer input contains a SiPongi record outside July-November")
        platform = _platform_group(record.satellite)
        year = record.reported_date.year
        month = record.reported_date.month
        sipongi_grouped[(year, month, record.province, platform)] += 1
        sipongi_annual_grouped[(year, record.province, platform)] += 1
        quality_key = (year, month, record.province, platform, record.confidence)
        quality = sipongi_quality_grouped.setdefault(quality_key, {
            "record_count": 0,
            "active_dates": set(),
            "repaired_row_count": 0,
        })
        quality["record_count"] += 1
        quality["active_dates"].add(record.reported_date)
        quality["repaired_row_count"] += int(record.source_schema_repaired)

    sipongi_monthly = [
        {
            "year": year,
            "month": month,
            "province": province,
            "platform": platform,
            "record_count": count,
        }
        for (year, month, province, platform), count in sorted(sipongi_grouped.items())
    ]
    sipongi_annual = [
        {
            "year": year,
            "province": province,
            "platform": platform,
            "record_count": count,
        }
        for (year, province, platform), count in sorted(sipongi_annual_grouped.items())
    ]
    sipongi_monthly_by_confidence = [
        {
            "year": year,
            "month": month,
            "province": province,
            "platform": platform,
            "confidence": confidence,
            "record_count": quality["record_count"],
            "active_date_count": len(quality["active_dates"]),
            "repaired_row_count": quality["repaired_row_count"],
        }
        for (year, month, province, platform, confidence), quality in sorted(sipongi_quality_grouped.items())
    ]
    current_snapshot = (
        _build_current_sipongi_snapshot(sipongi_snapshot_records, sipongi_snapshot_metadata)
        if sipongi_snapshot_records is not None and sipongi_snapshot_metadata is not None
        else None
    )

    blocked_assets = [
        gate["asset_id"]
        for gate in protocol_report.get("phase_1_gates", [])
        if not gate.get("gate_ready")
    ]
    bundle = {
        "schema_version": "evidence-explorer/v2",
        "generated_at_utc": generated_at.astimezone(timezone.utc).isoformat(),
        "title": "Kalimantan Fire Evidence Explorer",
        "display_status": {
            "label": "Descriptive evidence only",
            "primary_association": "NI - Not identifiable",
            "phase_1_ready": bool(protocol_report.get("phase_1_ready")),
            "blocked_assets": blocked_assets,
        },
        "scope": {
            "fire_season_months": list(FIRE_SEASON_MONTHS),
            "roni_context_months": list(RONI_CONTEXT_MONTHS),
            "gwis_years": [min(row["year"] for row in gwis_annual), max(row["year"] for row in gwis_annual)],
            "sipongi_years": [
                min(row["year"] for row in sipongi_annual),
                max(row["year"] for row in sipongi_annual),
            ],
        },
        "boundary_sets": [
            {
                "id": "gwis_gadm36_legacy_4",
                "unit_count": 4,
                "geography_note": "Historic Kalimantan Timur includes territory later represented as Kalimantan Utara.",
            },
            {
                "id": "sipongi_current_5",
                "unit_count": 5,
                "geography_note": "Current provincial reporting units; not harmonized to GWIS legacy geography.",
            },
        ],
        "limitations": [
            "The central human-accessibility and land-transformation hypothesis is not identifiable because the primary matched-overpass inputs have not passed Phase 1.",
            "GWIS values are aggregate historic four-province admin-1 burned-area rows, not individual event onsets, forest-only area, or a valid observation denominator.",
            "The GWIS legacy Kalimantan Timur unit includes territory now represented as Kalimantan Utara. It is not directly comparable with the current five-province SiPongi geography.",
            "SiPongi values are positive portal hotspot records, not fires, ignitions, unique events, occurrence rates, or detection probabilities.",
            "SiPongi all-platform counts cannot be interpreted longitudinally because portal platform composition changes; NASA-MODIS is the default display stratum.",
            "SiPongi 2024 is excluded: provider responses were quarantined after geography validation failed. Missing or rejected data are not rendered as zero.",
            "No raw SiPongi coordinates, local administrative labels, timestamps, or raw provider records are included in this explorer.",
            "The interactive globe uses rounded provincial aggregate reference anchors and simplified regional outlines for orientation only; it does not assert a vetted province-boundary geometry.",
        ],
        "provenance": provenance,
        "ledger": ledger_state,
        "quality": {
            "sipongi": {
                "record_count": len(sipongi_records),
                "year_range": [min(record.reported_date.year for record in sipongi_records), max(record.reported_date.year for record in sipongi_records)],
                "quarantined_request_count": 6,
                "excluded_years": list(sorted(set(sipongi_excluded_years))),
                "time_basis": "Portal-reported date; UTC unvalidated.",
                "has_observation_denominator": False,
                "raw_records_embedded": False,
            },
            "gwis": {
                "sparse_source_row_count": len(gwis_rows),
                "missing_rows_are_zero": False,
            },
        },
        "roni_annual": [
            {"year": year, "mean_aug_nov_c": round(value, 3)}
            for year, value in sorted(roni_by_year.items())
            if 2002 <= year <= 2026
        ],
        "latest_roni": {
            "season": latest_roni.season,
            "season_year": latest_roni.season_year,
            "end_date": latest_roni.end_date.isoformat(),
            "anomaly_c": round(latest_roni.anomaly_c, 3),
            "provisional": True,
        },
        "gwis_annual": gwis_annual,
        "gwis_province": gwis_province,
        "gwis_legacy_monthly": gwis_legacy_monthly,
        "sipongi_annual": sipongi_annual,
        "sipongi_monthly": sipongi_monthly,
        "sipongi_monthly_by_confidence": sipongi_monthly_by_confidence,
        "sipongi_platforms": list(SIPONGI_DISPLAY_PLATFORMS),
        "sipongi_current_snapshot": current_snapshot,
        "peat_fire_comparison": peat_fire_comparison,
        "condition_phase_audit": condition_phase_audit,
    }
    _validate_browser_bundle(bundle)
    return bundle


def _latest_validated_sipongi_snapshot(root: Path) -> tuple[Path, dict[str, Any], Path] | None:
    """Return the newest immutable partial snapshot with a local normalized table."""
    metadata_root = root / "outputs" / "quality" / "sipongi_snapshots"
    candidates: list[tuple[str, Path, dict[str, Any], Path]] = []
    for metadata_path in metadata_root.glob("*.json") if metadata_root.exists() else ():
        metadata = _read_json(metadata_path)
        snapshot_id = metadata.get("snapshot_id")
        if metadata.get("status") != "validated_partial" or not isinstance(snapshot_id, str):
            continue
        derived_path = root / "data" / "derived" / "sipongi" / "snapshots" / f"{snapshot_id}.csv"
        if derived_path.is_file():
            candidates.append((str(metadata.get("retrieved_at_utc", "")), metadata_path, metadata, derived_path))
    if not candidates:
        return None
    _, metadata_path, metadata, derived_path = max(candidates, key=lambda item: (item[0], item[1].name))
    return metadata_path, metadata, derived_path


def build_explorer_from_workspace(root: Path) -> dict[str, Any]:
    """Load the frozen local descriptive artifacts and make a browser bundle."""
    from .gwis import read_gwis_csv
    from .insights import read_roni_csv
    from .sipongi import read_sipongi_csv

    roni_path = root / "data" / "derived" / "enso" / "roni_seasons.csv"
    gwis_path = root / "data" / "derived" / "gwis" / "kalimantan_monthly_burned_area.csv"
    sipongi_path = root / "data" / "derived" / "sipongi" / "kalimantan_sipongi_jul-nov.csv"
    required = (roni_path, gwis_path, sipongi_path)
    missing = [str(path.relative_to(root)) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Cannot build evidence explorer; missing: {', '.join(missing)}")

    roni_metadata = _read_json(root / "outputs" / "quality" / "roni_fetch.json")
    gwis_metadata = _read_json(root / "outputs" / "quality" / "gwis_fetch.json")
    sipongi_metadata = _read_json(root / "outputs" / "quality" / "sipongi_fetch.json")
    excluded_years = tuple(int(year) for year in sipongi_metadata.get("query_scope", {}).get("excluded_years", [2024]))
    snapshot_source = _latest_validated_sipongi_snapshot(root)
    peat_fire_comparison = _read_peat_fire_analysis(root)
    condition_phase_audit = _read_condition_phase_audit(root)
    protocol_report = validate_protocol(root)
    ledger_state = verify_phase_ledger(root / "outputs" / "ledger" / "phase_ledger.jsonl")
    provenance = [
        _provenance_row(
            identifier="roni",
            label="NOAA CPC RONI",
            metadata=roni_metadata,
            derived_path=roni_path,
            display_path=roni_path.relative_to(root).as_posix(),
            access_note="Open CPC retrospective retrieval; recent values can revise.",
            distribution="public",
        ),
        _provenance_row(
            identifier="gwis",
            label="GWIS / GLOBFIRE aggregate archive",
            metadata=gwis_metadata,
            derived_path=gwis_path,
            display_path=gwis_path.relative_to(root).as_posix(),
            access_note="Anonymous aggregate descriptive archive through 2024.",
            distribution="public",
        ),
        _provenance_row(
            identifier="sipongi",
            label="SiPongi portal aggregate view",
            metadata=sipongi_metadata,
            derived_path=sipongi_path,
            display_path=sipongi_path.relative_to(root).as_posix(),
            access_note="Public portal; record-level redistribution terms remain unresolved.",
            distribution="local aggregate only pending terms review",
        ),
    ]
    snapshot_records: list[SipongiRecord] | None = None
    snapshot_metadata: dict[str, Any] | None = None
    if snapshot_source is not None:
        snapshot_metadata_path, snapshot_metadata, snapshot_derived_path = snapshot_source
        snapshot_records = read_sipongi_csv(snapshot_derived_path)
        provenance.append(
            _provenance_row(
                identifier="sipongi_current_snapshot",
                label="SiPongi latest closed-day portal snapshot",
                metadata=snapshot_metadata,
                derived_path=snapshot_derived_path,
                display_path=snapshot_derived_path.relative_to(root).as_posix(),
                access_note="Validated partial monitoring only; not comparable with completed July-November seasons.",
                distribution="local aggregate only pending terms review",
            )
        )
    return build_explorer_bundle(
        roni_records=read_roni_csv(roni_path),
        gwis_rows=read_gwis_csv(gwis_path),
        sipongi_records=read_sipongi_csv(sipongi_path),
        protocol_report=protocol_report,
        provenance=provenance,
        ledger_state=ledger_state,
        sipongi_excluded_years=excluded_years,
        sipongi_snapshot_records=snapshot_records,
        sipongi_snapshot_metadata=snapshot_metadata,
        peat_fire_comparison=peat_fire_comparison,
        condition_phase_audit=condition_phase_audit,
    )


def render_explorer_html(bundle: dict[str, Any]) -> str:
    """Render a dependency-free, self-contained interactive HTML explorer."""
    _validate_browser_bundle(bundle)
    embedded_data = json.dumps(bundle, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return _HTML_TEMPLATE.replace("__EMBEDDED_DATA__", embedded_data)


def write_explorer_artifacts(root: Path, output_dir: Path) -> tuple[Path, Path, dict[str, Any]]:
    """Write both a traceable JSON bundle and its self-contained HTML view."""
    bundle = build_explorer_from_workspace(root)
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = output_dir / "evidence-explorer.json"
    html_path = output_dir / "index.html"
    bundle_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    html_path.write_text(render_explorer_html(bundle), encoding="utf-8")
    return html_path, bundle_path, bundle


_HTML_TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="An offline, descriptive explorer for bounded Kalimantan wildfire evidence.">
  <title>Kalimantan Fire Evidence Explorer</title>
  <style>
    :root {
      --ink: #eef8f5;
      --muted: #9bb1b1;
      --muted-2: #6e8587;
      --night: #07161a;
      --deep: #0b2228;
      --panel: rgba(14, 42, 48, .86);
      --panel-solid: #0f2d34;
      --line: rgba(191, 230, 218, .14);
      --green: #4ce0a0;
      --green-2: #1aa875;
      --orange: #ff9c43;
      --orange-2: #ef622b;
      --red: #ff6760;
      --blue: #63b8ff;
      --yellow: #ffd166;
      --shadow: 0 24px 70px rgba(0, 0, 0, .26);
      --radius: 22px;
    }
    * { box-sizing: border-box; }
    html { background: var(--night); scroll-behavior: smooth; }
    body {
      margin: 0;
      min-width: 320px;
      color: var(--ink);
      background:
        radial-gradient(circle at 10% -5%, rgba(44, 157, 132, .28), transparent 31rem),
        radial-gradient(circle at 95% 8%, rgba(240, 101, 44, .18), transparent 27rem),
        linear-gradient(145deg, #061419 0%, #081b20 55%, #0b2025 100%);
      font: 15px/1.52 Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    button, select { font: inherit; }
    button { color: inherit; }
    .shell { max-width: 1540px; padding: 24px; margin: 0 auto; }
    .topline {
      display: flex; align-items: center; justify-content: space-between; gap: 18px;
      padding: 13px 0 24px; border-bottom: 1px solid var(--line);
    }
    .brand { display: flex; gap: 12px; align-items: center; min-width: 0; }
    .brand-mark {
      width: 34px; height: 34px; flex: 0 0 34px; border-radius: 50%;
      background: conic-gradient(from 200deg, var(--orange), #fdce72, var(--green), #137f72, var(--orange));
      box-shadow: 0 0 0 5px rgba(76, 224, 160, .08), 0 0 35px rgba(76, 224, 160, .23);
    }
    .eyebrow { color: var(--green); font-size: 11px; font-weight: 800; letter-spacing: .16em; text-transform: uppercase; }
    .brand h1 { margin: 0; font-size: 17px; letter-spacing: -.015em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .top-actions { display: flex; align-items: center; gap: 9px; flex-wrap: wrap; justify-content: flex-end; }
    .status-pill, .mini-pill {
      display: inline-flex; align-items: center; gap: 7px; border: 1px solid rgba(255, 166, 84, .42);
      border-radius: 999px; padding: 7px 11px; color: #ffd7ad; background: rgba(156, 63, 21, .22);
      font-size: 11px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase;
    }
    .status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--orange); box-shadow: 0 0 13px var(--orange); }
    .quiet-button {
      border: 1px solid var(--line); border-radius: 999px; padding: 8px 12px; cursor: pointer;
      background: rgba(255,255,255,.025); color: var(--ink); font-size: 12px; font-weight: 700;
    }
    .quiet-button:hover, .quiet-button:focus-visible { border-color: var(--green); background: rgba(76,224,160,.09); outline: none; }
    .hero {
      display: grid; grid-template-columns: minmax(0, 1.18fr) minmax(300px, .82fr); gap: 28px;
      padding: 46px 0 27px; align-items: stretch;
    }
    .hero-copy { padding: 16px 0 8px; }
    .hero-copy h2 { max-width: 850px; margin: 8px 0 15px; font-size: clamp(36px, 5.1vw, 70px); line-height: .98; letter-spacing: -.061em; }
    .hero-copy h2 em { color: var(--green); font-style: normal; }
    .hero-copy p { max-width: 740px; margin: 0; color: #b7ccca; font-size: 16px; }
    .hero-copy p strong { color: #fff0da; }
    .hero-note { display: flex; gap: 10px; align-items: flex-start; margin-top: 22px; color: #d9ece8; font-size: 13px; }
    .hero-note .line { height: 25px; width: 3px; flex: 0 0 3px; border-radius: 3px; background: var(--orange); box-shadow: 0 0 18px rgba(255,156,67,.8); }
    .orbit-card {
      position: relative; overflow: hidden; min-height: 290px; padding: 25px; border: 1px solid rgba(139, 219, 190, .15);
      border-radius: 28px; background: linear-gradient(145deg, rgba(26, 85, 82, .7), rgba(12, 34, 42, .87)); box-shadow: var(--shadow);
    }
    .orbit-card::before, .orbit-card::after { content: ""; position: absolute; right: -65px; bottom: -115px; width: 300px; height: 300px; border: 1px solid rgba(140,236,205,.17); border-radius: 50%; }
    .orbit-card::after { right: -22px; bottom: -78px; width: 212px; height: 212px; border-color: rgba(255,171,91,.16); }
    .orbit-copy { position: relative; z-index: 2; max-width: 295px; }
    .orbit-copy span { color: var(--green); font-size: 11px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
    .orbit-copy b { display: block; margin-top: 8px; font-size: 21px; line-height: 1.1; letter-spacing: -.03em; }
    .orbit-copy p { margin: 11px 0 0; color: #c3d8d3; font-size: 13px; }
    .gesture-list { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 23px 0 0; }
    .gesture { padding: 10px; border: 1px solid rgba(179,238,218,.13); border-radius: 11px; background: rgba(2,21,25,.2); color: #c9e5de; font-size: 11px; }
    .gesture b { display: block; color: #fff3e1; font-size: 12px; }
    .hero-globe-actions { display: flex; gap: 8px; margin-top: 17px; flex-wrap: wrap; }
    .hero-globe-actions .quiet-button { background: rgba(7,32,37,.52); }
    .controls {
      display: grid; grid-template-columns: 1.25fr .9fr .9fr; gap: 10px; padding: 13px;
      margin-bottom: 15px; border: 1px solid var(--line); border-radius: 17px; background: rgba(4, 18, 22, .28);
    }
    .field { min-width: 0; }
    .field label { display: block; margin: 0 0 5px; color: var(--muted); font-size: 10px; font-weight: 800; letter-spacing: .11em; text-transform: uppercase; }
    select { width: 100%; border: 1px solid rgba(173,225,213,.16); border-radius: 10px; padding: 9px 29px 9px 10px; color: var(--ink); background: #102c33; cursor: pointer; }
    select:focus-visible { outline: 2px solid var(--green); outline-offset: 2px; }
    .filter-note { display: none; margin: -4px 0 15px; color: #ffcf93; font-size: 12px; }
    .filter-note.visible { display: block; }
    .kpis { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 15px; }
    .kpi { min-height: 130px; padding: 18px; border: 1px solid var(--line); border-radius: 18px; background: var(--panel); box-shadow: 0 12px 30px rgba(0,0,0,.09); }
    .kpi .label { color: var(--muted); font-size: 10px; font-weight: 800; letter-spacing: .11em; text-transform: uppercase; }
    .kpi .value { margin-top: 12px; font-size: clamp(23px, 2.3vw, 34px); font-weight: 800; line-height: 1.02; letter-spacing: -.045em; }
    .kpi .detail { margin-top: 8px; color: var(--muted); font-size: 12px; }
    .kpi.ni .value { color: #ffca8d; font-size: 22px; letter-spacing: -.025em; }
    .workspace { display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(320px, .75fr); gap: 15px; }
    .card { border: 1px solid var(--line); border-radius: var(--radius); background: var(--panel); box-shadow: var(--shadow); }
    .map-card { padding: 0; overflow: hidden; min-height: 584px; }
    .card-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; padding: 21px 22px 0; }
    .card-heading h3 { margin: 0; font-size: 17px; letter-spacing: -.025em; }
    .card-heading p { margin: 4px 0 0; color: var(--muted); font-size: 12px; }
    .map-key { color: var(--green); font-size: 10px; font-weight: 800; letter-spacing: .1em; text-align: right; text-transform: uppercase; }
    .map-wrap { min-height: 495px; padding: 6px 14px 18px; }
    .globe-stage { position: relative; min-height: 430px; overflow: hidden; border-radius: 18px; background: radial-gradient(circle at 53% 38%, rgba(25,94,99,.25), rgba(2,18,24,.02) 58%); }
    #interactive-globe { display: block; width: 100%; height: 438px; touch-action: none; cursor: grab; outline: none; }
    #interactive-globe:active { cursor: grabbing; }
    #interactive-globe:focus-visible { box-shadow: inset 0 0 0 2px var(--green); border-radius: 18px; }
    .globe-hud { position: absolute; top: 13px; left: 13px; display: grid; gap: 4px; pointer-events: none; }
    .globe-hud span { width: max-content; padding: 5px 8px; color: #c9ebe1; border: 1px solid rgba(181,234,216,.13); border-radius: 999px; background: rgba(4,25,30,.62); font-size: 10px; font-weight: 780; letter-spacing: .09em; text-transform: uppercase; backdrop-filter: blur(8px); }
    .globe-tooltip { position: absolute; z-index: 3; max-width: 210px; padding: 9px 10px; border: 1px solid rgba(147,236,201,.22); border-radius: 10px; color: #eafff7; background: rgba(7,30,36,.92); box-shadow: 0 12px 30px rgba(0,0,0,.3); font-size: 11px; line-height: 1.35; pointer-events: none; transform: translate(11px, 11px); opacity: 0; transition: opacity .14s; }
    .globe-tooltip.visible { opacity: 1; }
    .globe-tooltip b { display: block; margin-bottom: 2px; color: var(--green); font-size: 12px; }
    .globe-controls { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin: 8px 7px 0; }
    .globe-controls .control-group { display: flex; gap: 7px; flex-wrap: wrap; }
    .globe-controls .quiet-button { min-height: 40px; padding: 6px 10px; font-size: 11px; }
    .gesture-hint { color: var(--muted); font-size: 11px; text-align: right; }
    .map-foot { display: flex; justify-content: space-between; gap: 16px; margin: 10px 7px 0; color: var(--muted); font-size: 11px; }
    .map-foot strong { color: #d5ede7; }
    .evidence-card { padding: 22px; display: flex; flex-direction: column; min-height: 477px; }
    .selected-title { margin: 13px 0 1px; color: var(--green); font-size: 27px; font-weight: 820; line-height: 1.05; letter-spacing: -.045em; }
    .selected-context { margin: 8px 0 20px; color: #c4d8d5; font-size: 13px; }
    .metric-list { display: grid; gap: 10px; margin-bottom: 22px; }
    .metric-line { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; padding: 11px 0; border-bottom: 1px solid var(--line); }
    .metric-line span { color: var(--muted); font-size: 12px; }
    .metric-line b { text-align: right; font-size: 14px; }
    .caution { margin-top: auto; padding: 15px; border: 1px solid rgba(255,156,67,.26); border-radius: 14px; background: rgba(166,69,24,.14); color: #fed8aa; font-size: 12px; }
    .caution b { display: block; margin-bottom: 5px; color: #fff0d8; font-size: 12px; }
    .charts { display: grid; grid-template-columns: 1.12fr .88fr; gap: 15px; margin-top: 15px; }
    .chart-card { min-height: 362px; padding-bottom: 17px; overflow: hidden; }
    .chart-svg { display: block; width: 100%; height: 250px; padding: 4px 12px 0; overflow: visible; }
    .chart-note { margin: 2px 22px 0; color: var(--muted); font-size: 11px; }
    .axis { stroke: rgba(218,246,237,.16); stroke-width: .8; }
    .axis-label { fill: #91a9a8; font-size: 9px; }
    .chart-bar { fill: url(#barGradient); opacity: .9; }
    .chart-bar:hover { fill: #ffb469; }
    .roni-line { fill: none; stroke: var(--green); stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round; }
    .roni-dot { fill: #09272d; stroke: var(--green); stroke-width: 2; }
    .stack-segment { transition: opacity .15s; }
    .stack-segment:hover { opacity: .72; }
    .table-card { margin-top: 15px; overflow: hidden; }
    .table-wrap { overflow: auto; max-height: 380px; padding: 7px 22px 20px; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th { color: var(--muted); font-size: 10px; font-weight: 800; letter-spacing: .1em; text-align: left; text-transform: uppercase; white-space: nowrap; }
    td, th { padding: 12px 10px; border-bottom: 1px solid var(--line); }
    td.num, th.num { text-align: right; }
    tbody tr:hover, tbody tr.selected { background: rgba(76,224,160,.075); }
    .province-select { min-height: 40px; border: 0; padding: 4px 0; color: #eafaf5; background: transparent; cursor: pointer; font-weight: 750; text-align: left; }
    .province-select:hover, .province-select:focus-visible { color: var(--green); outline: none; text-decoration: underline; text-underline-offset: 3px; }
    .coverage { color: var(--muted); font-variant-numeric: tabular-nums; }
    .provenance { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 15px; }
    details { padding: 19px 21px; }
    summary { cursor: pointer; color: #e7f4f1; font-size: 14px; font-weight: 800; }
    summary::marker { color: var(--green); }
    .source-list { display: grid; gap: 12px; margin: 16px 0 0; }
    .source-row { padding-top: 12px; border-top: 1px solid var(--line); }
    .source-row:first-child { padding-top: 0; border-top: 0; }
    .source-row h4 { margin: 0 0 4px; font-size: 13px; }
    .source-row p { margin: 0; color: var(--muted); font-size: 11px; overflow-wrap: anywhere; }
    .source-row a { color: #9ce4c6; }
    .limit-list { margin: 15px 0 0; padding-left: 19px; color: #c8d8d5; font-size: 12px; }
    .limit-list li { margin: 8px 0; }
    .footer { display: flex; justify-content: space-between; gap: 15px; padding: 25px 2px 9px; color: var(--muted-2); font-size: 11px; }
    dialog { width: min(680px, calc(100vw - 32px)); border: 1px solid rgba(137,229,196,.28); border-radius: 22px; padding: 0; color: var(--ink); background: #0d2a31; box-shadow: 0 32px 90px rgba(0,0,0,.65); }
    dialog::backdrop { background: rgba(0, 12, 15, .72); backdrop-filter: blur(4px); }
    .dialog-inner { padding: 26px; }
    .dialog-inner h2 { margin: 0 0 8px; font-size: 23px; letter-spacing: -.035em; }
    .dialog-inner p { color: #c4d7d4; }
    .dialog-close { margin-top: 6px; }
    @media (max-width: 1000px) {
      .hero, .workspace, .charts { grid-template-columns: 1fr; }
      .orbit-card { min-height: 240px; }
      .kpis { grid-template-columns: repeat(2, minmax(0,1fr)); }
    }
    @media (max-width: 700px) {
      .shell { padding: 15px; }
      .topline { align-items: flex-start; flex-direction: column; }
      .top-actions { justify-content: flex-start; }
      .hero { padding-top: 28px; }
      .controls { grid-template-columns: 1fr; }
      .kpis, .provenance { grid-template-columns: 1fr; }
      .map-foot { flex-direction: column; gap: 3px; }
      .footer { flex-direction: column; }
    }
    @media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto !important; } }
    @media print { body { background: #fff; color: #122; } .quiet-button, .controls { display: none; } .card, .kpi { box-shadow: none; border: 1px solid #bac; } }
  </style>
</head>
<body>
  <main class="shell">
    <header class="topline">
      <div class="brand">
        <div class="brand-mark" aria-hidden="true"></div>
        <div>
          <div class="eyebrow">Phase 0.5 / offline snapshot</div>
          <h1>Kalimantan Fire Evidence Explorer</h1>
        </div>
      </div>
      <div class="top-actions">
        <span class="status-pill"><i class="status-dot"></i> Descriptive only</span>
        <button class="quiet-button" id="open-limitations" type="button">Methods &amp; limits</button>
        <button class="quiet-button" id="fullscreen" type="button">Fullscreen</button>
      </div>
    </header>

    <section class="hero" aria-labelledby="explorer-heading">
      <div class="hero-copy">
        <div class="eyebrow">Evidence explorer, not a risk map</div>
        <h2 id="explorer-heading">Make the <em>known</em> visible.<br>Keep the unknown honest.</h2>
        <p>Explore a bounded, offline snapshot of climate context, aggregate burned area, and portal hotspot records. It intentionally does not turn incomplete inputs into a human-fire conclusion.</p>
        <div class="hero-note"><span class="line" aria-hidden="true"></span><span><strong>Primary association: NI — Not identifiable.</strong> The 1 km matched-overpass analysis remains gated by missing science-quality outcome, observation, weather, vegetation, peat, and dated-access inputs.</span></div>
      </div>
      <aside class="orbit-card" aria-label="Interactive globe navigation guide">
        <div class="orbit-copy"><span>Live spatial navigator</span><b>Rotate the evidence globe.</b><p>The globe below is a real orthographic projection: drag it, zoom it, then choose a generalized provincial aggregate anchor.</p>
          <div class="gesture-list"><div class="gesture"><b>Drag / touch</b>Rotate Earth</div><div class="gesture"><b>Scroll / pinch</b>Zoom view</div><div class="gesture"><b>Click marker</b>Select aggregate</div><div class="gesture"><b>Arrow keys</b>Rotate when focused</div></div>
          <div class="hero-globe-actions"><button class="quiet-button" id="hero-focus-globe" type="button">Focus Kalimantan</button><button class="quiet-button" id="hero-reset-globe" type="button">Reset globe</button></div>
        </div>
      </aside>
    </section>

    <section class="controls" aria-label="Explorer filters">
      <div class="field"><label for="mode">Evidence layer</label><select id="mode"><option value="sipongi">SiPongi portal records</option><option value="gwis">GWIS aggregate burned area</option></select></div>
      <div class="field"><label for="year">Fire season year</label><select id="year"></select></div>
      <div class="field" id="platform-field"><label for="platform">Satellite stratum</label><select id="platform"></select></div>
    </section>
    <div class="filter-note" id="filter-note" role="status"></div>

    <section class="kpis" aria-label="Selected evidence summary">
      <article class="kpi ni"><div class="label">Primary association</div><div class="value" id="kpi-ni">NI - Not identifiable</div><div class="detail">No accessibility or transformation estimate exists.</div></article>
      <article class="kpi"><div class="label">RONI Aug-Nov</div><div class="value" id="kpi-roni">--</div><div class="detail" id="kpi-roni-detail">ENSO context only</div></article>
      <article class="kpi"><div class="label" id="kpi-value-label">Portal records</div><div class="value" id="kpi-value">--</div><div class="detail" id="kpi-value-detail">--</div></article>
      <article class="kpi"><div class="label">Coverage signal</div><div class="value" id="kpi-coverage">--</div><div class="detail" id="kpi-coverage-detail">--</div></article>
    </section>

    <section class="workspace">
      <article class="card map-card">
        <div class="card-heading"><div><h3 id="map-heading">Interactive aggregate evidence globe</h3><p id="map-subheading">Drag to rotate, scroll to zoom, and click an anchor to inspect a provincial aggregate.</p></div><div class="map-key" id="map-key">NASA-MODIS<br>records</div></div>
        <div class="map-wrap"><div class="globe-stage"><canvas id="interactive-globe" tabindex="0" aria-describedby="map-subheading" aria-label="Interactive globe showing generalized aggregate anchors for Kalimantan"></canvas><div class="globe-hud"><span id="globe-layer-badge">Current five provinces</span><span id="globe-position-badge">Kalimantan centred</span></div><div class="globe-tooltip" id="globe-tooltip" role="status"></div></div><div class="globe-controls"><div class="control-group"><button class="quiet-button" id="globe-focus" type="button">Focus Kalimantan</button><button class="quiet-button" id="globe-reset" type="button">Reset</button><button class="quiet-button" id="globe-zoom-out" type="button" aria-label="Zoom globe out">-</button><button class="quiet-button" id="globe-zoom-in" type="button" aria-label="Zoom globe in">+</button></div><span class="gesture-hint">Drag, scroll, click a marker. Arrow keys work while the globe is focused.</span></div><div class="map-foot"><span><strong>Generalized aggregate anchors.</strong> They are provincial reference locations, not fire locations or verified boundary polygons.</span><span id="map-coverage">--</span></div></div>
      </article>
      <aside class="card evidence-card" aria-live="polite">
        <div class="eyebrow">Selected context</div>
        <div class="selected-title" id="selected-title">All current provinces</div>
        <p class="selected-context" id="selected-context">Choose a province from the map or table.</p>
        <div class="metric-list" id="metric-list"></div>
        <div class="caution" id="source-caution"></div>
      </aside>
    </section>

    <section class="charts">
      <article class="card chart-card"><div class="card-heading"><div><h3>Seasonal context, shown separately</h3><p>GWIS burned area and RONI use separate vertical scales; the display does not estimate their relationship.</p></div><span class="mini-pill">2015-2024</span></div><svg class="chart-svg" id="context-chart" role="img" aria-label="GWIS aggregate burned area bars with separate RONI climate context line"></svg><p class="chart-note">GWIS ends in 2024. Its province-month row count is shown in the table; absent rows are not treated as zero.</p></article>
      <article class="card chart-card"><div class="card-heading"><div><h3>Portal platform composition</h3><p>Changing satellite composition is an observation-design issue, not a fire trend.</p></div><span class="mini-pill">2015-2023</span></div><svg class="chart-svg" id="platform-chart" role="img" aria-label="Stacked annual counts by SiPongi portal satellite platform"></svg><p class="chart-note">Default mapping is NASA-MODIS. Use “all platforms” only to inspect composition, never as a longitudinal occurrence series.</p></article>
    </section>

    <section class="card table-card"><div class="card-heading"><div><h3 id="table-heading">Current-province portal-record table</h3><p id="table-subheading">Counts are pre-aggregated; no raw coordinates or local labels are in this explorer.</p></div><span class="mini-pill" id="table-badge">NASA-MODIS</span></div><div class="table-wrap"><table><thead id="detail-head"></thead><tbody id="detail-body"></tbody></table></div></section>

    <section class="provenance">
      <details class="card"><summary>Provenance &amp; frozen inputs</summary><div class="source-list" id="source-list"></div></details>
      <details class="card"><summary>What this explorer cannot show</summary><ul class="limit-list" id="limitations-list"></ul></details>
    </section>
    <footer class="footer"><span id="snapshot-line">Offline evidence bundle</span><span><a href="evidence-explorer.json" style="color:#9ce4c6">View aggregate JSON bundle</a> · Local, dependency-free HTML · Phase 0.5</span></footer>
  </main>

  <dialog id="limits-dialog"><div class="dialog-inner"><div class="eyebrow">Method boundary</div><h2>This is not a causal or operational fire map.</h2><p>The visual layer exists to make the available descriptive evidence inspectable while the preregistered primary design remains blocked. It does not contain a fire-risk surface, roads, vegetation, peat, named entities, 1 km predictions, or raw hotspot locations.</p><ul class="limit-list" id="dialog-limitations"></ul><button class="quiet-button dialog-close" id="close-limitations" type="button">Close</button></div></dialog>

  <script id="explorer-data" type="application/json">__EMBEDDED_DATA__</script>
  <script>
  (() => {
    "use strict";
    const DATA = JSON.parse(document.getElementById("explorer-data").textContent);
    const FIRE_MONTHS = new Set(DATA.scope.fire_season_months);
    const CURRENT_PROVINCES = ["Kalimantan Barat", "Kalimantan Tengah", "Kalimantan Selatan", "Kalimantan Timur", "Kalimantan Utara"];
    const LEGACY_PROVINCES = ["Kalimantan Barat", "Kalimantan Tengah", "Kalimantan Selatan", "Kalimantan Timur (legacy unit; includes later Kalimantan Utara area)"];
    const state = { mode: "sipongi", year: null, platform: "NASA-MODIS", province: "all" };
    const $ = (id) => document.getElementById(id);
    const fmt = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
    const decimal = new Intl.NumberFormat("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const compact = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });
    const escape = (value) => String(value).replace(/[&<>\"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[char]));
    const sum = (items, accessor) => items.reduce((total, item) => total + (accessor(item) || 0), 0);
    const roniFor = (year) => DATA.roni_annual.find((row) => row.year === Number(year));
    const gwisFor = (year) => DATA.gwis_annual.find((row) => row.year === Number(year));
    const sipongiRows = (year, platform = state.platform) => DATA.sipongi_annual.filter((row) => row.year === Number(year) && (platform === "All platforms" || row.platform === platform));
    const activeProvinces = () => state.mode === "gwis" ? LEGACY_PROVINCES : CURRENT_PROVINCES;
    const yearsForMode = () => state.mode === "gwis"
      ? DATA.gwis_annual.filter((row) => row.year >= 2015 && row.year <= 2024).map((row) => row.year)
      : [...new Set(DATA.sipongi_annual.map((row) => row.year))];

    function setYearOptions() {
      const years = yearsForMode();
      if (!years.includes(Number(state.year))) state.year = Math.max(...years);
      $("year").innerHTML = years.map((year) => `<option value="${year}">${year}</option>`).join("");
      $("year").value = String(state.year);
      $("platform-field").style.display = state.mode === "sipongi" ? "block" : "none";
    }

    function selectedRows() {
      if (state.mode === "gwis") {
        return DATA.gwis_province.filter((row) => row.year === Number(state.year));
      }
      return sipongiRows(state.year);
    }

    function perProvinceRows() {
      const rows = selectedRows();
      return activeProvinces().map((province) => {
        const matched = rows.filter((row) => row.province === province);
        if (state.mode === "gwis") {
          const isUnknown = matched.length === 0;
          return { province, value: isUnknown ? null : sum(matched, (row) => row.burned_area_ha), fireCount: isUnknown ? null : sum(matched, (row) => row.fire_count), observed: sum(matched, (row) => row.observed_months), expected: 5, isUnknown };
        }
        return { province, value: sum(matched, (row) => row.record_count), observed: 5, expected: 5, isUnknown: false };
      });
    }

    function colorScale(value, max) {
      if (value == null) return "rgba(86, 109, 111, .48)";
      if (value === 0) return "rgba(42, 78, 81, .72)";
      const t = Math.max(.12, Math.min(1, value / Math.max(1, max)));
      const hue = 144 - Math.round(t * 108);
      const light = 31 + Math.round(t * 29);
      return `hsl(${hue} 76% ${light}%)`;
    }

    function renderKpis() {
      const roni = roniFor(state.year);
      $("kpi-roni").textContent = roni ? `${decimal.format(roni.mean_aug_nov_c)} C` : "--";
      $("kpi-roni-detail").textContent = roni ? `Mean Aug-Nov RONI in ${state.year}; climate context only` : "No complete RONI context available";
      if (state.mode === "gwis") {
        const row = gwisFor(state.year);
        $("kpi-value-label").textContent = "GWIS burned area";
        $("kpi-value").textContent = row ? `${compact.format(row.burned_area_ha)} ha` : "Unknown";
        $("kpi-value-detail").textContent = "July-Nov aggregate; not forest-only or event-level";
        $("kpi-coverage").textContent = row ? `${row.observed_province_month_rows}/20` : "--";
        $("kpi-coverage-detail").textContent = "Observed GWIS province-month rows; absence remains unknown";
      } else {
        const rows = sipongiRows(state.year);
        const total = sum(rows, (row) => row.record_count);
        $("kpi-value-label").textContent = state.platform === "All platforms" ? "Portal records" : `${state.platform} records`;
        $("kpi-value").textContent = fmt.format(total);
        $("kpi-value-detail").textContent = "Positive portal records; not fires or an incidence rate";
        $("kpi-coverage").textContent = `${new Set(rows.map((row) => row.province)).size}/5`;
        $("kpi-coverage-detail").textContent = "Current provinces represented in the selected aggregate";
      }
    }

    // These reference anchors are deliberately rounded display positions for
    // province-level aggregates. They are not hotspots, event locations, or
    // a substitute for a frozen boundary dataset.
    const GLOBE_ANCHORS = {
      "Kalimantan Barat": { lon: 109.9, lat: -0.2 },
      "Kalimantan Tengah": { lon: 113.0, lat: -1.4 },
      "Kalimantan Selatan": { lon: 115.3, lat: -3.4 },
      "Kalimantan Timur": { lon: 117.2, lat: -0.4 },
      "Kalimantan Utara": { lon: 115.7, lat: 3.2 },
      "Kalimantan Timur (legacy unit; includes later Kalimantan Utara area)": { lon: 116.4, lat: 1.2 },
    };
    const GLOBE_OUTLINES = [
      { name: "Borneo", primary: true, points: [[108.7,2.0],[109.1,3.0],[110.2,3.8],[112.0,4.2],[113.8,4.5],[115.7,4.1],[117.2,3.1],[118.6,2.0],[119.1,.5],[118.8,-.6],[117.6,-1.4],[117.1,-2.8],[115.8,-3.7],[114.5,-4.0],[113.0,-3.2],[111.7,-2.8],[110.1,-2.5],[109.2,-1.4],[108.7,-.1]] },
      { name: "Sumatra", points: [[95.1,5.4],[98.5,4.6],[101.5,1.7],[103.7,-2.5],[104.2,-5.4],[102.7,-5.9],[100.5,-2.3],[98.2,1.3],[95.6,3.2]] },
      { name: "Java", points: [[105.2,-5.8],[108.3,-6.2],[112.3,-7.2],[114.8,-8.1],[113.0,-8.7],[108.6,-7.8],[105.2,-6.8]] },
      { name: "Sulawesi", points: [[119.1,1.4],[120.3,2.0],[121.3,1.0],[122.0,1.5],[123.0,.3],[122.2,-1.2],[123.4,-3.0],[122.5,-4.3],[121.3,-3.0],[120.6,-1.1],[119.5,-.4],[120.0,.5]] },
      { name: "Peninsula", points: [[100.0,6.3],[102.3,6.7],[103.6,4.7],[103.4,2.0],[102.5,1.1],[101.4,2.5],[100.5,4.5]] },
    ];
    const globe = {
      canvas: null, context: null, width: 0, height: 0, dpr: 1,
      centerLon: 114, centerLat: 0, zoom: 1.02, drag: null,
      pointers: new Map(), pinch: null, markerHits: [], hover: null,
    };

    function clamp(value, min, max) { return Math.max(min, Math.min(max, value)); }
    function wrapLongitude(value) { return ((value + 540) % 360) - 180; }
    function radians(value) { return value * Math.PI / 180; }
    function vector(lon, lat) {
      const lambda = radians(lon), phi = radians(lat);
      return [Math.cos(phi) * Math.cos(lambda), Math.sin(phi), Math.cos(phi) * Math.sin(lambda)];
    }
    function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
    function cross(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
    function unit(vectorValue) { const magnitude = Math.hypot(...vectorValue); return vectorValue.map((value) => value / magnitude); }

    function globeProjector(surface) {
      const forward = vector(globe.centerLon, globe.centerLat);
      const worldUp = Math.abs(forward[1]) > .98 ? [0, 0, 1] : [0, 1, 0];
      const right = unit(cross(forward, worldUp));
      const up = cross(right, forward);
      return (lon, lat) => {
        const point = vector(lon, lat);
        const depth = dot(point, forward);
        if (depth <= 0) return { visible: false, depth };
        return { visible: true, depth, x: surface.cx + surface.radius * dot(point, right), y: surface.cy - surface.radius * dot(point, up) };
      };
    }

    function globeSurface() {
      const radius = Math.min(globe.width, globe.height) * .405 * globe.zoom;
      return { cx: globe.width * .51, cy: globe.height * .51, radius };
    }

    function resizeGlobe() {
      const rect = globe.canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const width = Math.max(1, Math.round(rect.width * dpr));
      const height = Math.max(1, Math.round(rect.height * dpr));
      if (globe.canvas.width !== width || globe.canvas.height !== height) {
        globe.canvas.width = width; globe.canvas.height = height;
      }
      globe.width = rect.width; globe.height = rect.height; globe.dpr = dpr;
      globe.context.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function drawSegmentedLine(points, project, style, close = false) {
      const ctx = globe.context;
      let started = false;
      ctx.save(); Object.assign(ctx, style);
      for (const [lon, lat] of points) {
        const point = project(lon, lat);
        if (point.visible) {
          if (!started) { ctx.beginPath(); ctx.moveTo(point.x, point.y); started = true; }
          else ctx.lineTo(point.x, point.y);
        } else if (started) { ctx.stroke(); started = false; }
      }
      if (started && close) {
        const first = project(points[0][0], points[0][1]);
        if (first.visible) ctx.lineTo(first.x, first.y);
      }
      if (started) ctx.stroke();
      ctx.restore();
    }

    function drawLand(outline, project) {
      const projected = outline.points.map(([lon, lat]) => project(lon, lat));
      const allVisible = projected.every((point) => point.visible);
      const ctx = globe.context;
      if (outline.primary && allVisible) {
        ctx.save(); ctx.beginPath(); ctx.moveTo(projected[0].x, projected[0].y);
        projected.slice(1).forEach((point) => ctx.lineTo(point.x, point.y)); ctx.closePath();
        ctx.fillStyle = "rgba(67, 201, 144, .20)"; ctx.fill(); ctx.restore();
      }
      drawSegmentedLine(outline.points, project, { strokeStyle: outline.primary ? "rgba(122,239,190,.72)" : "rgba(111,202,182,.34)", lineWidth: outline.primary ? 1.35 : .8 }, true);
    }

    function drawGraticule(project, surface) {
      const latitudeLines = [-60, -30, 0, 30, 60];
      latitudeLines.forEach((lat) => {
        const points = []; for (let lon = -180; lon <= 180; lon += 4) points.push([lon, lat]);
        drawSegmentedLine(points, project, { strokeStyle: lat === 0 ? "rgba(141,232,202,.24)" : "rgba(151,224,210,.13)", lineWidth: lat === 0 ? 1.05 : .65 });
      });
      const start = Math.floor((globe.centerLon - 180) / 30) * 30;
      for (let lon = start; lon <= globe.centerLon + 180; lon += 30) {
        const points = []; for (let lat = -85; lat <= 85; lat += 3) points.push([lon, lat]);
        drawSegmentedLine(points, project, { strokeStyle: "rgba(151,224,210,.12)", lineWidth: .65 });
      }
      const ctx = globe.context;
      ctx.save(); ctx.setLineDash([3, 6]); ctx.strokeStyle = "rgba(164,243,215,.25)"; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.arc(surface.cx, surface.cy, surface.radius, 0, Math.PI * 2); ctx.stroke(); ctx.restore();
    }

    function markerLabel(row) {
      if (state.mode === "gwis") {
        return row.isUnknown ? "Unknown source-row coverage" : `${fmt.format(row.value)} reported ha`;
      }
      return `${fmt.format(row.value)} ${state.platform === "All platforms" ? "portal records" : `${state.platform} portal records`}`;
    }

    function drawGlobeMarkers(project, surface) {
      const rows = perProvinceRows();
      const values = rows.map((row) => row.value).filter((value) => value != null);
      const max = Math.max(1, ...values);
      const ctx = globe.context;
      globe.markerHits = [];
      rows.forEach((row) => {
        const anchor = GLOBE_ANCHORS[row.province];
        if (!anchor) return;
        const point = project(anchor.lon, anchor.lat);
        if (!point.visible) return;
        const unknown = Boolean(row.isUnknown);
        const size = unknown ? 6 : 5 + 10 * Math.sqrt(Math.max(0, row.value) / max);
        const selected = state.province === row.province;
        const hovered = globe.hover?.province === row.province;
        const base = unknown ? "#819293" : state.mode === "gwis" ? "#ff9c43" : "#4ce0a0";
        ctx.save();
        if (unknown) {
          ctx.setLineDash([3, 3]); ctx.lineWidth = 2; ctx.strokeStyle = "#c2d1cf";
          ctx.beginPath(); ctx.arc(point.x, point.y, size, 0, Math.PI * 2); ctx.stroke(); ctx.setLineDash([]);
        } else {
          const glow = ctx.createRadialGradient(point.x, point.y, 1, point.x, point.y, size * 2.2);
          glow.addColorStop(0, base); glow.addColorStop(.42, `${base}88`); glow.addColorStop(1, "rgba(0,0,0,0)");
          ctx.fillStyle = glow; ctx.beginPath(); ctx.arc(point.x, point.y, size * 2.2, 0, Math.PI * 2); ctx.fill();
          ctx.fillStyle = base; ctx.beginPath(); ctx.arc(point.x, point.y, size, 0, Math.PI * 2); ctx.fill();
          ctx.strokeStyle = "rgba(255,251,236,.95)"; ctx.lineWidth = selected ? 2.7 : 1.2; ctx.stroke();
        }
        if (selected || hovered) {
          ctx.font = "700 12px system-ui, sans-serif"; ctx.textAlign = "center"; ctx.fillStyle = "#effff9";
          ctx.shadowColor = "#04161a"; ctx.shadowBlur = 7; ctx.fillText(row.province.replace("Kalimantan ", "K."), point.x, point.y - size - 10);
        }
        ctx.restore();
        globe.markerHits.push({ ...row, point, radius: size + 6 });
      });
    }

    function drawGlobe() {
      if (!globe.canvas) return;
      resizeGlobe();
      const ctx = globe.context, surface = globeSurface(), project = globeProjector(surface);
      ctx.clearRect(0, 0, globe.width, globe.height);
      const sky = ctx.createLinearGradient(0, 0, globe.width, globe.height);
      sky.addColorStop(0, "rgba(5,34,40,.12)"); sky.addColorStop(1, "rgba(2,13,18,.0)"); ctx.fillStyle = sky; ctx.fillRect(0, 0, globe.width, globe.height);
      for (let index = 0; index < 48; index += 1) {
        const x = ((index * 97) % 1000) / 1000 * globe.width, y = ((index * 53 + 17) % 700) / 700 * globe.height;
        ctx.fillStyle = `rgba(203,246,233,${.08 + (index % 4) * .025})`; ctx.fillRect(x, y, 1, 1);
      }
      ctx.save(); ctx.shadowColor = "rgba(52,225,166,.3)"; ctx.shadowBlur = 24;
      const ocean = ctx.createRadialGradient(surface.cx - surface.radius * .36, surface.cy - surface.radius * .42, surface.radius * .05, surface.cx, surface.cy, surface.radius);
      ocean.addColorStop(0, "#174b55"); ocean.addColorStop(.55, "#0c2e39"); ocean.addColorStop(1, "#061a23");
      ctx.fillStyle = ocean; ctx.beginPath(); ctx.arc(surface.cx, surface.cy, surface.radius, 0, Math.PI * 2); ctx.fill(); ctx.restore();
      ctx.save(); ctx.beginPath(); ctx.arc(surface.cx, surface.cy, surface.radius, 0, Math.PI * 2); ctx.clip();
      drawGraticule(project, surface); GLOBE_OUTLINES.forEach((outline) => drawLand(outline, project)); drawGlobeMarkers(project, surface);
      ctx.restore();
      ctx.save(); const rim = ctx.createLinearGradient(surface.cx - surface.radius, surface.cy, surface.cx + surface.radius, surface.cy); rim.addColorStop(0, "rgba(84,226,179,.72)"); rim.addColorStop(.5, "rgba(143,244,209,.25)"); rim.addColorStop(1, "rgba(255,155,71,.65)"); ctx.strokeStyle = rim; ctx.lineWidth = 1.6; ctx.beginPath(); ctx.arc(surface.cx, surface.cy, surface.radius, 0, Math.PI * 2); ctx.stroke(); ctx.restore();
      const layer = state.mode === "gwis" ? "GWIS legacy four" : "SiPongi current five";
      $("globe-layer-badge").textContent = layer;
      const lonText = Math.round(globe.centerLon), latText = Math.round(globe.centerLat);
      $("globe-position-badge").textContent = Math.abs(globe.centerLon - 114) < 6 && Math.abs(globe.centerLat) < 5 ? "Kalimantan centred" : `View ${lonText} deg, ${latText} deg`;
    }

    function markerAt(x, y) {
      return globe.markerHits.filter((marker) => Math.hypot(marker.point.x - x, marker.point.y - y) <= marker.radius).sort((a, b) => b.point.depth - a.point.depth)[0] || null;
    }

    function hideGlobeTooltip() { $("globe-tooltip").classList.remove("visible"); }
    function showGlobeTooltip(marker, clientX, clientY) {
      const tooltip = $("globe-tooltip");
      if (!marker) { hideGlobeTooltip(); return; }
      tooltip.innerHTML = `<b>${escape(marker.province)}</b>${escape(markerLabel(marker))}<br><span>Annual provincial aggregate at a generalized reference anchor - not a hotspot location.</span>`;
      const stage = globe.canvas.getBoundingClientRect(); tooltip.style.left = `${clientX - stage.left}px`; tooltip.style.top = `${clientY - stage.top}px`; tooltip.classList.add("visible");
    }

    function focusGlobe() { globe.centerLon = 114; globe.centerLat = 0; globe.zoom = 1.95; drawGlobe(); }
    function resetGlobe() { globe.centerLon = 114; globe.centerLat = 0; globe.zoom = 1.02; globe.hover = null; hideGlobeTooltip(); drawGlobe(); }

    function setupGlobe() {
      globe.canvas = $("interactive-globe"); globe.context = globe.canvas.getContext("2d");
      const canvas = globe.canvas;
      const eventPoint = (event) => { const rect = canvas.getBoundingClientRect(); return { x: event.clientX - rect.left, y: event.clientY - rect.top }; };
      canvas.addEventListener("pointerdown", (event) => {
        canvas.setPointerCapture(event.pointerId); const point = eventPoint(event); globe.pointers.set(event.pointerId, point);
        if (globe.pointers.size === 1) globe.drag = { id: event.pointerId, x: point.x, y: point.y, lon: globe.centerLon, lat: globe.centerLat, moved: false };
        if (globe.pointers.size === 2) { const points = [...globe.pointers.values()]; globe.pinch = { distance: Math.hypot(points[0].x - points[1].x, points[0].y - points[1].y), zoom: globe.zoom }; globe.drag = null; }
      });
      canvas.addEventListener("pointermove", (event) => {
        const point = eventPoint(event); if (globe.pointers.has(event.pointerId)) globe.pointers.set(event.pointerId, point);
        if (globe.pinch && globe.pointers.size >= 2) { const points = [...globe.pointers.values()]; const distance = Math.hypot(points[0].x - points[1].x, points[0].y - points[1].y); globe.zoom = clamp(globe.pinch.zoom * distance / Math.max(1, globe.pinch.distance), .76, 3.25); drawGlobe(); return; }
        if (globe.drag && globe.drag.id === event.pointerId) { const dx = point.x - globe.drag.x, dy = point.y - globe.drag.y; globe.drag.moved ||= Math.hypot(dx, dy) > 4; globe.centerLon = wrapLongitude(globe.drag.lon - dx / Math.max(160, globe.width) * 180 / Math.PI * 2.3); globe.centerLat = clamp(globe.drag.lat + dy / Math.max(160, globe.height) * 180 / Math.PI * 1.7, -78, 78); hideGlobeTooltip(); drawGlobe(); return; }
        globe.hover = markerAt(point.x, point.y); canvas.style.cursor = globe.hover ? "pointer" : "grab"; showGlobeTooltip(globe.hover, event.clientX, event.clientY); drawGlobe();
      });
      const finishPointer = (event) => {
        const point = eventPoint(event), hit = markerAt(point.x, point.y), drag = globe.drag;
        globe.pointers.delete(event.pointerId); if (globe.pointers.size < 2) globe.pinch = null;
        if (drag && drag.id === event.pointerId && !drag.moved && hit) { state.province = hit.province; globe.hover = null; hideGlobeTooltip(); render(); }
        globe.drag = null;
      };
      canvas.addEventListener("pointerup", finishPointer); canvas.addEventListener("pointercancel", finishPointer);
      canvas.addEventListener("pointerleave", () => { if (!globe.drag) { globe.hover = null; hideGlobeTooltip(); drawGlobe(); } });
      canvas.addEventListener("wheel", (event) => { event.preventDefault(); globe.zoom = clamp(globe.zoom * Math.exp(-event.deltaY * .001), .76, 3.25); drawGlobe(); }, { passive: false });
      canvas.addEventListener("keydown", (event) => {
        const movement = event.shiftKey ? 11 : 5;
        if (event.key === "ArrowLeft") globe.centerLon = wrapLongitude(globe.centerLon - movement);
        else if (event.key === "ArrowRight") globe.centerLon = wrapLongitude(globe.centerLon + movement);
        else if (event.key === "ArrowUp") globe.centerLat = clamp(globe.centerLat + movement, -78, 78);
        else if (event.key === "ArrowDown") globe.centerLat = clamp(globe.centerLat - movement, -78, 78);
        else if (event.key === "+" || event.key === "=") globe.zoom = clamp(globe.zoom + .12, .76, 3.25);
        else if (event.key === "-" || event.key === "_") globe.zoom = clamp(globe.zoom - .12, .76, 3.25);
        else if (event.key === "Escape") { state.province = "all"; render(); return; }
        else if (event.key === "Home") { focusGlobe(); return; }
        else return;
        event.preventDefault(); drawGlobe();
      });
      const observer = new ResizeObserver(() => drawGlobe()); observer.observe(canvas);
      $("globe-focus").addEventListener("click", focusGlobe); $("globe-reset").addEventListener("click", resetGlobe);
      $("hero-focus-globe").addEventListener("click", () => { focusGlobe(); canvas.focus(); }); $("hero-reset-globe").addEventListener("click", () => { resetGlobe(); canvas.focus(); });
      $("globe-zoom-in").addEventListener("click", () => { globe.zoom = clamp(globe.zoom + .14, .76, 3.25); drawGlobe(); });
      $("globe-zoom-out").addEventListener("click", () => { globe.zoom = clamp(globe.zoom - .14, .76, 3.25); drawGlobe(); });
    }

    function renderGlobe() {
      if (!globe.canvas) setupGlobe();
      $("map-heading").textContent = state.mode === "gwis" ? "Interactive GWIS aggregate evidence globe" : "Interactive SiPongi aggregate evidence globe";
      $("map-subheading").textContent = state.mode === "gwis" ? "Historic four-province aggregate anchors. Drag to rotate; markers never split legacy Kalimantan Timur." : "Current five-province aggregate anchors. Drag to rotate, scroll to zoom, click a marker to inspect.";
      $("map-key").innerHTML = state.mode === "gwis" ? "GWIS<br>hectares" : `${escape(state.platform)}<br>records`;
      $("map-coverage").textContent = state.mode === "gwis" ? "Dashed anchor: unknown source-row coverage. Legacy Kalimantan Timur includes later Kalimantan Utara area." : "No raw points, coordinates, or exact hotspot locations are shown.";
      globe.canvas.setAttribute("aria-label", `${state.mode === "gwis" ? "GWIS historic four-province" : "SiPongi current five-province"} interactive aggregate evidence globe for ${state.year}. Use arrow keys to rotate; use the table to select a province.`);
      drawGlobe();
    }

    function renderSelectedEvidence() {
      const province = state.province;
      const chosen = province === "all" ? null : province;
      const rows = perProvinceRows();
      const row = chosen ? rows.find((item) => item.province === chosen) : null;
      const roni = roniFor(state.year);
      if (state.mode === "gwis") {
        const annual = gwisFor(state.year);
        $("selected-title").textContent = chosen || "All legacy provinces";
        $("selected-context").textContent = chosen ? "Historic GWIS admin-1 unit for the selected July-November season." : "Historic four-province GWIS aggregate. This is not comparable directly to current five-province summaries.";
        const area = chosen ? row?.value : annual?.burned_area_ha;
        const count = chosen ? row?.fireCount : annual?.fire_count;
        const coverage = chosen ? `${row.observed}/${row.expected} months` : `${annual?.observed_province_month_rows ?? "--"}/20 province-month rows`;
        $("metric-list").innerHTML = metric("Reported burned area", area == null ? "Unknown" : `${fmt.format(area)} ha`) + metric("Reported GWIS fire count", count == null ? "Unknown" : fmt.format(count)) + metric("Observed coverage", coverage) + metric("RONI Aug-Nov", roni ? `${decimal.format(roni.mean_aug_nov_c)} C` : "--");
        $("source-caution").innerHTML = "<b>Source boundary</b>GWIS is an aggregate burned-area archive, not the primary 1 km first-observed-onset outcome. Missing rows remain unknown, not zero.";
      } else {
        const all = sipongiRows(state.year);
        const total = chosen ? (row?.value || 0) : sum(all, (item) => item.record_count);
        $("selected-title").textContent = chosen || "All current provinces";
        $("selected-context").textContent = chosen ? `Pre-aggregated ${state.platform} portal-record count for the selected July-November season.` : `Pre-aggregated ${state.platform} portal-record count across the current five provinces.`;
        const monthly = DATA.sipongi_monthly.filter((item) => item.year === Number(state.year) && (state.platform === "All platforms" || item.platform === state.platform) && (!chosen || item.province === chosen));
        const monthCount = new Set(monthly.map((item) => item.month)).size;
        $("metric-list").innerHTML = metric("Portal records", total ? fmt.format(total) : "No returned positive record") + metric("Satellite stratum", state.platform) + metric("Season months with records", `${monthCount}/5`) + metric("RONI Aug-Nov", roni ? `${decimal.format(roni.mean_aug_nov_c)} C` : "--");
        $("source-caution").innerHTML = "<b>Do not read this as fire occurrence</b>SiPongi supplies positive portal hotspot records only: no processed-swath denominator, validated UTC, forest mask, or unique-event linkage.";
      }
    }
    function metric(label, value) { return `<div class="metric-line"><span>${escape(label)}</span><b>${escape(value)}</b></div>`; }

    function renderContextChart() {
      const years = DATA.gwis_annual.filter((row) => row.year >= 2015 && row.year <= 2024);
      const W = 720, H = 260, L = 46, R = 30, T = 26, B = 38, PW = W - L - R, PH = H - T - B;
      const maxArea = Math.max(...years.map((row) => row.burned_area_ha));
      const roniValues = years.map((row) => row.roni_aug_nov_c).filter((value) => value !== null);
      const rMin = Math.min(-1, ...roniValues), rMax = Math.max(1, ...roniValues);
      const x = (index) => L + (PW / years.length) * index + (PW / years.length) / 2;
      const yArea = (value) => T + PH - (value / maxArea) * PH;
      const yRoni = (value) => T + PH - ((value - rMin) / (rMax - rMin || 1)) * PH;
      const barW = Math.min(31, (PW / years.length) * .54);
      const lines = [0, .5, 1].map((t) => `<line class="axis" x1="${L}" y1="${T + PH * t}" x2="${W - R}" y2="${T + PH * t}"/>`).join("");
      const bars = years.map((row, index) => `<rect class="chart-bar" x="${x(index) - barW/2}" y="${yArea(row.burned_area_ha)}" width="${barW}" height="${T + PH - yArea(row.burned_area_ha)}" rx="4"><title>${row.year}: ${fmt.format(row.burned_area_ha)} reported GWIS hectares; ${row.observed_province_month_rows}/20 observed rows</title></rect>`).join("");
      const points = years.filter((row) => row.roni_aug_nov_c !== null).map((row, index) => [x(index), yRoni(row.roni_aug_nov_c), row]);
      const path = points.map(([px, py], index) => `${index ? "L" : "M"}${px.toFixed(1)},${py.toFixed(1)}`).join(" ");
      const dots = points.map(([px, py, row]) => `<circle class="roni-dot" cx="${px}" cy="${py}" r="3.7"><title>${row.year}: ${decimal.format(row.roni_aug_nov_c)} C mean Aug-Nov RONI</title></circle>`).join("");
      const labels = years.map((row, index) => `<text class="axis-label" x="${x(index)}" y="${H - 14}" text-anchor="middle">${String(row.year).slice(2)}</text>`).join("");
      $("context-chart").setAttribute("viewBox", `0 0 ${W} ${H}`);
      $("context-chart").innerHTML = `<defs><linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#ffb269"/><stop offset="1" stop-color="#e45e2d"/></linearGradient></defs>${lines}<text class="axis-label" x="${L}" y="15">GWIS burned area (left scale)</text><text class="axis-label" x="${W-R}" y="15" text-anchor="end" fill="#79dfb7">RONI C (right scale)</text><text class="axis-label" x="${L-6}" y="${T+PH+4}" text-anchor="end">0</text><text class="axis-label" x="${L-6}" y="${T+5}" text-anchor="end">${compact.format(maxArea)}</text><text class="axis-label" x="${W-R+6}" y="${T+PH+4}">${decimal.format(rMin)}</text><text class="axis-label" x="${W-R+6}" y="${T+5}">${decimal.format(rMax)}</text>${bars}<path class="roni-line" d="${path}"/>${dots}${labels}`;
    }

    function renderPlatformChart() {
      const years = [...new Set(DATA.sipongi_annual.map((row) => row.year))].sort((a,b) => a-b);
      const platforms = DATA.sipongi_platforms;
      const colors = { "NASA-MODIS": "#ff9c43", "S-NPP": "#4ce0a0", "NOAA-20": "#63b8ff", "Other / unknown": "#a98eff" };
      const W = 620, H = 260, L = 35, R = 16, T = 32, B = 39, PW = W - L - R, PH = H - T - B;
      const totals = years.map((year) => sum(DATA.sipongi_annual.filter((row) => row.year === year), (row) => row.record_count));
      const max = Math.max(...totals, 1), unit = PW / years.length, bw = Math.min(38, unit * .58);
      const x = (index) => L + unit * index + unit/2;
      let rects = "";
      years.forEach((year, index) => {
        let current = T + PH;
        platforms.forEach((platform) => {
          const count = sum(DATA.sipongi_annual.filter((row) => row.year === year && row.platform === platform), (row) => row.record_count);
          const height = (count / max) * PH;
          current -= height;
          if (count) rects += `<rect class="stack-segment" x="${x(index)-bw/2}" y="${current}" width="${bw}" height="${height}" rx="${Math.min(3,height/2)}" fill="${colors[platform]}"><title>${year}, ${platform}: ${fmt.format(count)} portal records</title></rect>`;
        });
      });
      const legend = platforms.map((platform, index) => `<g transform="translate(${L + index * 133}, 15)"><circle r="4" cx="0" cy="0" fill="${colors[platform]}"></circle><text class="axis-label" x="8" y="3" fill="#c8dcda">${escape(platform)}</text></g>`).join("");
      const labels = years.map((year,index) => `<text class="axis-label" x="${x(index)}" y="${H-14}" text-anchor="middle">${String(year).slice(2)}</text>`).join("");
      $("platform-chart").setAttribute("viewBox", `0 0 ${W} ${H}`);
      $("platform-chart").innerHTML = `<line class="axis" x1="${L}" y1="${T+PH}" x2="${W-R}" y2="${T+PH}"/><line class="axis" x1="${L}" y1="${T}" x2="${W-R}" y2="${T}" opacity=".35"/><text class="axis-label" x="${L}" y="${T-7}">${compact.format(max)} records</text>${legend}${rects}${labels}`;
    }

    function renderTable() {
      const rows = perProvinceRows();
      if (state.mode === "gwis") {
        $("table-heading").textContent = `GWIS historic-province table - ${state.year}`;
        $("table-subheading").textContent = "Rows absent from the archive remain unknown. Legacy Kalimantan Timur includes later Kalimantan Utara area.";
        $("table-badge").textContent = "Aggregate only";
        $("detail-head").innerHTML = "<tr><th>Historic unit</th><th class='num'>Reported burned area</th><th class='num'>Reported count</th><th class='num'>Observed months</th></tr>";
        $("detail-body").innerHTML = rows.map((row) => `<tr class="${state.province === row.province ? "selected" : ""}"><td><button type="button" class="province-select" data-province="${escape(row.province)}" aria-pressed="${state.province === row.province}">${escape(row.province)}</button></td><td class="num">${row.isUnknown ? "Unknown" : `${fmt.format(row.value)} ha`}</td><td class="num">${row.isUnknown ? "Unknown" : fmt.format(row.fireCount)}</td><td class="num coverage">${row.observed}/${row.expected}</td></tr>`).join("");
      } else {
        $("table-heading").textContent = `SiPongi current-province table - ${state.year}`;
        $("table-subheading").textContent = "Pre-aggregated positive portal records only; use a province button to select the matching globe anchor.";
        $("table-badge").textContent = state.platform;
        $("detail-head").innerHTML = "<tr><th>Current province</th><th class='num'>Portal records</th><th class='num'>Selected stratum</th><th class='num'>Season support</th></tr>";
        $("detail-body").innerHTML = rows.map((row) => `<tr class="${state.province === row.province ? "selected" : ""}"><td><button type="button" class="province-select" data-province="${escape(row.province)}" aria-pressed="${state.province === row.province}">${escape(row.province)}</button></td><td class="num">${row.value ? fmt.format(row.value) : "No returned positive record"}</td><td class="num">${escape(state.platform)}</td><td class="num coverage">Jul-Nov</td></tr>`).join("");
      }
      $("detail-body").querySelectorAll(".province-select").forEach((button) => button.addEventListener("click", () => { state.province = state.province === button.dataset.province ? "all" : button.dataset.province; render(); }));
    }

    function renderStaticInformation() {
      $("source-list").innerHTML = DATA.provenance.map((source) => `<div class="source-row"><h4>${escape(source.label)}</h4><p><a href="${escape(source.source_url)}" target="_blank" rel="noreferrer">Source / retrieval endpoint</a><br>Retrieved: ${escape(source.retrieved_at_utc)}<br>Raw/input hash: ${escape(source.raw_sha256)}<br>Derived bundle hash: ${escape(source.derived_sha256)}<br>Distribution: ${escape(source.distribution)}<br>${escape(source.access_note)}</p></div>`).join("");
      const items = DATA.limitations.map((line) => `<li>${escape(line)}</li>`).join("");
      $("limitations-list").innerHTML = items;
      $("dialog-limitations").innerHTML = items;
      const blocked = DATA.display_status.blocked_assets.join(", ");
      $("snapshot-line").textContent = `Built ${new Date(DATA.generated_at_utc).toLocaleString()} · Phase 1 ready: ${DATA.display_status.phase_1_ready ? "yes" : "no"} · blocked gates: ${blocked}`;
    }

    function renderWarning() {
      const note = $("filter-note");
      if (state.mode === "sipongi" && state.platform === "All platforms") {
        note.classList.add("visible");
        note.textContent = "Caution: all-platform portal counts mix changing MODIS, S-NPP, and NOAA-20 coverage. Use this view for composition inspection only, not a longitudinal wildfire trend.";
      } else {
        note.classList.remove("visible"); note.textContent = "";
      }
    }

    function render() {
      setYearOptions();
      renderWarning(); renderKpis(); renderGlobe(); renderSelectedEvidence(); renderContextChart(); renderPlatformChart(); renderTable();
    }

    $("mode").addEventListener("change", (event) => { state.mode = event.target.value; state.province = "all"; render(); });
    $("year").addEventListener("change", (event) => { state.year = Number(event.target.value); state.province = "all"; render(); });
    $("platform").innerHTML = ["NASA-MODIS", "All platforms", "S-NPP", "NOAA-20", "Other / unknown"].map((value) => `<option value="${escape(value)}">${escape(value)}</option>`).join("");
    $("platform").value = state.platform;
    $("platform").addEventListener("change", (event) => { state.platform = event.target.value; state.province = "all"; render(); });
    $("open-limitations").addEventListener("click", () => $("limits-dialog").showModal());
    $("close-limitations").addEventListener("click", () => $("limits-dialog").close());
    $("fullscreen").addEventListener("click", async () => { try { if (!document.fullscreenElement) await document.documentElement.requestFullscreen(); else await document.exitFullscreen(); } catch (_) {} });
    renderStaticInformation();
    render();
  })();
  </script>
</body>
</html>
'''
