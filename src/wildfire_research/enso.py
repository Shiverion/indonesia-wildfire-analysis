"""NOAA CPC RONI parsing and provenance helpers."""

from __future__ import annotations

import calendar
import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.request import Request, urlopen

from .paths import logical_relative


DEFAULT_RONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt"
PROJECT_ROOT = Path(__file__).resolve().parents[2]

_SEASON_END_MONTH = {
    "DJF": 2,
    "JFM": 3,
    "FMA": 4,
    "MAM": 5,
    "AMJ": 6,
    "MJJ": 7,
    "JJA": 8,
    "JAS": 9,
    "ASO": 10,
    "SON": 11,
    "OND": 12,
    "NDJ": 1,
}


@dataclass(frozen=True)
class RoniRecord:
    season: str
    season_year: int
    end_date: date
    anomaly_c: float


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _public_artifact_path(path: Path) -> str:
    """Return stable provenance without publishing a workstation path."""
    try:
        return logical_relative(PROJECT_ROOT, path)
    except ValueError:
        return path.name


def parse_roni_text(text: str) -> list[RoniRecord]:
    """Parse CPC's whitespace-delimited RONI text file, rejecting malformed data."""
    records: list[RoniRecord] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("SEAS"):
            continue
        parts = line.split()
        if len(parts) != 3:
            raise ValueError(f"RONI line {line_number} must have 3 fields: {raw_line!r}")
        season, year_text, anomaly_text = parts
        if season not in _SEASON_END_MONTH:
            raise ValueError(f"RONI line {line_number} has unknown season {season!r}")
        try:
            season_year = int(year_text)
            anomaly_c = float(anomaly_text)
        except ValueError as exc:
            raise ValueError(f"RONI line {line_number} has invalid numeric fields") from exc
        end_month = _SEASON_END_MONTH[season]
        end_year = season_year + 1 if season == "NDJ" else season_year
        end_day = calendar.monthrange(end_year, end_month)[1]
        records.append(RoniRecord(season, season_year, date(end_year, end_month, end_day), anomaly_c))
    if not records:
        raise ValueError("RONI source contained no records")
    if len({(r.season, r.season_year) for r in records}) != len(records):
        raise ValueError("RONI source contains duplicate season/year rows")
    return sorted(records, key=lambda r: r.end_date)


def latest_complete_before(records: Iterable[RoniRecord], cutoff: date) -> RoniRecord:
    """Return the latest complete three-month season that ended before a cutoff date."""
    eligible = [record for record in records if record.end_date < cutoff]
    if not eligible:
        raise ValueError(f"No complete RONI season before {cutoff.isoformat()}")
    return max(eligible, key=lambda record: record.end_date)


def fetch_roni(url: str = DEFAULT_RONI_URL, timeout_seconds: int = 30) -> tuple[bytes, str]:
    request = Request(url, headers={"User-Agent": "IndonesiaWildfireResearch/1.0 (+reproducible protocol)"})
    with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310: fixed official HTTPS URL/explicit CLI override
        payload = response.read()
        resolved_url = response.geturl()
    if not payload:
        raise ValueError("RONI download was empty")
    return payload, resolved_url


def write_roni_artifacts(
    payload: bytes,
    source_url: str,
    raw_path: Path,
    derived_csv_path: Path,
    metadata_path: Path,
    retrieved_at: datetime | None = None,
) -> list[RoniRecord]:
    """Store raw bytes, deterministic seasonal table, and provenance metadata."""
    retrieved_at = retrieved_at or datetime.now(timezone.utc)
    text = payload.decode("utf-8")
    records = parse_roni_text(text)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    derived_csv_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(payload)
    with derived_csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["season", "season_year", "end_date", "anomaly_c"])
        writer.writeheader()
        for record in records:
            row = asdict(record)
            row["end_date"] = record.end_date.isoformat()
            writer.writerow(row)
    metadata = {
        "source_url": source_url,
        "retrieved_at_utc": retrieved_at.isoformat(),
        "raw_path": _public_artifact_path(raw_path),
        "raw_sha256": sha256_bytes(payload),
        "record_count": len(records),
        "first_complete_season_end": records[0].end_date.isoformat(),
        "last_complete_season_end": records[-1].end_date.isoformat(),
        "note": "CPC can revise recent RONI values; this artifact is a retrospective frozen retrieval, not proof of real-time availability.",
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return records
