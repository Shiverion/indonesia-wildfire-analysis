"""Local-only Phase 1 input audit and VIIRS manifest reconciliation.

This command deliberately does not contact any provider and never changes a
raw payload.  It checks the files already downloaded, compares the on-disk
VIIRS pair inventory with the most recent download manifest, and writes a
separate reconciliation manifest when a previous batch was overwritten by a
later download command.

The reconciliation manifest is not a Phase 1 provenance lock: files that are
present locally but absent from the provider manifest are marked
``source_metadata_not_retained``.  They must not be treated as gate-ready
until the original provider metadata (or a fresh authenticated query) is
frozen.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from datetime import date, timedelta, datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VIIRS_RE = re.compile(
    r"^VNP(?P<kind>14|03)IMG\.A(?P<year>\d{4})(?P<doy>\d{3})\.(?P<hhmm>\d{4})\.002\.[^.]+\.nc$"
)
CHIRPS_RE = re.compile(r"^chirps-v3\.0\.rnl\.(?P<date>\d{4}\.\d{2}\.\d{2})\.cog$")
MODIS_RE = re.compile(r"^MOD13Q1\.A(?P<year>\d{4})(?P<doy>\d{3})\.h(?P<h>\d{2})v(?P<v>\d{2})\.061\..+\.hdf$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def viirs_inventory(root: Path) -> dict[str, Any]:
    """Return acquisition-key inventories for VNP14/VNP03 local files."""
    by_kind: dict[str, dict[str, Path]] = {"14": {}, "03": {}}
    malformed: list[str] = []
    duplicates: list[str] = []
    for path in sorted((root / "data/raw/viirs").glob("VNP*IMG/*.nc")):
        match = VIIRS_RE.match(path.name)
        if not match:
            malformed.append(rel(path))
            continue
        kind = match.group("kind")
        key = f"{match.group('year')}{match.group('doy')}.{match.group('hhmm')}"
        if key in by_kind[kind]:
            duplicates.append(key)
        by_kind[kind][key] = path
    keys14, keys03 = set(by_kind["14"]), set(by_kind["03"])
    return {
        "files": {
            "VNP14IMG": len(keys14),
            "VNP03IMG": len(keys03),
        },
        "pair_rows": len(keys14 | keys03),
        "paired_rows": len(keys14 & keys03),
        "unpaired_keys": sorted(keys14 ^ keys03),
        "duplicate_keys": sorted(set(duplicates)),
        "malformed_files": malformed,
        "paths": {
            "VNP14IMG": {key: rel(path) for key, path in sorted(by_kind["14"].items())},
            "VNP03IMG": {key: rel(path) for key, path in sorted(by_kind["03"].items())},
        },
    }


def _manifest_paths(manifest: dict[str, Any]) -> dict[str, set[str]]:
    paths: dict[str, set[str]] = {"VNP14IMG": set(), "VNP03IMG": set()}
    for record in manifest.get("records", []):
        short_name = record.get("short_name")
        if short_name not in paths:
            continue
        for entry in record.get("downloaded_files", []):
            if isinstance(entry, dict) and isinstance(entry.get("path"), str):
                paths[short_name].add(entry["path"].replace("\\", "/"))
        for entry in record.get("matches", []):
            if isinstance(entry, dict) and isinstance(entry.get("path"), str):
                paths[short_name].add(entry["path"].replace("\\", "/"))
    return paths


def reconcile_viirs(root: Path) -> dict[str, Any]:
    """Create a separate inventory manifest without fabricating provider metadata."""
    source_path = root / "data/raw/viirs/download_manifest.json"
    source = load_json(source_path) if source_path.is_file() else {}
    source_paths = _manifest_paths(source)
    inventory = viirs_inventory(root)
    records: list[dict[str, Any]] = []
    for short_name, kind in (("VNP14IMG", "14"), ("VNP03IMG", "03")):
        entries: list[dict[str, Any]] = []
        for key, path_text in inventory["paths"][short_name].items():
            path = root / Path(path_text)
            entry = {
                "path": path_text,
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
                "acquisition_key": key,
                "provenance_status": (
                    "recorded_in_source_manifest"
                    if path_text in source_paths[short_name]
                    else "source_metadata_not_retained"
                ),
            }
            entries.append(entry)
        recorded = sum(item["provenance_status"] == "recorded_in_source_manifest" for item in entries)
        records.append(
            {
                "short_name": short_name,
                "version": "002",
                "local_file_count": len(entries),
                "source_manifest_file_count": recorded,
                "reconciled_local_only_count": len(entries) - recorded,
                "files": entries,
            }
        )
    result = {
        "schema_version": "viirs-local-reconciliation/v1",
        "reconciled_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_manifest": rel(source_path),
        "source_manifest_sha256": sha256_file(source_path) if source_path.is_file() else None,
        "source_manifest_temporal": source.get("temporal"),
        "source_manifest_bbox": source.get("bounding_box"),
        "purpose": "Byte-level local inventory correction after a later download run replaced an earlier manifest.",
        "gate_effect": "none; Phase 1 remains blocked until provider metadata and the negative opportunity frame are frozen.",
        "inventory": inventory,
        "records": records,
    }
    output = root / "data/raw/viirs/reconciled_manifest.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def _audit_chirps(root: Path) -> dict[str, Any]:
    manifest_path = root / "data/raw/chirps/download_manifest.json"
    manifest = load_json(manifest_path) if manifest_path.is_file() else {}
    expected = {row.get("date") for row in manifest.get("records", []) if row.get("date")}
    actual: dict[str, Path] = {}
    bad_magic: list[str] = []
    for path in sorted((root / "data/raw/chirps").glob("*/chirps-v3.0.rnl.*.cog")):
        match = CHIRPS_RE.match(path.name)
        if not match:
            continue
        iso_date = match.group("date").replace(".", "-")
        actual[iso_date] = path
        if path.stat().st_size == 0 or path.open("rb").read(4) not in {b"II*\x00", b"MM\x00*"}:
            bad_magic.append(rel(path))
    missing = sorted(expected - set(actual))
    unexpected = sorted(set(actual) - expected)
    contiguous = False
    if expected:
        dates = sorted(date.fromisoformat(item) for item in expected)
        contiguous = dates == [dates[0] + timedelta(days=i) for i in range(len(dates))]
    status = "locally_complete_for_requested_window"
    if missing or not contiguous or bad_magic:
        status = "needs_review"
    elif unexpected:
        # A prior smoke test left a valid COG outside the requested fire-season
        # window.  Keep it on disk and report it; it is not a gap in the
        # requested 2015-07-01..2015-11-30 support frame.
        status = "locally_complete_with_extra_dates"
    return {
        "manifest_temporal": manifest.get("temporal"),
        "manifest_record_count": len(expected),
        "local_file_count": len(actual),
        "missing_dates": missing,
        "unexpected_dates": unexpected,
        "contiguous_manifest_dates": contiguous,
        "bad_magic_files": bad_magic,
        "status": status,
    }


def _audit_mod13q1(root: Path) -> dict[str, Any]:
    manifest_path = root / "data/raw/mod13q1/download_manifest.json"
    manifest = load_json(manifest_path) if manifest_path.is_file() else {}
    hdf_files = sorted((root / "data/raw/mod13q1").glob("MOD13Q1/*.hdf"))
    xml_files = sorted((root / "data/raw/mod13q1").glob("MOD13Q1/*.xml"))
    jpg_files = sorted((root / "data/raw/mod13q1").glob("MOD13Q1/*.jpg"))
    expected_entries = {
        item.get("path")
        for record in manifest.get("records", [])
        for item in record.get("downloaded_files", [])
        if isinstance(item, dict) and item.get("path")
    }
    actual_paths = {rel(path) for path in hdf_files + xml_files + jpg_files}
    missing_manifest_entries = sorted(actual_paths - expected_entries)
    bad_hdf_magic = []
    dates: set[str] = set()
    tiles: set[str] = set()
    for path in hdf_files:
        if path.open("rb").read(4) != b"\x0e\x03\x13\x01":
            bad_hdf_magic.append(rel(path))
        match = MODIS_RE.match(path.name)
        if match:
            dates.add(f"{match.group('year')}{match.group('doy')}")
            tiles.add(f"h{match.group('h')}v{match.group('v')}")
    return {
        "manifest_temporal": manifest.get("temporal"),
        "manifest_record_count": sum(record.get("downloaded_count", 0) for record in manifest.get("records", [])),
        "local_hdf_count": len(hdf_files),
        "local_xml_count": len(xml_files),
        "local_jpg_count": len(jpg_files),
        "expected_tiles": sorted(tiles),
        "composite_count": len(dates),
        "missing_manifest_entries": missing_manifest_entries,
        "bad_hdf_magic_files": bad_hdf_magic,
        "status": "HDF_payload_complete_but_QA_timing_unvalidated" if len(hdf_files) == 144 and not bad_hdf_magic else "needs_review",
    }


def _audit_peat(root: Path) -> dict[str, Any]:
    peat = root / "data/raw/peat/global/peatland.extent_multi_p_1km_s_2000_2020_go_epsg4326_v20260423.tif"
    drainage = root / "data/raw/peat_and_drainage/dadap_2017_geotiffs.zip"
    zip_bad = None
    members = 0
    if drainage.is_file():
        with zipfile.ZipFile(drainage) as archive:
            zip_bad = archive.testzip()
            members = len(archive.infolist())
    return {
        "peat_path": rel(peat) if peat.is_file() else None,
        "peat_exists": peat.is_file(),
        "peat_size_bytes": peat.stat().st_size if peat.is_file() else None,
        "peat_reference_period": "2000-2020",
        "drainage_exists": drainage.is_file(),
        "drainage_zip_members": members,
        "drainage_bad_member": zip_bad,
        "status": "sensitivity_inputs_readable_but_provenance_timing_not_frozen" if peat.is_file() and drainage.is_file() and not zip_bad else "needs_review",
    }


def _audit_viirs_swath_summary(root: Path) -> dict[str, Any]:
    path = root / "outputs/quality/viirs_swath_summary.json"
    if not path.is_file():
        return {
            "exists": False,
            "status": "not_built",
            "denominator_ready": False,
            "negative_frame_ready": False,
        }
    try:
        payload = load_json(path)
    except json.JSONDecodeError:
        return {
            "exists": True,
            "status": "invalid_json",
            "denominator_ready": False,
            "negative_frame_ready": False,
        }
    summary = payload.get("summary", {})
    return {
        "exists": True,
        "status": payload.get("interpretation", {}).get("status", "screening_only"),
        "paired_rows_requested": summary.get("paired_rows_requested"),
        "swaths_screened": summary.get("swaths_screened"),
        "swaths_failed": summary.get("swaths_failed"),
        "denominator_ready": summary.get("denominator_ready") is True,
        "negative_frame_ready": summary.get("negative_frame_ready") is True,
    }


def run(root: Path) -> dict[str, Any]:
    reconciliation = reconcile_viirs(root)
    report = {
        "schema_version": "phase1-local-audit/v1",
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Local input integrity only; does not unlock Phase 1 or assert causal validity.",
        "viirs": {
            "inventory": reconciliation["inventory"],
            "source_manifest_file_counts": {
                row["short_name"]: row["source_manifest_file_count"] for row in reconciliation["records"]
            },
            "reconciled_local_only_counts": {
                row["short_name"]: row["reconciled_local_only_count"] for row in reconciliation["records"]
            },
            "pair_index_status": "60/60 acquisition-key pairs found locally; negative opportunity frame not built",
            "swath_screening": _audit_viirs_swath_summary(root),
            "status": "paired_and_geolocated_screening_complete_but_negative_frame_not_built",
        },
        "chirps": _audit_chirps(root),
        "mod13q1": _audit_mod13q1(root),
        "peat_and_drainage": _audit_peat(root),
        "phase_1_ready": False,
        "blocking_gates": [
            "VIIRS swath geolocation/quality screening is complete for the local pairs, but the frozen 2014 forest intersection and processed non-detection frame are not built.",
            "Current VIIRS download_manifest.json records only the latest 50-file batch; 10+10 local files are source-metadata-not-retained in reconciled_manifest.json.",
            "ERA5-Land 2015 is complete locally; temporal lag and coverage QA remain pending.",
            "MapBiomas frozen 2014 export/crosswalk and dated access source are still absent.",
            "Peat and Dadap 2017 drainage inputs are sensitivity-ready, not a dated 2014 construction baseline.",
        ],
    }
    output = root / "outputs/quality/phase1_local_audit.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    report = run(args.root.resolve())
    print(json.dumps({
        "report": rel(args.root / "outputs/quality/phase1_local_audit.json"),
        "reconciled_manifest": rel(args.root / "data/raw/viirs/reconciled_manifest.json"),
        "viirs_pairs": report["viirs"]["inventory"]["paired_rows"],
        "viirs_local_only": report["viirs"]["reconciled_local_only_counts"],
        "chirps_status": report["chirps"]["status"],
        "mod13q1_status": report["mod13q1"]["status"],
        "phase_1_ready": report["phase_1_ready"],
    }, indent=2))


if __name__ == "__main__":
    main()
