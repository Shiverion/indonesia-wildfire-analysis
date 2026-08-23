#!/usr/bin/env python3
"""Resume ERA5-Land downloads for the registered 2015-2025 study window.

Requests are sequential and monthly so a failed month can be resumed without
repeating completed files. The existing 2015 files are reused; the manifest is
merged append-only by year/month.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from download_era5_land import run  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=2015)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.start_year > args.end_year:
        parser.error("--start-year must not exceed --end-year")
    for year in range(args.start_year, args.end_year + 1):
        run(year, [f"{month:02d}" for month in range(1, 13)], ROOT / "data" / "raw" / "era5_land", args.dry_run)
    manifest = ROOT / "data" / "raw" / "era5_land" / "download_manifest.json"
    if manifest.is_file():
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        print(json.dumps({"manifest": manifest.relative_to(ROOT).as_posix(), "record_count": len(payload.get("records", [])), "dry_run": args.dry_run}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
