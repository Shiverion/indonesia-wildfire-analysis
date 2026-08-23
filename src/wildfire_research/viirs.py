"""Index paired S-NPP VIIRS active-fire/geolocation granules.

This module deliberately stops one step before the scientific denominator.  A
VNP14 file contains detections, while the paired VNP03 file provides the
geolocation needed to reconstruct the swath opportunity.  Until VNP03 pixels
are decoded, quality-screened, and intersected with the analysis grid, a pair
is only *eligible for* opportunity processing; it is not a negative or a
zero-fire observation.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


GRANULE_RE = re.compile(
    r"^VNP(?P<kind>14|03)IMG\.A(?P<year>\d{4})(?P<doy>\d{3})\."
    r"(?P<hhmm>\d{4})\.002(?:\.|$)"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_granule_name(name: str) -> dict[str, Any] | None:
    """Parse a VNP14/VNP03 Collection 002 basename into its pair key."""

    match = GRANULE_RE.match(name)
    if match is None:
        return None
    year = int(match.group("year"))
    doy = int(match.group("doy"))
    hhmm = match.group("hhmm")
    hour, minute = int(hhmm[:2]), int(hhmm[2:])
    if not 1 <= doy <= 366 or not 0 <= hour <= 23 or not 0 <= minute <= 59:
        return None
    try:
        acquired = datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(
            days=doy - 1, hours=hour, minutes=minute
        )
    except ValueError:
        return None
    return {
        "kind": f"VNP{match.group('kind')}IMG",
        "year": year,
        "doy": doy,
        "hhmm": hhmm,
        "pair_key": f"{year:04d}{doy:03d}.{hhmm}",
        "acquisition_utc": acquired.isoformat().replace("+00:00", "Z"),
    }


def _file_record(path: Path, parsed: dict[str, Any], root: Path, *, hash_files: bool) -> dict[str, Any]:
    record: dict[str, Any] = {
        "path": path.relative_to(root).as_posix(),
        "name": path.name,
        "size_bytes": path.stat().st_size,
    }
    if hash_files:
        record["sha256"] = _sha256(path)
    return {**parsed, **record}


def index_pairs(root: Path, *, hash_files: bool = False) -> dict[str, Any]:
    """Build a deterministic pair index without treating detections as negatives."""

    viirs_root = root / "data" / "raw" / "viirs"
    by_kind: dict[str, dict[str, list[dict[str, Any]]]] = {"VNP14IMG": {}, "VNP03IMG": {}}
    ignored_files: list[str] = []
    for kind in by_kind:
        directory = viirs_root / kind
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.nc")):
            parsed = parse_granule_name(path.name)
            if parsed is None or parsed["kind"] != kind:
                ignored_files.append(path.relative_to(root).as_posix())
                continue
            by_kind[kind].setdefault(parsed["pair_key"], []).append(
                _file_record(path, parsed, root, hash_files=hash_files)
            )

    rows: list[dict[str, Any]] = []
    for pair_key in sorted(set(by_kind["VNP14IMG"]) | set(by_kind["VNP03IMG"])):
        fires = by_kind["VNP14IMG"].get(pair_key, [])
        geolocations = by_kind["VNP03IMG"].get(pair_key, [])
        if len(fires) == 1 and len(geolocations) == 1:
            pair_status = "paired"
            opportunity_status = "eligible_for_geolocation_processing"
        elif not fires:
            pair_status = "missing_vnp14"
            opportunity_status = "blocked_unpaired"
        elif not geolocations:
            pair_status = "missing_vnp03"
            opportunity_status = "blocked_unpaired"
        else:
            pair_status = "ambiguous_duplicate"
            opportunity_status = "blocked_ambiguous"
        representative = (fires or geolocations)[0]
        rows.append(
            {
                "pair_key": pair_key,
                "acquisition_utc": representative["acquisition_utc"],
                "year": representative["year"],
                "doy": representative["doy"],
                "hhmm": representative["hhmm"],
                "vnp14_count": len(fires),
                "vnp03_count": len(geolocations),
                "vnp14_path": fires[0]["path"] if len(fires) == 1 else "",
                "vnp03_path": geolocations[0]["path"] if len(geolocations) == 1 else "",
                "pair_status": pair_status,
                "outcome_status": "active_fire_product_present" if fires else "no_vnp14_product",
                "opportunity_status": opportunity_status,
                # This is intentionally never inferred from a missing VNP14.
                "negative_frame_status": "not_built",
            }
        )

    counts = Counter(row["pair_status"] for row in rows)
    manifest_path = viirs_root / "download_manifest.json"
    manifest_sha256 = _sha256(manifest_path) if manifest_path.is_file() else None
    manifest_scope: dict[str, Any] = {}
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest_scope = {
                "retrieved_at_utc": manifest.get("retrieved_at_utc"),
                "temporal": manifest.get("temporal"),
                "bounding_box": manifest.get("bounding_box"),
            }
        except json.JSONDecodeError:
            manifest_scope = {"invalid_json": True}

    return {
        "schema_version": "viirs-pair-opportunity/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "root": "data/raw/viirs",
            "manifest": "data/raw/viirs/download_manifest.json",
            "manifest_sha256": manifest_sha256,
            **manifest_scope,
        },
        "summary": {
            "vnp14_files": sum(len(values) for values in by_kind["VNP14IMG"].values()),
            "vnp03_files": sum(len(values) for values in by_kind["VNP03IMG"].values()),
            "pair_rows": len(rows),
            "paired_rows": counts.get("paired", 0),
            "unpaired_or_ambiguous_rows": len(rows) - counts.get("paired", 0),
            "ignored_files": len(ignored_files),
        },
        "denominator_ready": False,
        "negative_frame": {
            "status": "not_built",
            "reason": (
                "VNP03 geolocation and VNP14 quality/status arrays must be decoded; "
                "valid observed pixels with no VNP14 detection can then be labelled "
                "negative only after cloud/quality and grid-overlap filters."
            ),
            "required_next_step": "decode_geolocation_and_build_valid_observation_pixels",
        },
        "ignored_files": ignored_files,
        "rows": rows,
    }


def write_index(root: Path, *, output_dir: Path | None = None, quality_path: Path | None = None, hash_files: bool = False) -> dict[str, Any]:
    """Write CSV/JSON pair-index artifacts and return the JSON payload."""

    payload = index_pairs(root, hash_files=hash_files)
    output_dir = output_dir or root / "data" / "derived" / "viirs"
    quality_path = quality_path or root / "outputs" / "quality" / "viirs_pair_index.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    quality_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "viirs_pair_index.csv"
    fields = [
        "pair_key", "acquisition_utc", "year", "doy", "hhmm", "vnp14_count", "vnp03_count",
        "vnp14_path", "vnp03_path", "pair_status", "outcome_status", "opportunity_status",
        "negative_frame_status",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(payload["rows"])
    payload["outputs"] = {
        "csv": csv_path.relative_to(root).as_posix(),
        "quality_json": quality_path.relative_to(root).as_posix(),
    }
    quality_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload
