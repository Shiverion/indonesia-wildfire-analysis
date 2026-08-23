"""Authenticated NASA Earthdata downloads for the condition-phase inputs.

The script uses ``earthaccess`` so credentials stay local.  It never accepts
or stores a password on the command line.  Start with ``--dry-run`` or
``--limit 1`` before requesting a multi-year archive.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BBOX = (109.0, -5.0, 120.0, 8.0)  # Kalimantan study extent, lon/lat

PRODUCTS = {
    "viirs": (
        ("VNP14IMG", "002"),
        ("VNP03IMG", "002"),
    ),
    "mod13q1": (("MOD13Q1", "061"),),
    "hls": (("HLSL30", "002"), ("HLSS30", "002")),
}
LAADS_ARCHIVE = "https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/5200/VNP03IMG"
VNP14_GRANULE_RE = re.compile(r"VNP14IMG\.A(?P<year>\d{4})(?P<doy>\d{3})\.(?P<hhmm>\d{4})\.002(?:\.|$)")
VNP03_FILE_RE_TEMPLATE = "VNP03IMG.A{year}{doy}.{hhmm}.002."


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _parse_date(value: str) -> str:
    return datetime.strptime(value, "%Y-%m-%d").date().isoformat()


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _download_laads_geolocation(auth: Any, vnp14_granule: Any, target: Path, dry_run: bool) -> dict[str, Any]:
    """Find and optionally download the matching VNP03IMG LAADS file.

    VNP03IMG.002 is visible in the LAADS directory archive but historical
    granules are not returned by the CMR query used for the VNP14 LPDAAC
    collection. We therefore match on the producer acquisition stamp
    (YYYYDDD.HHMM), then retain the exact LAADS filename and URL in the
    private manifest.
    """
    granule_ur = str(vnp14_granule.get("umm", {}).get("GranuleUR", ""))
    match = VNP14_GRANULE_RE.search(granule_ur)
    if not match:
        return {"status": "unmatched_vnp14_name", "vnp14_granule": granule_ur}
    year, doy, hhmm = match.group("year"), match.group("doy"), match.group("hhmm")
    directory_url = f"{LAADS_ARCHIVE}/{year}/{doy}/"
    session = auth.get_session()
    response = session.get(directory_url, timeout=60)
    def access_error(exc: Exception, status_code: int, final_url: str, filename: str | None = None) -> dict[str, Any]:
        resolution_url = parse_qs(urlparse(final_url).query).get("resolution_url", [None])[0]
        item: dict[str, Any] = {
            "status": "laads_access_error",
            "vnp14_granule": granule_ur,
            "directory_url": directory_url,
            "http_status": status_code,
            "error": str(exc),
        }
        if filename:
            item["vnp03_filename"] = filename
            item["url"] = url
        if resolution_url:
            item.update({
                "resolution_url": resolution_url,
                "action": "Open resolution_url to pre-authorize the LAADS application, then rerun the same command.",
            })
        else:
            item["action"] = "Update the NASA Earthdata/LAADS profile required attributes, then rerun the same command."
        return item
    try:
        response.raise_for_status()
    except Exception as exc:
        return access_error(exc, response.status_code, response.url)
    prefix = VNP03_FILE_RE_TEMPLATE.format(year=year, doy=doy, hhmm=hhmm)
    candidates = sorted(set(re.findall(rf"{re.escape(prefix)}\d+\.nc", response.text)))
    if not candidates:
        return {
            "status": "vnp03_not_found",
            "vnp14_granule": granule_ur,
            "directory_url": directory_url,
        }
    filename = candidates[0]
    url = f"{directory_url}{filename}"
    output = target / filename
    record: dict[str, Any] = {
        "status": "dry_run" if dry_run else "downloaded",
        "vnp14_granule": granule_ur,
        "vnp03_filename": filename,
        "directory_url": directory_url,
        "url": url,
    }
    if not dry_run:
        if not output.exists() or output.stat().st_size == 0:
            with session.get(url, stream=True, timeout=120) as download_response:
                try:
                    download_response.raise_for_status()
                except Exception as exc:
                    return access_error(exc, download_response.status_code, download_response.url, filename)
                with output.open("wb") as handle:
                    for block in download_response.iter_content(chunk_size=1024 * 1024):
                        if block:
                            handle.write(block)
        record["path"] = _relative(output)
        record["sha256"] = _sha256(output)
        record["size_bytes"] = output.stat().st_size
    return record


def run(product: str, start: str, end: str, bbox: tuple[float, float, float, float], output_root: Path, limit: int | None, dry_run: bool) -> dict[str, Any]:
    try:
        import earthaccess
    except ImportError as exc:
        raise SystemExit("Install the NASA client first: python -m pip install earthaccess") from exc

    # Interactive login is safe: the password is entered by earthaccess and
    # is not included in shell history or this repository.
    # Reuse the credential entry created by the one-time interactive login.
    # If it is missing, earthaccess will fall back to its supported local
    # authentication methods and explain how to authenticate.
    auth = earthaccess.login(persist=False)
    records: list[dict[str, Any]] = []
    if product == "viirs":
        # VNP14 is indexed in CMR and can be spatially filtered. VNP03 is
        # paired from the LAADS archive using each VNP14 acquisition stamp.
        granules = earthaccess.search_data(
            short_name="VNP14IMG",
            version="002",
            bounding_box=bbox,
            temporal=(start, end),
            count=-1,
        )
        if limit is not None:
            granules = granules[:limit]
        vnp14_target = output_root / product / "VNP14IMG"
        vnp03_target = output_root / product / "VNP03IMG"
        vnp14_target.mkdir(parents=True, exist_ok=True)
        vnp03_target.mkdir(parents=True, exist_ok=True)
        print(f"VNP14IMG.002: {len(granules)} granules selected")
        downloaded_vnp14: list[str] = []
        if not dry_run and granules:
            downloaded_vnp14 = [str(Path(path)) for path in earthaccess.download(granules, str(vnp14_target))]
        records.append({
            "short_name": "VNP14IMG",
            "version": "002",
            "search_count": len(granules),
            "downloaded_count": len(downloaded_vnp14),
            "downloaded_files": [
                {"path": _relative(Path(path)), "sha256": _sha256(Path(path))}
                for path in downloaded_vnp14 if Path(path).is_file()
            ],
        })
        vnp03_matches = [_download_laads_geolocation(auth, granule, vnp03_target, dry_run) for granule in granules]
        records.append({
            "short_name": "VNP03IMG",
            "version": "002",
            "search_basis": "LAADS directory matched to VNP14 acquisition YYYYDDD.HHMM",
            "search_count": len(vnp03_matches),
            "downloaded_count": sum(item.get("status") == "downloaded" for item in vnp03_matches),
            "matches": vnp03_matches,
        })
    else:
        requested = PRODUCTS[product]
        for short_name, version in requested:
            print(f"Searching {short_name}.{version} from {start} through {end} …")
            granules = earthaccess.search_data(
                short_name=short_name,
                version=version,
                bounding_box=bbox,
                temporal=(start, end),
                count=-1,
            )
            if limit is not None:
                granules = granules[:limit]
            target = output_root / product / short_name
            target.mkdir(parents=True, exist_ok=True)
            print(f"  {len(granules)} granules selected; destination {target}")
            downloaded: list[str] = []
            if not dry_run and granules:
                paths = earthaccess.download(granules, str(target))
                downloaded = [str(Path(path)) for path in paths]
            records.append({
                "short_name": short_name,
                "version": version,
                "search_count": len(granules),
                "downloaded_count": len(downloaded),
                "downloaded_files": [
                    {"path": _relative(Path(path)), "sha256": _sha256(Path(path))}
                    for path in downloaded if Path(path).is_file()
                ],
            })
    manifest = {
        "schema_version": "earthdata-download/v1",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "product_group": product,
        "temporal": [start, end],
        "bounding_box": list(bbox),
        "dry_run": dry_run,
        "records": records,
        "timing_rule": "Search extent only; event-level prefire timing and VIIRS opportunity pairing are validated downstream.",
    }
    manifest_path = output_root / product / "download_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Manifest: {manifest_path.relative_to(ROOT)}")
    laads_errors = [
        item for record in records if record.get("short_name") == "VNP03IMG"
        for item in record.get("matches", []) if item.get("status") == "laads_access_error"
    ]
    if laads_errors:
        print("VNP03IMG pairing is blocked by LAADS account-profile requirements; see the manifest action.")
        raise SystemExit(2)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("product", choices=sorted(PRODUCTS), help="authenticated product group")
    parser.add_argument("--start", default="2015-01-01")
    parser.add_argument("--end", default="2025-12-31")
    parser.add_argument("--limit", type=int, default=None, help="limit granules per product for a test run")
    parser.add_argument("--dry-run", action="store_true", help="search and write the manifest without downloading")
    parser.add_argument("--output-root", type=Path, default=ROOT / "data" / "raw")
    args = parser.parse_args()
    start, end = _parse_date(args.start), _parse_date(args.end)
    if start > end:
        parser.error("--start must not be after --end")
    run(args.product, start, end, DEFAULT_BBOX, args.output_root, args.limit, args.dry_run)


if __name__ == "__main__":
    main()
