"""Configuration and data-gate validation for the frozen research protocol."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .quality import asset_local_evidence, sha256_file, workspace_path


REQUIRED_ASSET_FIELDS = {
    "id",
    "purpose",
    "source_url",
    "access_class",
    "licence_or_terms",
    "expected_local_path",
    "status",
    "required_for",
}

CORE_PHASE_1_ASSETS = {
    "viirs_snpp_active_fire_and_geolocation",
    "era5_land",
    "chirps_v3",
    "mapbiomas_indonesia_collection_4_1",
    "mod13q1_061",
    "historical_access_assets",
    "peat_and_drainage_assets",
}


def _provenance_evidence(root: Path, asset: dict) -> dict:
    """Check a ready asset has a local acquisition record as well as payload bytes."""
    if asset.get("status") != "ready":
        return {"provenance_ready": False, "reason": "asset_not_marked_ready"}
    provenance_path = asset.get("provenance_path")
    if not isinstance(provenance_path, str) or not provenance_path:
        return {"provenance_ready": False, "reason": "missing_provenance_path"}
    try:
        path = workspace_path(root, provenance_path)
    except ValueError as exc:
        return {"provenance_ready": False, "reason": "invalid_provenance_path", "detail": str(exc)}
    if not path.is_file():
        return {"provenance_ready": False, "reason": "provenance_file_missing"}
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"provenance_ready": False, "reason": "provenance_invalid_json", "detail": str(exc)}
    required = {"source_url", "retrieved_at_utc"}
    missing = required - set(record)
    if missing:
        return {"provenance_ready": False, "reason": "provenance_missing_fields", "detail": sorted(missing)}
    if record["source_url"] != asset["source_url"]:
        return {"provenance_ready": False, "reason": "provenance_source_url_mismatch"}
    expected = workspace_path(root, asset["expected_local_path"])
    if expected.is_file() and "raw_sha256" in record:
        if record["raw_sha256"] != sha256_file(expected):
            return {"provenance_ready": False, "reason": "provenance_hash_mismatch"}
    elif expected.is_file():
        return {"provenance_ready": False, "reason": "provenance_missing_raw_sha256"}
    elif expected.is_dir():
        # Download manifests use ``records`` while standalone provenance
        # receipts use ``files``.  Both are accepted when each entry carries
        # a workspace-relative path and SHA-256 receipt.
        entries = record.get("files") or record.get("records")
        if not isinstance(entries, list) or not entries:
            return {"provenance_ready": False, "reason": "provenance_missing_file_inventory"}
        seen_paths: set[str] = set()
        for entry in entries:
            if not isinstance(entry, dict):
                return {"provenance_ready": False, "reason": "provenance_invalid_file_inventory"}
            raw_path = entry.get("raw_path") or entry.get("path")
            raw_sha256 = entry.get("raw_sha256") or entry.get("sha256")
            if not isinstance(raw_path, str) or not isinstance(raw_sha256, str):
                return {"provenance_ready": False, "reason": "provenance_file_entry_missing_path_or_hash"}
            try:
                file_path = workspace_path(root, raw_path)
                file_path.relative_to(expected.resolve())
            except ValueError:
                return {"provenance_ready": False, "reason": "provenance_file_entry_outside_expected_path"}
            if not file_path.is_file():
                return {"provenance_ready": False, "reason": "provenance_file_entry_missing"}
            if file_path.as_posix() in seen_paths:
                return {"provenance_ready": False, "reason": "provenance_file_entry_duplicate"}
            seen_paths.add(file_path.as_posix())
            if sha256_file(file_path) != raw_sha256:
                return {"provenance_ready": False, "reason": "provenance_file_entry_hash_mismatch"}
    return {"provenance_ready": True, "provenance_path": provenance_path}


def validate_protocol(root: Path) -> dict:
    config_path = root / "config" / "study.json"
    manifest_path = root / "data" / "manifests" / "assets.json"
    errors: list[str] = []
    warnings: list[str] = []
    config = json.loads(config_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    for key in ("study_id", "geography", "projection", "time_split", "vegetation", "enso", "monitoring"):
        if key not in config:
            errors.append(f"study configuration missing {key!r}")
    if config.get("projection") != "EPSG:6933":
        errors.append("primary grid projection must remain EPSG:6933")
    if config.get("time_split", {}).get("locked_retrospective_test") != [2024, 2025]:
        errors.append("locked retrospective test must remain [2024, 2025]")
    if "conditioned out" not in config.get("enso", {}).get("exact_overpass_role", ""):
        errors.append("ENSO exact-overpass role must state that its main effect is conditioned out")
    if "exclude" not in config.get("vegetation", {}).get("roles", {}).get("total_accessibility", ""):
        errors.append("total-accessibility vegetation rule must exclude dynamic mediator variables")

    assets = manifest.get("assets", [])
    seen_ids: set[str] = set()
    phase_1_gate_rows: list[dict] = []
    for asset in assets:
        missing = REQUIRED_ASSET_FIELDS - set(asset)
        if missing:
            errors.append(f"asset {asset.get('id', '<unknown>')} missing fields: {sorted(missing)}")
            continue
        if asset["id"] in seen_ids:
            errors.append(f"duplicate asset ID {asset['id']!r}")
        seen_ids.add(asset["id"])
        try:
            local_evidence = asset_local_evidence(root, asset)
        except ValueError as exc:
            errors.append(f"asset {asset['id']!r} has invalid local evidence path: {exc}")
            continue
        provenance = _provenance_evidence(root, asset)
        if asset["id"] in CORE_PHASE_1_ASSETS:
            gate_ready = local_evidence["gate_ready"] and provenance["provenance_ready"]
            phase_1_gate_rows.append(
                {
                    "asset_id": asset["id"],
                    "manifest_status": asset["status"],
                    "expected_local_path": asset["expected_local_path"],
                    "local_path_exists": local_evidence["local_path_exists"],
                    "payload_file_count": local_evidence["payload_file_count"],
                    "provenance_ready": provenance["provenance_ready"],
                    "gate_ready": gate_ready,
                }
            )
        if asset["id"] == "noaa_cpc_roni_v6" and not local_evidence["locally_populated"]:
            warnings.append("RONI has not been fetched; run `fetch-roni` before any ENSO panel work")
        if asset["status"] == "ready" and not provenance["provenance_ready"]:
            errors.append(
                f"asset {asset['id']!r} is marked ready but has invalid provenance: {provenance['reason']}"
            )

    missing_core = CORE_PHASE_1_ASSETS - seen_ids
    if missing_core:
        errors.append(f"manifest missing core Phase 1 assets: {sorted(missing_core)}")
    phase_1_ready = bool(phase_1_gate_rows) and all(row["gate_ready"] for row in phase_1_gate_rows)
    if not phase_1_ready:
        warnings.append("Phase 1 is not ready; matched-risk-set construction and effect estimation are blocked")

    report = {
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "study_id": config.get("study_id"),
        "config_sha256": sha256_file(config_path),
        "manifest_sha256": sha256_file(manifest_path),
        "errors": errors,
        "warnings": warnings,
        "phase_1_gates": phase_1_gate_rows,
        "phase_1_ready": phase_1_ready,
        "result": "pass" if not errors else "fail",
    }
    return report


def write_validation_report(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
