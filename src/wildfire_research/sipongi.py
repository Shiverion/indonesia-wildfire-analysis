"""SiPongi portal-record acquisition and strictly descriptive reporting.

The public Indonesian SiPongi endpoint supplies positive hotspot records only.
It does not supply swath coverage, validated UTC acquisition times, fire radiative
power, or non-detection opportunities.  This module therefore deliberately does
not create a primary fire-onset or causal-analysis outcome.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import statistics
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Collection
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from .enso import RoniRecord
from .paths import logical_relative


DEFAULT_SIPONGI_URL = "https://opsroom.sipongidata.my.id/api/sebaran/download"
MIN_SIPONGI_YEAR = 2015
DEFAULT_EXCLUDED_SIPONGI_YEARS = (2024,)
JAKARTA_TIMEZONE = ZoneInfo("Asia/Jakarta")
KALIMANTAN_PROVINCES = {
    "11": "Kalimantan Barat",
    "12": "Kalimantan Selatan",
    "13": "Kalimantan Tengah",
    "14": "Kalimantan Timur",
    "15": "Kalimantan Utara",
}
_EXPECTED_COLUMNS = (
    "Provinsi",
    "Kab Kota",
    "Kecamatan",
    "Desa",
    "Tanggal",
    "Waktu",
    "Satelit",
    "Confidence",
    "Latitude",
    "Longitude",
)


@dataclass(frozen=True)
class SipongiRecord:
    province_id: str
    province: str
    district: str
    subdistrict: str
    village: str
    reported_date: date
    reported_time: str
    satellite: str
    confidence: str
    latitude: float
    longitude: float
    source_file: str
    source_sha256: str
    source_schema_repaired: bool = False


@dataclass(frozen=True)
class SipongiFileEvidence:
    province_id: str
    province: str
    year: int
    request_period: str
    request_url: str
    raw_path: Path
    raw_sha256: str
    canonical_records_sha256: str
    byte_count: int
    record_count: int
    repaired_row_count: int
    validation_attempts: int
    rejected_response_count: int
    reused_local_file: bool


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_json_sha256(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _canonical_records_sha256(records: list[SipongiRecord]) -> str:
    """Hash normalized content after a deterministic sort, separate from raw bytes."""
    values = [
        {
            "province_id": record.province_id,
            "province": record.province,
            "district": record.district,
            "subdistrict": record.subdistrict,
            "village": record.village,
            "reported_date": record.reported_date.isoformat(),
            "reported_time": record.reported_time,
            "satellite": record.satellite,
            "confidence": record.confidence,
            "latitude": record.latitude,
            "longitude": record.longitude,
        }
        for record in records
    ]
    values.sort(key=lambda row: json.dumps(row, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
    return _canonical_json_sha256(values)


def fire_season_months() -> tuple[int, ...]:
    """Return the registered July--November season by portal-reported date.

    The protocol's primary season is in UTC.  SiPongi reports display times in
    WIB even for eastern provinces, so this auxiliary product uses only its
    *reported date* and never asserts an exact UTC interval.
    """
    return (7, 8, 9, 10, 11)


def latest_completed_fire_season_year(as_of_date: date | None = None) -> int:
    """Return the latest year whose July--November season has fully elapsed."""
    as_of_date = as_of_date or datetime.now(JAKARTA_TIMEZONE).date()
    return as_of_date.year if as_of_date >= date(as_of_date.year, 11, 30) else as_of_date.year - 1


def latest_closed_portal_day(as_of_date: date | None = None) -> date:
    """Return the most recent complete Asia/Jakarta portal-reported date.

    The portal can expose intra-day rows. A monitoring snapshot therefore stops
    at the preceding calendar day rather than presenting an unfinished local
    day as complete evidence.
    """
    as_of_date = as_of_date or datetime.now(JAKARTA_TIMEZONE).date()
    return as_of_date - timedelta(days=1)


def _validate_complete_season_year_range(
    start_year: int,
    end_year: int,
    *,
    as_of_date: date | None = None,
) -> tuple[int, ...]:
    maximum = latest_completed_fire_season_year(as_of_date)
    if not MIN_SIPONGI_YEAR <= start_year <= end_year <= maximum:
        raise ValueError(
            f"years must lie within {MIN_SIPONGI_YEAR}--{maximum}, the completed July--November seasons available as of the retrieval date"
        )
    return tuple(range(start_year, end_year + 1))


def _normalized_excluded_years(excluded_years: Collection[int]) -> tuple[int, ...]:
    return tuple(sorted({int(year) for year in excluded_years}))


def month_bounds(year: int, month: int) -> tuple[date, date]:
    if year < MIN_SIPONGI_YEAR:
        raise ValueError(f"descriptive SiPongi acquisition begins in {MIN_SIPONGI_YEAR}")
    if month not in fire_season_months():
        raise ValueError("only the registered July--November descriptive season is supported")
    if month == 12:
        return date(year, month, 1), date(year, 12, 31)
    next_month = date(year, month + 1, 1)
    return date(year, month, 1), date.fromordinal(next_month.toordinal() - 1)


def season_bounds(year: int) -> tuple[date, date]:
    if year < MIN_SIPONGI_YEAR:
        raise ValueError(f"descriptive SiPongi acquisition begins in {MIN_SIPONGI_YEAR}")
    return date(year, 7, 1), date(year, 11, 30)


def build_request_url(
    province_id: str,
    start_date: date,
    end_date: date,
    base_url: str = DEFAULT_SIPONGI_URL,
) -> str:
    if province_id not in KALIMANTAN_PROVINCES:
        raise ValueError(f"unknown Kalimantan province ID: {province_id}")
    if end_date < start_date:
        raise ValueError("end date precedes start date")
    parameters = {
        "startdate": f"{start_date.isoformat()} 00:00:00",
        "enddate": f"{end_date.isoformat()} 23:59:59",
        "provinsi": province_id,
        "confidence": "all",
        "satelit": "all-nasa",
        "tipe": "txt",
    }
    return f"{base_url}?{urlencode(parameters)}"


def fetch_sipongi_payload(
    url: str,
    *,
    timeout_seconds: int = 120,
    retries: int = 3,
) -> tuple[bytes, dict[str, str]]:
    """Fetch one portal response with bounded retry/backoff.

    Calls are intentionally sequential in the command layer.  The portal
    advertises a rate limit; the code avoids parallel request bursts.
    """
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        request = Request(url, headers={"User-Agent": "IndonesiaWildfireResearch/1.0 (+reproducible descriptive audit)"})
        try:
            with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310: endpoint is user-overridable only through explicit CLI option
                payload = response.read()
                headers = {key.lower(): value for key, value in response.headers.items()}
            if not payload:
                raise ValueError("SiPongi response was empty")
            return payload, headers
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            last_error = exc
            retryable_status = isinstance(exc, HTTPError) and (exc.code == 429 or exc.code >= 500)
            if attempt == retries or (isinstance(exc, HTTPError) and not retryable_status):
                break
            time.sleep(min(15.0, 1.5 * (2**attempt)))
    raise RuntimeError(f"SiPongi request failed after {retries + 1} attempts: {url}") from last_error


def parse_sipongi_payload(
    payload: bytes,
    *,
    province_id: str,
    start_date: date,
    end_date: date,
    source_file: str,
    source_sha256: str | None = None,
) -> list[SipongiRecord]:
    """Validate one TXT response and turn it into standardized local records."""
    if province_id not in KALIMANTAN_PROVINCES:
        raise ValueError(f"unknown Kalimantan province ID: {province_id}")
    if not payload:
        raise ValueError("SiPongi response was empty")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("SiPongi response was not UTF-8 text") from exc
    # The service sometimes represents an empty valid selection as a JSON
    # object rather than as a header-only TXT response.  Treat only an exact
    # empty data array as a valid zero, never an arbitrary JSON error body.
    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            possible_empty = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError("SiPongi response was neither TXT nor valid empty JSON") from exc
        if possible_empty == {"data": []}:
            return []
        raise ValueError(f"Unexpected JSON SiPongi response: {possible_empty!r}")
    reader = csv.reader(io.StringIO(text), skipinitialspace=True)
    header = next(reader, None)
    fieldnames = tuple((name or "").strip() for name in (header or []))
    if fieldnames != _EXPECTED_COLUMNS:
        raise ValueError(f"Unexpected SiPongi schema: {header}")
    digest = source_sha256 or sha256_bytes(payload)
    records: list[SipongiRecord] = []
    expected_province = KALIMANTAN_PROVINCES[province_id].casefold()
    for raw_values in reader:
        values = [(value or "").strip() for value in raw_values]
        if not any(values):
            continue
        if len(values) < len(_EXPECTED_COLUMNS):
            raise ValueError(f"Too few columns in SiPongi row: {raw_values}")
        # A small number of source rows contain an unquoted comma in the
        # village label.  Dates, sensor fields, confidence, and coordinates
        # are the final six fields, so retain all of them and reconstruct only
        # the administrative tail.  Mark the repair in local evidence rather
        # than quietly shifting dates or coordinates.
        repaired = len(values) > len(_EXPECTED_COLUMNS)
        province, district, subdistrict = values[:3]
        village = ",".join(values[3:-6])
        row = {
            "Provinsi": province,
            "Kab Kota": district,
            "Kecamatan": subdistrict,
            "Desa": village,
            "Tanggal": values[-6],
            "Waktu": values[-5],
            "Satelit": values[-4],
            "Confidence": values[-3],
            "Latitude": values[-2],
            "Longitude": values[-1],
        }
        try:
            reported = datetime.strptime(row["Tanggal"], "%d-%m-%Y").date()
            latitude = float(row["Latitude"])
            longitude = float(row["Longitude"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid SiPongi row: {raw_values}") from exc
        if not start_date <= reported <= end_date:
            raise ValueError(f"SiPongi row date outside requested period: {raw_values}")
        if row["Provinsi"].casefold() != expected_province:
            raise ValueError(f"SiPongi row province disagrees with request: {raw_values}")
        # Broad Kalimantan bounds catch malformed coordinate parsing without
        # pretending the portal row is an exact sensor-geolocated observation.
        if not (-6.0 <= latitude <= 8.0 and 107.0 <= longitude <= 121.0):
            raise ValueError(f"SiPongi row is outside broad Kalimantan bounds: {raw_values}")
        if not row["Satelit"] or not row["Confidence"] or not row["Waktu"]:
            raise ValueError(f"SiPongi row is missing sensor/confidence/time: {raw_values}")
        records.append(
            SipongiRecord(
                province_id=province_id,
                province=row["Provinsi"],
                district=row["Kab Kota"],
                subdistrict=row["Kecamatan"],
                village=row["Desa"],
                reported_date=reported,
                reported_time=row["Waktu"],
                satellite=row["Satelit"],
                confidence=row["Confidence"],
                latitude=latitude,
                longitude=longitude,
                source_file=source_file,
                source_sha256=digest,
                source_schema_repaired=repaired,
            )
        )
    return records


def _raw_path(raw_root: Path, province_id: str, year: int, request_period: str) -> Path:
    return raw_root / str(year) / f"sipongi_{province_id}_{year}_{request_period}_jul-nov.txt"


def _relative(path: Path, root: Path) -> str:
    return logical_relative(root, path)


def _snapshot_provider_contract(root: Path, raw_root: Path, base_url: str) -> dict[str, Any]:
    """Freeze the mutable provider configuration and province catalogue."""
    marker = "/sebaran/download"
    if marker not in base_url:
        raise ValueError("SiPongi download endpoint must contain '/sebaran/download' to snapshot its provider contract")
    api_base = base_url.split(marker, 1)[0]
    configuration_url = f"{api_base}/konfigurasi"
    provinces_url = f"{api_base}/getProvinsi/all"
    configuration_payload, _ = fetch_sipongi_payload(configuration_url)
    provinces_payload, _ = fetch_sipongi_payload(provinces_url)
    try:
        configuration = json.loads(configuration_payload.decode("utf-8"))
        provinces = json.loads(provinces_payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("SiPongi provider configuration/catalogue was not valid UTF-8 JSON") from exc
    if not isinstance(configuration, dict) or not isinstance(provinces, list):
        raise ValueError("SiPongi provider configuration/catalogue had an unexpected JSON shape")
    live_provinces = {
        str(row.get("id")): str(row.get("nama_provinsi", "")).strip()
        for row in provinces
        if isinstance(row, dict)
    }
    mismatch = {
        identifier: {"expected": name, "provider": live_provinces.get(identifier)}
        for identifier, name in KALIMANTAN_PROVINCES.items()
        if live_provinces.get(identifier) != name
    }
    if mismatch:
        raise ValueError(f"SiPongi live province catalogue changed: {mismatch}")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot_root = raw_root / "_provider_snapshots"
    snapshot_root.mkdir(parents=True, exist_ok=True)
    configuration_path = snapshot_root / f"konfigurasi_{timestamp}.json"
    provinces_path = snapshot_root / f"provinsi_{timestamp}.json"
    configuration_path.write_bytes(configuration_payload)
    provinces_path.write_bytes(provinces_payload)
    return {
        "api_base_url": api_base,
        "configuration_url": configuration_url,
        "configuration_path": _relative(configuration_path, root),
        "configuration_sha256": sha256_bytes(configuration_payload),
        "province_catalogue_url": provinces_url,
        "province_catalogue_path": _relative(provinces_path, root),
        "province_catalogue_sha256": sha256_bytes(provinces_payload),
        "validated_kalimantan_provinces": KALIMANTAN_PROVINCES,
    }


def _quarantine_invalid_payload(
    *,
    root: Path,
    raw_root: Path,
    raw_path: Path,
    payload: bytes,
    request_url: str,
    reason: str,
) -> dict[str, str]:
    """Move a bad provider response aside with a receipt; never silently overwrite it."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    digest = sha256_bytes(payload)
    rejected_root = raw_root / "_rejected"
    rejected_root.mkdir(parents=True, exist_ok=True)
    destination = rejected_root / f"{raw_path.stem}_{timestamp}_{digest[:12]}{raw_path.suffix}"
    if raw_path.exists():
        raw_path.replace(destination)
    else:
        destination.write_bytes(payload)
    receipt_path = destination.with_suffix(destination.suffix + ".json")
    receipt = {
        "quarantined_at_utc": datetime.now(timezone.utc).isoformat(),
        "request_url": request_url,
        "raw_sha256": digest,
        "reason": reason,
        "source_path": _relative(destination, root),
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return {"payload_path": _relative(destination, root), "receipt_path": _relative(receipt_path, root)}


def fetch_sipongi_fire_season(
    *,
    root: Path,
    raw_root: Path,
    derived_csv_path: Path,
    metadata_path: Path,
    start_year: int = 2015,
    end_year: int = 2025,
    base_url: str = DEFAULT_SIPONGI_URL,
    request_granularity: str = "month",
    overwrite: bool = False,
    request_delay_seconds: float = 0.35,
    validation_retries: int = 1,
    excluded_years: Collection[int] = DEFAULT_EXCLUDED_SIPONGI_YEARS,
    progress: Callable[[str], None] | None = None,
) -> tuple[list[SipongiRecord], list[SipongiFileEvidence]]:
    """Fetch/resume all five provinces over July--November portal dates.

    Each province-month is an independently hashed raw response.  This lets a
    failed acquisition resume safely and makes the portal's per-query behavior
    inspectable.  It is deliberately not a fast, parallel scraper.
    """
    requested_years = _validate_complete_season_year_range(start_year, end_year)
    excluded = _normalized_excluded_years(excluded_years)
    selected_years = tuple(year for year in requested_years if year not in excluded)
    if not selected_years:
        raise ValueError("all requested SiPongi archive years are excluded")
    if request_delay_seconds < 0:
        raise ValueError("request delay cannot be negative")
    if validation_retries < 0:
        raise ValueError("validation retries cannot be negative")
    raw_root.mkdir(parents=True, exist_ok=True)
    provider_snapshot = _snapshot_provider_contract(root, raw_root, base_url)
    all_records: list[SipongiRecord] = []
    evidence: list[SipongiFileEvidence] = []
    if request_granularity not in {"month", "season"}:
        raise ValueError("request granularity must be 'month' or 'season'")
    request_periods: list[tuple[int, str, date, date]] = []
    for year in selected_years:
        if request_granularity == "month":
            for month in fire_season_months():
                start_date, end_date = month_bounds(year, month)
                request_periods.append((year, f"{month:02d}", start_date, end_date))
        else:
            start_date, end_date = season_bounds(year)
            request_periods.append((year, "07-11", start_date, end_date))
    requests = [
        (year, request_period, start_date, end_date, province_id)
        for year, request_period, start_date, end_date in request_periods
        for province_id in KALIMANTAN_PROVINCES
    ]
    total = len(requests)
    for ordinal, (year, request_period, start_date, end_date, province_id) in enumerate(requests, start=1):
        url = build_request_url(province_id, start_date, end_date, base_url)
        raw_path = _raw_path(raw_root, province_id, year, request_period)
        validation_attempts = 0
        rejected_response_count = 0
        while True:
            reused = raw_path.is_file() and not overwrite and validation_attempts == 0
            if reused:
                payload = raw_path.read_bytes()
                if not payload:
                    raise ValueError(f"existing SiPongi payload is empty: {raw_path}")
                headers: dict[str, str] = {}
            else:
                payload, headers = fetch_sipongi_payload(url)
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                raw_path.write_bytes(payload)
            digest = sha256_bytes(payload)
            source_file = _relative(raw_path, root)
            try:
                records = parse_sipongi_payload(
                    payload,
                    province_id=province_id,
                    start_date=start_date,
                    end_date=end_date,
                    source_file=source_file,
                    source_sha256=digest,
                )
            except ValueError as exc:
                rejected_response_count += 1
                quarantine = _quarantine_invalid_payload(
                    root=root,
                    raw_root=raw_root,
                    raw_path=raw_path,
                    payload=payload,
                    request_url=url,
                    reason=str(exc),
                )
                validation_attempts += 1
                if progress:
                    progress(
                        f"[{ordinal}/{total}] rejected {year}-{request_period} {KALIMANTAN_PROVINCES[province_id]} response; quarantined at {quarantine['payload_path']}"
                    )
                if validation_attempts > validation_retries:
                    raise RuntimeError(
                        f"SiPongi response remained invalid after {validation_attempts} validation retry/retries: {url}"
                    ) from exc
                continue
            break
        all_records.extend(records)
        entry = SipongiFileEvidence(
            province_id=province_id,
            province=KALIMANTAN_PROVINCES[province_id],
            year=year,
            request_period=request_period,
            request_url=url,
            raw_path=raw_path,
            raw_sha256=digest,
            canonical_records_sha256=_canonical_records_sha256(records),
            byte_count=len(payload),
            record_count=len(records),
            repaired_row_count=sum(record.source_schema_repaired for record in records),
            validation_attempts=validation_attempts + 1,
            rejected_response_count=rejected_response_count,
            reused_local_file=reused,
        )
        evidence.append(entry)
        if progress:
            mode = "reused" if reused else "downloaded"
            rate_limit = headers.get("x-ratelimit-limit")
            suffix = f"; server rate limit {rate_limit}" if rate_limit else ""
            progress(f"[{ordinal}/{total}] {mode} {year}-{request_period} {KALIMANTAN_PROVINCES[province_id]}: {len(records):,} records{suffix}")
        if not reused and ordinal < total and request_delay_seconds:
            time.sleep(request_delay_seconds)

    _write_sipongi_derived(all_records, derived_csv_path)
    _write_sipongi_metadata(
        root=root,
        evidence=evidence,
        metadata_path=metadata_path,
        start_year=start_year,
        end_year=end_year,
        base_url=base_url,
        request_granularity=request_granularity,
        provider_snapshot=provider_snapshot,
        excluded_years=excluded,
        coverage_kind="complete_fire_season_archive",
    )
    return all_records, evidence


def fetch_sipongi_monitoring_snapshot(
    *,
    root: Path,
    raw_root: Path,
    through_date: date,
    base_url: str = DEFAULT_SIPONGI_URL,
    request_delay_seconds: float = 0.35,
    validation_retries: int = 1,
    progress: Callable[[str], None] | None = None,
) -> tuple[list[SipongiRecord], list[SipongiFileEvidence], Path, Path]:
    """Acquire one immutable, aggregate-only-ready partial-season snapshot.

    This is deliberately a different artifact from the complete July--November
    archive. It stops at a closed portal-reporting day and is never eligible
    for the historical season chart, archive year selector, or a longitudinal
    comparison with completed seasons.
    """
    season_start = date(through_date.year, 7, 1)
    season_end = date(through_date.year, 11, 30)
    if through_date < season_start or through_date >= season_end:
        raise ValueError("partial SiPongi monitoring must end from July 1 through November 29 inclusive")
    if through_date > latest_closed_portal_day():
        raise ValueError("partial SiPongi monitoring cannot claim an open or future Asia/Jakarta portal-reporting day")
    if request_delay_seconds < 0:
        raise ValueError("request delay cannot be negative")
    if validation_retries < 0:
        raise ValueError("validation retries cannot be negative")

    retrieved_at = datetime.now(timezone.utc)
    snapshot_id = f"kalimantan_sipongi_through_{through_date.isoformat()}_{retrieved_at.strftime('%Y%m%dT%H%M%SZ')}"
    snapshot_raw_root = raw_root / "snapshots" / snapshot_id
    if snapshot_raw_root.exists():
        raise FileExistsError(f"immutable SiPongi snapshot path already exists: {snapshot_raw_root}")
    derived_path = root / "data" / "derived" / "sipongi" / "snapshots" / f"{snapshot_id}.csv"
    metadata_path = root / "outputs" / "quality" / "sipongi_snapshots" / f"{snapshot_id}.json"
    provider_snapshot = _snapshot_provider_contract(root, snapshot_raw_root, base_url)
    all_records: list[SipongiRecord] = []
    evidence: list[SipongiFileEvidence] = []
    province_ids = tuple(KALIMANTAN_PROVINCES)

    for ordinal, province_id in enumerate(province_ids, start=1):
        request_period = f"07-{through_date.month:02d}-{through_date.day:02d}"
        url = build_request_url(province_id, season_start, through_date, base_url)
        raw_path = snapshot_raw_root / f"sipongi_{province_id}_{through_date.year}_{request_period}_monitoring.txt"
        validation_attempts = 0
        rejected_response_count = 0
        while True:
            payload, headers = fetch_sipongi_payload(url)
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(payload)
            digest = sha256_bytes(payload)
            try:
                records = parse_sipongi_payload(
                    payload,
                    province_id=province_id,
                    start_date=season_start,
                    end_date=through_date,
                    source_file=_relative(raw_path, root),
                    source_sha256=digest,
                )
            except ValueError as exc:
                rejected_response_count += 1
                quarantine = _quarantine_invalid_payload(
                    root=root,
                    raw_root=snapshot_raw_root,
                    raw_path=raw_path,
                    payload=payload,
                    request_url=url,
                    reason=str(exc),
                )
                validation_attempts += 1
                if progress:
                    progress(
                        f"[{ordinal}/{len(province_ids)}] rejected partial snapshot {KALIMANTAN_PROVINCES[province_id]}; quarantined at {quarantine['payload_path']}"
                    )
                if validation_attempts > validation_retries:
                    raise RuntimeError(
                        f"SiPongi monitoring response remained invalid after {validation_attempts} validation retry/retries: {url}"
                    ) from exc
                continue
            break

        all_records.extend(records)
        evidence.append(
            SipongiFileEvidence(
                province_id=province_id,
                province=KALIMANTAN_PROVINCES[province_id],
                year=through_date.year,
                request_period=request_period,
                request_url=url,
                raw_path=raw_path,
                raw_sha256=digest,
                canonical_records_sha256=_canonical_records_sha256(records),
                byte_count=len(payload),
                record_count=len(records),
                repaired_row_count=sum(record.source_schema_repaired for record in records),
                validation_attempts=validation_attempts + 1,
                rejected_response_count=rejected_response_count,
                reused_local_file=False,
            )
        )
        if progress:
            rate_limit = headers.get("x-ratelimit-limit")
            suffix = f"; server rate limit {rate_limit}" if rate_limit else ""
            progress(
                f"[{ordinal}/{len(province_ids)}] downloaded partial snapshot {KALIMANTAN_PROVINCES[province_id]}: {len(records):,} records{suffix}"
            )
        if ordinal < len(province_ids) and request_delay_seconds:
            time.sleep(request_delay_seconds)

    _write_sipongi_derived(all_records, derived_path)
    _write_sipongi_metadata(
        root=root,
        evidence=evidence,
        metadata_path=metadata_path,
        start_year=through_date.year,
        end_year=through_date.year,
        base_url=base_url,
        request_granularity="partial_snapshot_july_through_closed_day",
        provider_snapshot=provider_snapshot,
        excluded_years=(),
        coverage_kind="validated_partial_monitoring_snapshot",
    )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.update({
        "snapshot_id": snapshot_id,
        "status": "validated_partial",
        "season": {
            "year": through_date.year,
            "start_date": season_start.isoformat(),
            "end_date": season_end.isoformat(),
            "complete": False,
        },
        "through_date": through_date.isoformat(),
        "retrieved_at_utc": retrieved_at.isoformat(),
        "time_basis": "Portal-reported date; UTC unvalidated. The through date is the last closed Asia/Jakarta portal-reporting day.",
        "metric": "positive portal records",
        "comparison_guardrail": {
            "included_in_annual_archive": False,
            "eligible_for_year_slider": False,
            "eligible_for_annual_chart": False,
            "comparable_to_completed_jul_nov_seasons": False,
        },
        "validation": {
            "expected_province_responses": len(province_ids),
            "validated_province_responses": len(evidence),
            "raw_inventory_sha256": metadata["raw_inventory_sha256"],
            "provider_configuration_sha256": provider_snapshot["configuration_sha256"],
            "province_catalogue_sha256": provider_snapshot["province_catalogue_sha256"],
            "raw_records_embedded": False,
            "has_observation_denominator": False,
        },
    })
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return all_records, evidence, derived_path, metadata_path


def build_sipongi_from_local_raw(
    *,
    root: Path,
    raw_root: Path,
    derived_csv_path: Path,
    metadata_path: Path,
    start_year: int = 2015,
    end_year: int = 2025,
    base_url: str = DEFAULT_SIPONGI_URL,
    excluded_years: Collection[int] = DEFAULT_EXCLUDED_SIPONGI_YEARS,
) -> tuple[list[SipongiRecord], list[SipongiFileEvidence]]:
    """Rebuild a complete archive from already validated raw chunks.

    A complete monthly set is preferred for a province-year.  Otherwise one
    valid July--November response is accepted as an expedited local fallback.
    This selection rule prevents double-counting when a failed large request is
    replaced by monthly chunks, while preserving the rejected raw response and
    its receipt separately.
    """
    requested_years = _validate_complete_season_year_range(start_year, end_year)
    excluded = _normalized_excluded_years(excluded_years)
    selected_years = tuple(year for year in requested_years if year not in excluded)
    if not selected_years:
        raise ValueError("all requested SiPongi archive years are excluded")
    provider_snapshot = _snapshot_provider_contract(root, raw_root, base_url)
    all_records: list[SipongiRecord] = []
    evidence: list[SipongiFileEvidence] = []
    selection: dict[str, str] = {}
    for year in selected_years:
        for province_id in KALIMANTAN_PROVINCES:
            monthly = [
                (f"{month:02d}", *_bounds)
                for month in fire_season_months()
                for _bounds in [month_bounds(year, month)]
            ]
            monthly_paths = [_raw_path(raw_root, province_id, year, period) for period, _, _ in monthly]
            if all(path.is_file() for path in monthly_paths):
                selected = monthly
                selection[f"{year}-{province_id}"] = "monthly"
            else:
                start_date, end_date = season_bounds(year)
                season_path = _raw_path(raw_root, province_id, year, "07-11")
                if not season_path.is_file():
                    missing = [str(path) for path in monthly_paths if not path.is_file()]
                    raise FileNotFoundError(
                        f"No complete valid SiPongi source set for {year} province {province_id}; missing monthly paths: {missing} and no season file"
                    )
                selected = [("07-11", start_date, end_date)]
                selection[f"{year}-{province_id}"] = "season_fallback"

            for request_period, start_date, end_date in selected:
                raw_path = _raw_path(raw_root, province_id, year, request_period)
                payload = raw_path.read_bytes()
                if not payload:
                    raise ValueError(f"existing SiPongi payload is empty: {raw_path}")
                digest = sha256_bytes(payload)
                records = parse_sipongi_payload(
                    payload,
                    province_id=province_id,
                    start_date=start_date,
                    end_date=end_date,
                    source_file=_relative(raw_path, root),
                    source_sha256=digest,
                )
                all_records.extend(records)
                evidence.append(
                    SipongiFileEvidence(
                        province_id=province_id,
                        province=KALIMANTAN_PROVINCES[province_id],
                        year=year,
                        request_period=request_period,
                        request_url=build_request_url(province_id, start_date, end_date, base_url),
                        raw_path=raw_path,
                        raw_sha256=digest,
                        canonical_records_sha256=_canonical_records_sha256(records),
                        byte_count=len(payload),
                        record_count=len(records),
                        repaired_row_count=sum(record.source_schema_repaired for record in records),
                        validation_attempts=1,
                        rejected_response_count=0,
                        reused_local_file=True,
                    )
                )
    _write_sipongi_derived(all_records, derived_csv_path)
    _write_sipongi_metadata(
        root=root,
        evidence=evidence,
        metadata_path=metadata_path,
        start_year=start_year,
        end_year=end_year,
        base_url=base_url,
        request_granularity="mixed_local_rebuild_monthly_preferred",
        provider_snapshot=provider_snapshot,
        excluded_years=excluded,
        coverage_kind="complete_fire_season_archive",
    )
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    rejected_receipts = sorted(raw_root.glob("_rejected/*.json"))
    metadata["local_selection_by_year_province"] = selection
    metadata["quarantined_provider_response_receipts"] = [_relative(path, root) for path in rejected_receipts]
    metadata["quarantined_provider_response_count"] = len(rejected_receipts)
    metadata["rebuild_note"] = (
        "Each province-year used exactly one complete source set: all five monthly chunks when available, otherwise one validated season response. "
        "This is a descriptive source assembly, not a primary fire outcome."
    )
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return all_records, evidence


def _write_sipongi_derived(records: list[SipongiRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "province_id",
                "province",
                "district",
                "subdistrict",
                "village",
                "reported_date",
                "reported_time",
                "satellite",
                "confidence",
                "latitude",
                "longitude",
                "source_file",
                "source_sha256",
                "source_schema_repaired",
            ],
        )
        writer.writeheader()
        for record in sorted(
            records,
            key=lambda value: (
                value.reported_date,
                value.province_id,
                value.reported_time,
                value.latitude,
                value.longitude,
                value.satellite,
            ),
        ):
            writer.writerow({
                "province_id": record.province_id,
                "province": record.province,
                "district": record.district,
                "subdistrict": record.subdistrict,
                "village": record.village,
                "reported_date": record.reported_date.isoformat(),
                "reported_time": record.reported_time,
                "satellite": record.satellite,
                "confidence": record.confidence,
                "latitude": record.latitude,
                "longitude": record.longitude,
                "source_file": record.source_file,
                "source_sha256": record.source_sha256,
                "source_schema_repaired": str(record.source_schema_repaired).lower(),
            })


def _write_sipongi_metadata(
    *,
    root: Path,
    evidence: list[SipongiFileEvidence],
    metadata_path: Path,
    start_year: int,
    end_year: int,
    base_url: str,
    request_granularity: str,
    provider_snapshot: dict[str, Any],
    excluded_years: Collection[int] = (),
    coverage_kind: str = "complete_fire_season_archive",
) -> None:
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    file_rows = [
        {
            "province_id": item.province_id,
            "province": item.province,
            "year": item.year,
            "request_period": item.request_period,
            "request_url": item.request_url,
            "raw_path": _relative(item.raw_path, root),
            "raw_sha256": item.raw_sha256,
            "canonical_records_sha256": item.canonical_records_sha256,
            "byte_count": item.byte_count,
            "record_count": item.record_count,
            "repaired_row_count": item.repaired_row_count,
            "validation_attempts": item.validation_attempts,
            "rejected_response_count": item.rejected_response_count,
            "reused_local_file": item.reused_local_file,
        }
        for item in evidence
    ]
    metadata = {
        "source_url": base_url,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "query_scope": {
            "years": [start_year, end_year],
            "excluded_years": list(_normalized_excluded_years(excluded_years)),
            "months": list(fire_season_months()),
            "province_ids": list(KALIMANTAN_PROVINCES),
            "confidence": "all",
            "satellite": "all-nasa",
            "request_granularity": request_granularity,
            "time_rule": "Portal-reported dates only; display-time zone is not validated as sensor acquisition UTC.",
        },
        "coverage_kind": coverage_kind,
        "provider_snapshot": provider_snapshot,
        "file_count": len(file_rows),
        "record_count": sum(item["record_count"] for item in file_rows),
        "empty_response_count": sum(item["record_count"] == 0 for item in file_rows),
        "repaired_row_count": sum(item["repaired_row_count"] for item in file_rows),
        "rejected_response_count": sum(item["rejected_response_count"] for item in file_rows),
        "raw_inventory_sha256": _canonical_json_sha256(file_rows),
        "files": file_rows,
        "licence_or_terms_note": "The public portal requests SiPongi/Kemenhut attribution. Reusable redistribution rights were not established by this acquisition and must be checked before public release of records.",
        "analysis_limit": "Positive portal records only; no swath coverage, valid non-detections, validated UTC, forest-only mask, or individual fire-event linkage. This is not a substitute for the VNP14IMG/VNP03IMG primary outcome.",
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def read_sipongi_csv(path: Path) -> list[SipongiRecord]:
    records: list[SipongiRecord] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        expected = {
            "province_id",
            "province",
            "district",
            "subdistrict",
            "village",
            "reported_date",
            "reported_time",
            "satellite",
            "confidence",
            "latitude",
            "longitude",
            "source_file",
            "source_sha256",
            "source_schema_repaired",
        }
        if set(reader.fieldnames or []) != expected:
            raise ValueError(f"Unexpected derived SiPongi schema: {reader.fieldnames}")
        for row in reader:
            records.append(
                SipongiRecord(
                    province_id=row["province_id"],
                    province=row["province"],
                    district=row["district"],
                    subdistrict=row["subdistrict"],
                    village=row["village"],
                    reported_date=date.fromisoformat(row["reported_date"]),
                    reported_time=row["reported_time"],
                    satellite=row["satellite"],
                    confidence=row["confidence"],
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                    source_file=row["source_file"],
                    source_sha256=row["source_sha256"],
                    source_schema_repaired=row["source_schema_repaired"].casefold() == "true",
                )
            )
    if not records:
        raise ValueError(f"No SiPongi records in {path}")
    return records


def _platform_group(satellite: str) -> str:
    normal = satellite.upper().replace("_", "-")
    if "MODIS" in normal:
        return "NASA-MODIS"
    if "NOAA-20" in normal or "NOAA20" in normal:
        return "NOAA-20"
    if "NPP" in normal:
        return "S-NPP"
    return "other"


def _pearson(values_x: list[float], values_y: list[float]) -> float | None:
    if len(values_x) < 3 or len(values_x) != len(values_y):
        return None
    x_bar = statistics.fmean(values_x)
    y_bar = statistics.fmean(values_y)
    numerator = sum((x - x_bar) * (y - y_bar) for x, y in zip(values_x, values_y))
    x_denominator = math.sqrt(sum((x - x_bar) ** 2 for x in values_x))
    y_denominator = math.sqrt(sum((y - y_bar) ** 2 for y in values_y))
    if not x_denominator or not y_denominator:
        return None
    return numerator / (x_denominator * y_denominator)


def _roni_aug_nov(records: list[RoniRecord]) -> dict[int, float]:
    by_year: dict[int, list[float]] = defaultdict(list)
    for record in records:
        if record.end_date.month in {8, 9, 10, 11}:
            by_year[record.end_date.year].append(record.anomaly_c)
    return {year: statistics.fmean(values) for year, values in by_year.items()}


def build_sipongi_context_markdown(
    records: list[SipongiRecord],
    roni_records: list[RoniRecord],
    *,
    excluded_years: Collection[int] = DEFAULT_EXCLUDED_SIPONGI_YEARS,
) -> str:
    """Build a non-causal, sensor-stratified portal-record context report."""
    by_year: dict[int, Counter[str]] = defaultdict(Counter)
    active_days: dict[int, set[date]] = defaultdict(set)
    total_by_year: Counter[int] = Counter()
    for record in records:
        if record.reported_date.month not in fire_season_months():
            raise ValueError("SiPongi report input contains a record outside the registered descriptive season")
        year = record.reported_date.year
        total_by_year[year] += 1
        by_year[year][_platform_group(record.satellite)] += 1
        active_days[year].add(record.reported_date)
    if not total_by_year:
        raise ValueError("SiPongi report input has no portal records")
    observed_start = min(total_by_year)
    observed_end = max(total_by_year)
    years = sorted(total_by_year)
    missing_years = [year for year in range(observed_start, observed_end + 1) if year not in total_by_year]
    unexpected_missing = sorted(set(missing_years) - set(_normalized_excluded_years(excluded_years)))
    if unexpected_missing:
        raise ValueError(f"SiPongi report input is missing unregistered calendar years: {unexpected_missing}")
    roni_by_year = _roni_aug_nov(roni_records)
    paired = [year for year in years if year in total_by_year and year in roni_by_year]
    all_platform_correlation = _pearson(
        [roni_by_year[year] for year in paired],
        [math.log1p(total_by_year[year]) for year in paired],
    )
    modis_correlation = _pearson(
        [roni_by_year[year] for year in paired],
        [math.log1p(by_year[year]["NASA-MODIS"]) for year in paired],
    )
    largest_year = max(years, key=lambda year: total_by_year[year])
    lines = [
        "# Preliminary SiPongi Portal-Record Insight -- Kalimantan",
        "",
        "## Scope and non-substitution rule",
        "",
        f"This report counts public SiPongi positive hotspot records in the five current Kalimantan provinces for July-November {observed_start}-{observed_end}, using portal-reported dates. A portal record is not an individual wildfire, an ignition, or a valid fire-incidence rate. The endpoint provides no processed-swath denominator, valid non-detections, forest-only cohort, or verified UTC acquisition time. It is not the primary 1 km S-NPP first-observed-onset outcome and cannot test the human-accessibility or transformation hypothesis.",
        "",
        "## Observed sensor and climate context",
        "",
        f"The largest all-platform portal-record count was **{total_by_year[largest_year]:,}** in **{largest_year}**. The all-platform count mixes changing satellite coverage.",
    ]
    if all_platform_correlation is not None:
        lines.append(
            f"Over the {len(paired)} paired seasons, its unadjusted correlation with log(1 + count) and mean August-November RONI was **{all_platform_correlation:.2f}**."
        )
    else:
        lines.append("No all-platform correlation is reported because fewer than three paired seasons were available.")
    if modis_correlation is not None:
        lines.append(
            f"The same descriptive correlation using only NASA-MODIS records was **{modis_correlation:.2f}**. Neither correlation adjusts for local weather, vegetation, peat, land use, detection opportunity, reporting structure, or time trend, so neither is a climate effect estimate."
        )
    else:
        lines.append(
            "A MODIS-only correlation could not be computed. No correlation in this report is a climate effect estimate.")
    lines.extend([
        "",
        "## Fire-season portal-record table",
        "",
        "| Year | All platform records | NASA-MODIS | S-NPP | NOAA-20 | Other/unknown | Portal-reported active dates | Mean Aug-Nov RONI (degrees C) |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for year in years:
        roni = roni_by_year.get(year)
        lines.append(
            f"| {year} | {total_by_year[year]:,} | {by_year[year]['NASA-MODIS']:,} | {by_year[year]['S-NPP']:,} | {by_year[year]['NOAA-20']:,} | {by_year[year]['other']:,} | {len(active_days[year])} | {'--' if roni is None else f'{roni:.2f}'} |"
        )
    lines.extend([
        "",
        "## Interpretation and required caution",
        "",
        "Sensor composition is a design finding, not a nuisance detail: a raw all-platform increase after S-NPP and NOAA-20 appear cannot be interpreted as an increase in wildfire occurrence. The NASA-MODIS column is a platform-restricted descriptive sensitivity, not a correction for cloud, scan geometry, overpass timing, or platform sensitivity. SiPongi display times are labelled WIB even in eastern Kalimantan, so these data must not be used for exact-overpass matching, a 72-hour prior-negative rule, or UTC timing. Before public redistribution of record-level data, confirm the portal's licence; this implementation preserves the requested SiPongi/Kemenhut attribution but does not assume an open redistribution licence.",
        "",
        f"Excluded archive years: {', '.join(map(str, _normalized_excluded_years(excluded_years))) or 'none'}. These are a registered provider-quality exclusion, not zero-record years and not a gap that may be imputed.",
        "",
        "## Provenance",
        "",
        "Raw portal responses: `data/raw/sipongi/`; standardized local table: `data/derived/sipongi/kalimantan_sipongi_jul-nov.csv`; per-request URLs, raw and canonical-content hashes, provider snapshots, and rejected-response receipts: `outputs/quality/sipongi_fetch.json`. ENSO context uses the separately archived NOAA CPC RONI file.",
        "",
    ])
    return "\n".join(lines)
