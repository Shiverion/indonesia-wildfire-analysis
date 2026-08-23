"""Download final CHIRPS v3 daily RNL COGs without an account.

CHIRPS files are global 0.05-degree rasters; the Kalimantan bounding box is
applied during downstream extraction, not by the provider URL. This helper
downloads one date range at a time, skips non-empty existing files, and writes
private SHA-256 receipts without embedding raster data in the browser bundle.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/daily/final/rnl/cogs"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download_one(day: date, output_root: Path, dry_run: bool) -> dict[str, object]:
    year = day.year
    filename = f"chirps-v3.0.rnl.{day:%Y.%m.%d}.cog"
    url = f"{BASE_URL}/{year}/{filename}"
    target = output_root / str(year) / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 0:
        return {
            "date": day.isoformat(),
            "status": "existing",
            "url": url,
            "path": target.relative_to(ROOT).as_posix(),
            "size_bytes": target.stat().st_size,
            "sha256": sha256(target),
        }
    if dry_run:
        return {"date": day.isoformat(), "status": "dry_run", "url": url, "target": target.relative_to(ROOT).as_posix()}
    request = Request(url, headers={"User-Agent": "Indonesia-Wildfire-Analysis/1.0"})
    try:
        with urlopen(request, timeout=180) as response, target.open("wb") as handle:
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                handle.write(block)
    except (HTTPError, URLError, TimeoutError) as exc:
        if target.exists() and target.stat().st_size == 0:
            target.unlink()
        return {"date": day.isoformat(), "status": "download_error", "url": url, "error": str(exc)}
    return {
        "date": day.isoformat(),
        "status": "downloaded",
        "url": url,
        "path": target.relative_to(ROOT).as_posix(),
        "size_bytes": target.stat().st_size,
        "sha256": sha256(target),
    }


def run(start: date, end: date, output_root: Path, limit: int | None, dry_run: bool) -> dict[str, object]:
    if start > end:
        raise SystemExit("--start must not be after --end")
    days: list[date] = []
    cursor = start
    while cursor <= end:
        days.append(cursor)
        cursor += timedelta(days=1)
    if limit is not None:
        days = days[:limit]
    records = [download_one(day, output_root, dry_run) for day in days]
    manifest = {
        "schema_version": "chirps-v3-download/v1",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": BASE_URL,
        "product": "CHIRPS v3 FINAL RNL daily COG",
        "temporal": [start.isoformat(), end.isoformat()],
        "study_bbox": [109.0, -5.0, 120.0, 8.0],
        "dry_run": dry_run,
        "records": records,
        "timing_rule": "Download support only; derive antecedent rainfall before each event cutoff downstream.",
    }
    manifest_path = output_root / "download_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Downloaded/verified {sum(item.get('status') in {'downloaded', 'existing'} for item in records)} of {len(records)} requested CHIRPS dates")
    print(f"Manifest: {manifest_path.relative_to(ROOT)}")
    if any(item.get("status") == "download_error" for item in records):
        raise SystemExit(2)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, type=date.fromisoformat)
    parser.add_argument("--end", required=True, type=date.fromisoformat)
    parser.add_argument("--limit", type=int, default=None, help="limit dates for a smoke test")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-root", type=Path, default=ROOT / "data" / "raw" / "chirps")
    args = parser.parse_args()
    run(args.start, args.end, args.output_root, args.limit, args.dry_run)


if __name__ == "__main__":
    main()
