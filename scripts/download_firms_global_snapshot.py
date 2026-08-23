"""Download a frozen global NASA FIRMS NRT daily snapshot.

The browser receives only country-level aggregates derived from these files.
Raw NRT text files remain local and are ignored by Git.  Earthdata credentials
are read through earthaccess/netrc; no token is written to the project.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "data" / "raw" / "firms" / "nrt_global"
QUALITY_ROOT = ROOT / "outputs" / "quality" / "firms_global_nrt"

SOURCES: dict[str, str] = {
    "MODIS": "modis-c6.1/Global/MODIS_C6_1_Global_MCD14DL_NRT_{year}{doy}.txt",
    "VIIRS_NOAA20": "noaa-20-viirs-c2/Global/J1_VIIRS_C2_Global_VJ114IMGTDL_NRT_{year}{doy}.txt",
    "VIIRS_NOAA21": "noaa-21-viirs-c2/Global/J2_VIIRS_C2_Global_VJ214IMGTDL_NRT_{year}{doy}.txt",
    "VIIRS_SNPP": "suomi-npp-viirs-c2/Global/SUOMI_VIIRS_C2_Global_VNP14IMGTDL_NRT_{year}{doy}.txt",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_snapshot(snapshot_date: date, *, overwrite: bool = False) -> dict[str, Any]:
    try:
        import earthaccess
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise RuntimeError("earthaccess is required; use the bundled research Python runtime") from exc

    day_dir = RAW_ROOT / snapshot_date.isoformat()
    day_dir.mkdir(parents=True, exist_ok=True)
    auth = earthaccess.login(strategy="netrc", persist=False)
    if not auth.authenticated:
        raise RuntimeError("Earthdata Login did not authenticate")
    session = auth.get_session()
    year = snapshot_date.year
    doy = snapshot_date.strftime("%j")
    base = "https://nrt3.modaps.eosdis.nasa.gov/archive/FIRMS/"
    retrieved_at = datetime.now(timezone.utc).isoformat()
    files: list[dict[str, Any]] = []

    for sensor, template in SOURCES.items():
        relative = template.format(year=year, doy=doy)
        url = base + relative
        destination = day_dir / Path(relative).name
        temporary = destination.with_suffix(destination.suffix + ".part")
        if destination.exists() and not overwrite:
            payload_hash = sha256(destination)
            byte_count = destination.stat().st_size
        else:
            response = session.get(url, stream=True, timeout=180)
            response.raise_for_status()
            with temporary.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
            temporary.replace(destination)
            payload_hash = sha256(destination)
            byte_count = destination.stat().st_size
        files.append({
            "sensor": sensor,
            "url": url,
            "path": destination.relative_to(ROOT).as_posix(),
            "bytes": byte_count,
            "sha256": payload_hash,
        })

    metadata = {
        "schema_version": "firms-global-nrt-snapshot/v1",
        "status": "downloaded_pending_aggregation",
        "snapshot_date": snapshot_date.isoformat(),
        "date_basis": "NASA FIRMS portal acquisition date; NRT daily file",
        "retrieved_at_utc": retrieved_at,
        "source": "NASA FIRMS NRT global daily text files",
        "source_url": base,
        "sensors": files,
        "raw_records_embedded": False,
        "latest_day_guardrail": "Use a closed UTC day; do not treat an in-progress portal day as complete.",
    }
    QUALITY_ROOT.mkdir(parents=True, exist_ok=True)
    metadata_path = QUALITY_ROOT / f"{snapshot_date.isoformat()}.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", type=date.fromisoformat, required=True, help="closed UTC date, YYYY-MM-DD")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    result = download_snapshot(args.date, overwrite=args.overwrite)
    total_bytes = sum(int(item["bytes"]) for item in result["sensors"])
    print(f"Downloaded {len(result['sensors'])} global FIRMS files for {result['snapshot_date']} ({total_bytes:,} bytes).")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
