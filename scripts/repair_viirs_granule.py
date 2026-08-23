#!/usr/bin/env python3
"""Repair one unreadable LAADS VNP03IMG granule without altering the canonical manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAADS_ROOT = "https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/5200/VNP03IMG"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def repair(pair_key: str) -> dict:
    match = re.fullmatch(r"(?P<year>\d{4})(?P<doy>\d{3})\.(?P<hhmm>\d{4})", pair_key)
    if not match:
        raise ValueError("pair key must have the form YYYYDDD.HHMM")
    year, doy, hhmm = match.group("year"), match.group("doy"), match.group("hhmm")
    target_dir = ROOT / "data" / "raw" / "viirs" / "VNP03IMG"
    matches = sorted(target_dir.glob(f"VNP03IMG.A{year}{doy}.{hhmm}.002.*.nc"))
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one local target, found {len(matches)}")
    target = matches[0]
    old_size = target.stat().st_size
    old_sha256 = sha256(target)
    rejected_dir = ROOT / "data" / "raw" / "viirs" / "_rejected"
    rejected_dir.mkdir(parents=True, exist_ok=True)
    rejected = rejected_dir / f"{target.name}.corrupt"
    if rejected.exists():
        raise RuntimeError(f"refusing to overwrite existing quarantine file: {rejected}")

    try:
        import earthaccess
        from netCDF4 import Dataset
    except ImportError as exc:
        raise SystemExit("Install earthaccess and netCDF4 in the analysis runtime first") from exc

    auth = earthaccess.login(persist=False)
    session = auth.get_session()
    directory_url = f"{LAADS_ROOT}/{year}/{doy}/"
    response = session.get(directory_url, timeout=60)
    response.raise_for_status()
    candidates = sorted(set(re.findall(rf"VNP03IMG\.A{year}{doy}\.{hhmm}\.002\.\d+\.nc", response.text)))
    if len(candidates) != 1:
        raise RuntimeError(f"expected one LAADS candidate, found {len(candidates)}: {candidates}")
    filename = candidates[0]
    url = f"{directory_url}{filename}"
    temporary = target.with_suffix(target.suffix + ".partial")
    shutil.move(str(target), str(rejected))
    try:
        with session.get(url, stream=True, timeout=180) as download_response:
            download_response.raise_for_status()
            with temporary.open("wb") as handle:
                for block in download_response.iter_content(chunk_size=1024 * 1024):
                    if block:
                        handle.write(block)
        with Dataset(temporary) as dataset:
            if "geolocation_data" not in dataset.groups:
                raise RuntimeError("replacement file lacks geolocation_data group")
        if temporary.name != target.name:
            replacement = target.parent / filename
        else:
            replacement = target
        temporary.replace(replacement)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        if not target.exists() and rejected.exists():
            shutil.move(str(rejected), str(target))
        raise

    receipt = {
        "schema_version": "viirs-granule-repair/v1",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "pair_key": pair_key,
        "product": "VNP03IMG.002",
        "directory_url": directory_url,
        "url": url,
        "quarantined_path": rejected.relative_to(ROOT).as_posix(),
        "quarantined_sha256": old_sha256,
        "quarantined_size_bytes": old_size,
        "replacement_path": replacement.relative_to(ROOT).as_posix(),
        "replacement_sha256": sha256(replacement),
        "replacement_size_bytes": replacement.stat().st_size,
        "canonical_manifest_updated": False,
    }
    receipt_path = ROOT / "outputs" / "quality" / f"viirs_repair_{pair_key.replace('.', '_')}.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pair_key")
    args = parser.parse_args()
    print(json.dumps(repair(args.pair_key), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

