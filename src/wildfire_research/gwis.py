"""Anonymous GWIS aggregate burned-area ingestion and bounded descriptive analysis."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import statistics
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from .enso import RoniRecord


DEFAULT_GWIS_URL = (
    "https://effis-gwis-cms.s3.eu-west-1.amazonaws.com/apps/country.profile/"
    "GLOBFIRE_burned_area_full_dataset_2002_2024.zip"
)

# The GWIS download uses the older four-province GADM level-1 series.
# Kalimantan Utara is not separate in this historical coding and is folded into
# the legacy Kalimantan Timur unit. Do not compare it directly with current
# five-province administrative statistics without a boundary harmonization.
KALIMANTAN_GADM36 = {
    "IDN.12_1": "Kalimantan Barat",
    "IDN.13_1": "Kalimantan Selatan",
    "IDN.14_1": "Kalimantan Tengah",
    "IDN.15_1": "Kalimantan Timur (legacy unit; includes later Kalimantan Utara area)",
}


@dataclass(frozen=True)
class GwisMonthlyRecord:
    gid_1: str
    province: str
    year: int
    month: int
    burned_area_ha: float
    fire_count: int


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def fetch_gwis(url: str = DEFAULT_GWIS_URL, timeout_seconds: int = 60) -> tuple[bytes, str]:
    request = Request(url, headers={"User-Agent": "IndonesiaWildfireResearch/1.0 (+reproducible protocol)"})
    with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310: official HTTPS URL/explicit CLI override
        payload = response.read()
        resolved_url = response.geturl()
    if not payload:
        raise ValueError("GWIS download was empty")
    return payload, resolved_url


def parse_gwis_zip(payload: bytes) -> list[GwisMonthlyRecord]:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = archive.namelist()
        if names != ["GLOBFIRE_burned_area_full_dataset_2002_2024.csv"]:
            raise ValueError(f"Unexpected GWIS archive members: {names}")
        with archive.open(names[0]) as raw_handle:
            reader = csv.DictReader(io.TextIOWrapper(raw_handle, encoding="utf-8-sig"), delimiter=";")
            expected = {"gid_0", "gid_1", "year", "month", "ba_area_ha", "ba_count"}
            if set(reader.fieldnames or []) != expected:
                raise ValueError(f"Unexpected GWIS schema: {reader.fieldnames}")
            rows: list[GwisMonthlyRecord] = []
            for row in reader:
                if row["gid_0"] != "IDN" or row["gid_1"] not in KALIMANTAN_GADM36:
                    continue
                year = int(float(row["year"]))
                month = int(float(row["month"]))
                area = float(row["ba_area_ha"])
                count = int(float(row["ba_count"]))
                if not (2002 <= year <= 2024 and 1 <= month <= 12):
                    raise ValueError(f"GWIS row has invalid time: {row}")
                if area < 0 or count < 0:
                    raise ValueError(f"GWIS row has negative burned area/count: {row}")
                rows.append(GwisMonthlyRecord(row["gid_1"], KALIMANTAN_GADM36[row["gid_1"]], year, month, area, count))
    if not rows:
        raise ValueError("GWIS archive contained no Kalimantan records")
    duplicate_keys = [(row.gid_1, row.year, row.month) for row in rows]
    if len(set(duplicate_keys)) != len(duplicate_keys):
        raise ValueError("GWIS archive contains duplicate Kalimantan province-month rows")
    return sorted(rows, key=lambda row: (row.year, row.month, row.gid_1))


def write_gwis_artifacts(
    payload: bytes,
    source_url: str,
    raw_path: Path,
    derived_csv_path: Path,
    metadata_path: Path,
    retrieved_at: datetime | None = None,
) -> list[GwisMonthlyRecord]:
    rows = parse_gwis_zip(payload)
    retrieved_at = retrieved_at or datetime.now(timezone.utc)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    derived_csv_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(payload)
    with derived_csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["gid_1", "province", "year", "month", "burned_area_ha", "fire_count"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "gid_1": row.gid_1,
                "province": row.province,
                "year": row.year,
                "month": row.month,
                "burned_area_ha": row.burned_area_ha,
                "fire_count": row.fire_count,
            })
    metadata = {
        "source_url": source_url,
        "retrieved_at_utc": retrieved_at.isoformat(),
        "raw_path": str(raw_path),
        "raw_sha256": sha256_bytes(payload),
        "record_count": len(rows),
        "years_present": [min(row.year for row in rows), max(row.year for row in rows)],
        "province_codes": sorted({row.gid_1 for row in rows}),
        "boundary_note": "GWIS uses an older four-province GADM level-1 Kalimantan coding; the legacy Kalimantan Timur unit includes territory now called Kalimantan Utara.",
        "analysis_limit": "Aggregate burned-area/fire-count rows are descriptive only. They are not VIIRS overpass opportunity data, individual event onsets, or forest-only burned area.",
    }
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return rows


def read_gwis_csv(path: Path) -> list[GwisMonthlyRecord]:
    rows: list[GwisMonthlyRecord] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                GwisMonthlyRecord(
                    gid_1=row["gid_1"],
                    province=row["province"],
                    year=int(row["year"]),
                    month=int(row["month"]),
                    burned_area_ha=float(row["burned_area_ha"]),
                    fire_count=int(row["fire_count"]),
                )
            )
    if not rows:
        raise ValueError(f"No derived GWIS rows found in {path}")
    return rows


def _pearson_correlation(values_x: list[float], values_y: list[float]) -> float | None:
    if len(values_x) != len(values_y) or len(values_x) < 3:
        return None
    mean_x = statistics.fmean(values_x)
    mean_y = statistics.fmean(values_y)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(values_x, values_y))
    denominator_x = math.sqrt(sum((x - mean_x) ** 2 for x in values_x))
    denominator_y = math.sqrt(sum((y - mean_y) ** 2 for y in values_y))
    if denominator_x == 0 or denominator_y == 0:
        return None
    return numerator / (denominator_x * denominator_y)


def _seasonal_roni_mean(records: list[RoniRecord]) -> dict[int, float]:
    values: dict[int, list[float]] = {}
    for record in records:
        if record.end_date.month in {8, 9, 10, 11}:
            values.setdefault(record.end_date.year, []).append(record.anomaly_c)
    return {year: statistics.fmean(series) for year, series in values.items()}


def build_gwis_context_markdown(rows: list[GwisMonthlyRecord], roni_records: list[RoniRecord]) -> str:
    """Report observed aggregate burned area and ENSO context without causal interpretation."""
    reported: dict[int, float] = {}
    fire_counts: dict[int, int] = {}
    observed_months: dict[int, set[tuple[str, int]]] = {}
    for row in rows:
        if 7 <= row.month <= 11:
            reported[row.year] = reported.get(row.year, 0.0) + row.burned_area_ha
            fire_counts[row.year] = fire_counts.get(row.year, 0) + row.fire_count
            observed_months.setdefault(row.year, set()).add((row.gid_1, row.month))

    roni_by_year = _seasonal_roni_mean(roni_records)
    years = list(range(2015, 2025))
    paired_years = [year for year in years if year in reported and year in roni_by_year]
    correlation = _pearson_correlation(
        [roni_by_year[year] for year in paired_years],
        [math.log1p(reported[year]) for year in paired_years],
    )

    lines = [
        "# Preliminary Aggregate Burned-Area Insight -- Kalimantan",
        "",
        "## Scope and non-substitution rule",
        "",
        "This is a descriptive aggregation of GWIS/GLOBFIRE monthly admin-1 burned-area rows for the historic four-province Kalimantan coding. It is not the primary 1 km S-NPP first-observed-onset outcome; it has no observation-opportunity denominator, no forest-only cohort, no dated accessibility exposure, and no 2025 data. It must not be used to decide the central accessibility or transformation hypothesis.",
        "",
        "## Observed climate-context pattern",
        "",
    ]
    if correlation is not None and paired_years:
        maximum_year = max(paired_years, key=lambda year: reported[year])
        median_area = statistics.median(reported[year] for year in paired_years)
        ratio = reported[maximum_year] / median_area if median_area > 0 else None
        ratio_text = f"{ratio:.1f}x" if ratio is not None else "not defined because the median is zero"
        lines.append(
            f"For the {len(paired_years)} shared fire seasons from 2015 through 2024, the largest reported July-November burned area occurred in **{maximum_year}** at **{reported[maximum_year]:,.0f} ha**. That was **{ratio_text}** the median reported area across those seasons. The unadjusted Pearson correlation between mean August-November RONI and log(1 + reported July-November burned area) was **{correlation:.2f}** (n = {len(paired_years)}). This is a descriptive climate-context association, not a causal estimate and not a test of the human-accessibility hypothesis."
        )
    else:
        lines.append(
            "There were fewer than three shared complete seasons with reported burned area and RONI, so no correlation is reported. This is a descriptive climate-context analysis, not a causal estimate and not a test of the human-accessibility hypothesis."
        )

    lines.extend([
        "",
        "## Fire-season table",
        "",
        "| Year | Reported July-Nov burned area (ha) | Reported fire count | Province-month rows present / 20 | Mean Aug-Nov RONI (degrees C) |",
        "|---:|---:|---:|---:|---:|",
    ])
    for year in range(2015, 2025):
        area = reported.get(year)
        count = fire_counts.get(year)
        month_count = len(observed_months.get(year, set()))
        roni = roni_by_year.get(year)
        if area is not None and count is not None:
            area_text = f"{area:,.0f}"
            count_text = f"{count:,}"
        else:
            area_text = "--"
            count_text = "--"
        roni_text = "--" if roni is None else f"{roni:.2f}"
        lines.append(f"| {year} | {area_text} | {count_text} | {month_count} / 20 | {roni_text} |")

    lines.extend([
        "",
        "## Interpretation and required caution",
        "",
        "The open data provide a useful plausibility check: the study period contains both strong El Nino and La Nina conditions and substantial variation in aggregate reported burning. The association is vulnerable to unmeasured local weather, vegetation, peat, land conversion, boundary changes, reporting structure, and time trends. Missing province-month rows are displayed rather than automatically treated as observed zero fire. The historic GADM coding has four Kalimantan units; its Kalimantan Timur unit includes territory now represented by Kalimantan Utara. Therefore, this report supports data planning and descriptive triangulation only.",
        "",
        "## Provenance",
        "",
        "GWIS archive: `data/raw/gwis/GLOBFIRE_burned_area_full_dataset_2002_2024.zip`; filtered table: `data/derived/gwis/kalimantan_monthly_burned_area.csv`; retrieval/hash record: `outputs/quality/gwis_fetch.json`. ENSO context uses the separately archived NOAA CPC RONI file.",
        "",
    ])
    return "\n".join(lines)
