"""Evidence-bounded synthesis for the open descriptive research tracks."""

from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict

from .enso import RoniRecord
from .gwis import GwisMonthlyRecord
from .sipongi import SipongiRecord


def _roni_aug_nov(records: list[RoniRecord]) -> dict[int, float]:
    grouped: dict[int, list[float]] = defaultdict(list)
    for record in records:
        if record.end_date.month in {8, 9, 10, 11}:
            grouped[record.end_date.year].append(record.anomaly_c)
    return {year: statistics.fmean(values) for year, values in grouped.items()}


def _gwis_jul_nov(rows: list[GwisMonthlyRecord]) -> dict[int, float]:
    totals: dict[int, float] = defaultdict(float)
    for row in rows:
        if 7 <= row.month <= 11:
            totals[row.year] += row.burned_area_ha
    return dict(totals)


def _sipongi_counts(records: list[SipongiRecord]) -> tuple[Counter[int], Counter[int]]:
    all_platform = Counter()
    modis = Counter()
    for record in records:
        all_platform[record.reported_date.year] += 1
        if "MODIS" in record.satellite.upper():
            modis[record.reported_date.year] += 1
    return all_platform, modis


def _ranking(values: dict[int, float], limit: int = 3) -> list[tuple[int, float]]:
    return sorted(values.items(), key=lambda item: (-item[1], item[0]))[:limit]


def build_preliminary_synthesis_markdown(
    *,
    roni_records: list[RoniRecord],
    gwis_rows: list[GwisMonthlyRecord],
    sipongi_records: list[SipongiRecord],
    protocol_report: dict,
) -> str:
    """Write a neutral conclusion from evidence that genuinely exists locally."""
    roni = _roni_aug_nov(roni_records)
    gwis = _gwis_jul_nov(gwis_rows)
    sipongi_all, sipongi_modis = _sipongi_counts(sipongi_records)
    gwis_years = sorted(year for year in gwis if 2015 <= year <= 2024)
    sipongi_years = sorted(sipongi_all)
    if not gwis_years or not sipongi_years:
        raise ValueError("synthesis requires non-empty GWIS and SiPongi evidence")

    gwis_top = _ranking({year: gwis[year] for year in gwis_years})
    neutral_roni_year = min(gwis_years, key=lambda year: abs(roni.get(year, math.inf)))
    strongest_roni_year = max(gwis_years, key=lambda year: roni.get(year, -math.inf))
    sipongi_peak = max(sipongi_years, key=lambda year: sipongi_all[year])
    core_gates = protocol_report.get("phase_1_gates", [])
    blocked_assets = [row["asset_id"] for row in core_gates if not row.get("gate_ready")]
    phase_label = "NI -- Not identifiable" if not protocol_report.get("phase_1_ready") else "Data gate passed; primary model not yet run"

    top_text = "; ".join(f"{year}: {area:,.0f} ha" for year, area in gwis_top)
    shared_years = sorted(set(gwis_years) & set(sipongi_years))
    missing_sipongi_years = [year for year in range(sipongi_years[0], sipongi_years[-1] + 1) if year not in sipongi_years]
    sipongi_coverage = f"{sipongi_years[0]}-{sipongi_years[-1]}"
    if missing_sipongi_years:
        sipongi_coverage += f" excluding {', '.join(map(str, missing_sipongi_years))}"
    lines = [
        "# Evidence-Bounded Preliminary Insight -- Kalimantan Fire Research",
        "",
        "## Bottom line",
        "",
        f"**Central human-accessibility / transformation conclusion: {phase_label}.** The primary matched-overpass analysis has not been substituted with a hotspot-count regression. Consequently, this project currently has no estimate of an accessibility effect, no estimate of a transformation effect, and no causal attribution to people, sectors, companies, or land uses.",
        "",
        "## What the open evidence does show",
        "",
        f"The independent GWIS aggregate archive reports its largest July-November Kalimantan burned area in **{gwis_top[0][0]}** ({gwis_top[0][1]:,.0f} ha). The top three reported seasons are **{top_text}**. The NOAA CPC RONI mean for August-November was **{roni[strongest_roni_year]:.2f} degrees C** in {strongest_roni_year}; that year is the strongest RONI condition in the shared GWIS span.",
        "",
        f"A deliberately countervailing observation is **{neutral_roni_year}**: RONI was near neutral (**{roni[neutral_roni_year]:.2f} degrees C**) while GWIS still reported **{gwis[neutral_roni_year]:,.0f} ha** in July-November. This supports a limited inference: an oceanic ENSO index alone is not a sufficient description of Kalimantan fire-season burden. It does not identify which local mechanisms account for the difference, and it is not evidence that accessibility caused fire.",
        "",
        f"The validated SiPongi descriptive archive spans {sipongi_coverage}. It contains **{sum(sipongi_all.values()):,}** portal records; its all-platform maximum is **{sipongi_peak}** ({sipongi_all[sipongi_peak]:,} records), while the matched NASA-MODIS subtotal is only **{sipongi_modis[sipongi_peak]:,}**. That disparity is direct evidence of changing sensor composition in the portal series, so all-platform count changes must not be called changes in wildfire occurrence.",
        "",
        "## What cannot yet be claimed",
        "",
        "- No exact S-NPP VIIRS observation-opportunity denominator or 72-hour prior-negative frame exists locally.",
        "- No frozen MapBiomas Indonesia 4.1 baseline/lagged transformation export or QA-valid prefire EVI exists locally; vegetation and fuel cannot be omitted from the primary model.",
        "- No validated dated road-opening / settlement accessibility series exists; dated OSM mapping is only a sensitivity, not construction timing.",
        "- No ERA5-Land request is frozen, so wind, VPD, soil water, and other local-weather adjustment are unavailable.",
        "- SiPongi is a positive-record portal source and GWIS is an aggregate burned-area archive. Neither can replace the specified primary outcome.",
        "",
        "## Data-quality decision",
        "",
        "The SiPongi 2024 all-platform requests exposed a provider integrity failure: a Kalimantan Barat request repeatedly returned Alor records. Those responses were quarantined and excluded. The archive therefore leaves 2024 absent rather than using an incorrect response, treating it as zero, or silently filling it from another provider.",
        "",
        "## Evidence sources and next gate",
        "",
        "- [NOAA CPC RONI](https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt): archived locally with retrieval hash; retrospective climate context only.",
        "- [GWIS country-profile downloads](https://gwis.jrc.ec.europa.eu/apps/country.profile/downloads): aggregate monthly burned-area context through 2024, not event geometries or 2025 data.",
        "- [SiPongi hotspot portal](https://sipongi.gakkum.kehutanan.go.id/sebaran-titik-panas): portal-record context with preserved sensor labels and provider-quality receipts.",
        "",
        f"The next legitimate step is to resolve all Phase 1 assets: {', '.join(blocked_assets)}. Only then may the pipeline construct risk sets, lock the 2024-2025 test inputs, and estimate the two central adjusted associations.",
        "",
        f"Shared descriptive years used for cross-source context: {', '.join(map(str, shared_years))}.",
        "",
    ]
    return "\n".join(lines)
