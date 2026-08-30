#!/usr/bin/env python3
"""Build the compact, coordinate-free Phase 3 analysis-data archive."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE_ROOT = ROOT / "publication" / "release"
MANIFEST_PATH = ROOT / "publication" / "data" / "manifest.json"
ARCHIVE_PATH = RELEASE_ROOT / "phase3-analysis-data-v1.zip"

FILES = {
    "data/derived/viirs/opportunity_frame.csv": ROOT
    / "data"
    / "derived"
    / "viirs"
    / "opportunity_frame.csv",
    "data/derived/phase3/mapbiomas_c41_transition_summary_private.csv": ROOT
    / "data"
    / "derived"
    / "phase3"
    / "mapbiomas_c41_transition_summary_private.csv",
    "config/phase3_registration.json": ROOT / "config" / "phase3_registration.json",
    "config/phase3_reporting_amendment_2026-08-30.json": ROOT
    / "config"
    / "phase3_reporting_amendment_2026-08-30.json",
    "config/mapbiomas_collection41_legend.json": ROOT
    / "config"
    / "mapbiomas_collection41_legend.json",
    "DATA_LICENSE.md": ROOT / "DATA_LICENSE.md",
    "publication/data/SOURCE_ATTRIBUTION.md": ROOT
    / "publication"
    / "data"
    / "SOURCE_ATTRIBUTION.md",
}

FORBIDDEN_COLUMN_PARTS = {"longitude", "latitude", "grid_row", "grid_col", "geometry"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def csv_shape(path: Path) -> tuple[int, list[str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        columns = next(reader)
        rows = sum(1 for _ in reader)
    return rows, columns


def validate_coordinate_free(path: Path, columns: list[str]) -> None:
    lowered = {column.lower() for column in columns}
    forbidden = sorted(lowered & FORBIDDEN_COLUMN_PARTS)
    if forbidden:
        raise ValueError(f"{path} contains forbidden coordinate columns: {forbidden}")


def build_manifest() -> dict:
    entries = []
    for archive_name, path in FILES.items():
        if not path.is_file():
            raise FileNotFoundError(path)
        entry = {
            "archive_path": archive_name,
            "source_path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        if path.suffix.lower() == ".csv":
            rows, columns = csv_shape(path)
            validate_coordinate_free(path, columns)
            entry.update({"row_count": rows, "column_count": len(columns), "columns": columns})
        entries.append(entry)
    return {
        "schema_version": "phase3-analysis-data-bundle/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Coordinate-free inputs sufficient to reproduce the registered Kalimantan Phase 3 models and publication diagnostics.",
        "contains_coordinates": False,
        "contains_credentials": False,
        "raw_provider_files_included": False,
        "files": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ARCHIVE_PATH)
    args = parser.parse_args()
    manifest = build_manifest()
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for archive_name, path in FILES.items():
            bundle.write(path, archive_name)
        bundle.writestr("publication/data/manifest.json", json.dumps(manifest, indent=2) + "\n")
        bundle.writestr(
            "BUNDLE_README.txt",
            "Phase 3 coordinate-free analysis inputs. Extract at the repository root, "
            "install requirements-analysis.txt, then run: python scripts/reproduce_publication.py\n",
        )
    print(
        json.dumps(
            {
                "status": "complete",
                "archive": str(output),
                "archive_bytes": output.stat().st_size,
                "archive_sha256": sha256_file(output),
                "file_count": len(FILES),
                "contains_coordinates": False,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
