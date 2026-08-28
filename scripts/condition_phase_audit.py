"""Audit the condition-specific peat vulnerability phase without network calls.

This audit is deliberately separate from the original accessibility Phase 1
gate.  It reports what can support a peat x condition interaction and what is
still blocked.  A present file is not automatically marked ready: payload,
timing, provenance, and the observation-opportunity requirement are checked
independently.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from wildfire_research.temporal_qa import run_temporal_qa

try:
    import rasterio
except ImportError:  # pragma: no cover - the workspace runtime includes rasterio
    rasterio = None


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "quality" / "condition_phase_audit.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def payload_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    if path.is_file():
        return [path] if path.stat().st_size > 0 else []
    # Control-plane manifests are evidence about an attempted request, not a
    # scientific payload. Never let a dry-run JSON make a missing input look
    # present.
    return sorted(
        candidate for candidate in path.rglob("*")
        if candidate.is_file()
        and candidate.stat().st_size > 0
        and candidate.suffix.lower() not in {".json", ".md", ".txt"}
    )


def _peat_check() -> dict[str, Any]:
    candidates = sorted((ROOT / "data" / "raw" / "peat" / "global").glob("*.tif"))
    if not candidates:
        return {"status": "blocked", "reason": "latest global peat raster is missing", "payload_file_count": 0}
    path = candidates[0]
    result: dict[str, Any] = {
        "status": "ready_for_sensitivity",
        "path": path.relative_to(ROOT).as_posix(),
        "payload_file_count": 1,
        "sha256": sha256(path),
        "reference_period": "2000-2020",
        "release_date": "2026-04-24",
        "not_2026_land_cover": True,
        "source_url": "https://zenodo.org/records/19731872",
        "license": "CC-BY-4.0",
    }
    if rasterio is None:
        result["reason"] = "rasterio unavailable; structural file check only"
        return result
    try:
        with rasterio.open(path) as dataset:
            result.update({
                "crs": str(dataset.crs),
                "width": dataset.width,
                "height": dataset.height,
                "resolution": [abs(dataset.transform.a), abs(dataset.transform.e)],
                "nodata": dataset.nodata,
                "dtype": dataset.dtypes[0],
            })
        if result["crs"] != "EPSG:4326":
            result["status"] = "blocked"
            result["reason"] = "peat raster is not EPSG:4326"
    except Exception as exc:  # pragma: no cover
        result["status"] = "blocked"
        result["reason"] = f"raster inspection failed: {type(exc).__name__}: {exc}"
    return result


def _drainage_check() -> dict[str, Any]:
    path = ROOT / "data" / "raw" / "peat_and_drainage" / "dadap_2017_geotiffs.zip"
    if not path.is_file() or path.stat().st_size == 0:
        return {"status": "blocked", "reason": "Dadap 2017 canal sensitivity archive is missing", "payload_file_count": 0}
    try:
        with zipfile.ZipFile(path) as archive:
            members = [name for name in archive.namelist() if not name.endswith("/")]
        return {
            "status": "usable_sensitivity",
            "path": path.relative_to(ROOT).as_posix(),
            "payload_file_count": 1,
            "member_count": len(members),
            "sha256": sha256(path),
            "source_reference_year": 2017,
            "not_a_2014_baseline": True,
            "not_a_construction_timing_series": True,
            "source_url": "https://purl.stanford.edu/yj761xk5815",
            "license": "CC-BY-3.0",
        }
    except (OSError, zipfile.BadZipFile) as exc:
        return {"status": "blocked", "reason": f"drainage archive invalid: {exc}", "payload_file_count": 0}


def _missing_check(asset_id: str, expected: str, role: str, next_action: str) -> dict[str, Any]:
    path = ROOT / expected
    files = payload_files(path)
    if files:
        return {
            "status": "present_needs_temporal_validation",
            "path": expected,
            "payload_file_count": len(files),
            "role": role,
            "next_action": next_action,
            "sha256_first_payload": sha256(files[0]),
        }
    return {"status": "blocked", "path": expected, "payload_file_count": 0, "role": role, "next_action": next_action}


def run() -> dict[str, Any]:
    temporal_support = run_temporal_qa(ROOT)
    assets = {
        "peat_baseline": _peat_check(),
        "drainage_sensitivity": _drainage_check(),
        "viirs_outcome_and_opportunity": _missing_check(
            "viirs", "data/raw/viirs", "required denominator and outcome", "Earthdata account; freeze VNP14IMG.002 + VNP03IMG.002 paired swaths and processed negatives",
        ),
        "era5_land": _missing_check(
            "era5", "data/raw/era5_land", "soil moisture, VPD, wind, rainfall", "CDS account; request hourly variables with UTC/time/bounds metadata",
        ),
        "chirps": _missing_check(
            "chirps", "data/raw/chirps", "antecedent rainfall and drought", "Download final/RNL daily COGs; derive 1/7/30/90-day lagged rainfall",
        ),
        "prefire_vegetation": _missing_check(
            "vegetation", "data/raw/mod13q1", "prefire EVI; HLS NDMI sensitivity", "Earthdata account; freeze QA mask and ensure composite support ends before event",
        ),
        "dated_access": _missing_check(
            "access", "data/raw/historical_access", "dated road/settlement exposure for original hypothesis", "Obtain authoritative dated construction source; OSM remains sensitivity only",
        ),
    }
    # Keep this condition-specific audit synchronized with temporal QA.  A
    # payload directory alone is not enough, but the report should distinguish
    # a complete ERA5 study window from an unvalidated vegetation inventory.
    era5_qa = temporal_support["assets"]["era5_land"]
    if era5_qa.get("status") == "study_window_complete":
        assets["era5_land"].update({
            "status": "ready_for_lag_derivation",
            "next_action": "derive event-cutoff VPD, wind, rainfall, and soil-water lags",
        })
    chirps_qa = temporal_support["assets"]["chirps"]
    if chirps_qa.get("status") in {"support_window_complete_with_extra_dates", "support_window_and_partial_lags_complete"}:
        assets["chirps"].update({
            "status": "present_needs_lag_derivation",
            "next_action": "derive complete 1/7/30/90-day rainfall lags and expand beyond the 2015 support window",
        })
    vegetation_qa = temporal_support["assets"]["prefire_vegetation"]
    if vegetation_qa.get("status") == "payload_inventory_only_qa_unvalidated":
        assets["prefire_vegetation"].update({
            "status": "present_needs_qa_and_timing",
            "next_action": "extract QA SDS and enforce pre-fire composite timing",
        })
    required = ("peat_baseline", "viirs_outcome_and_opportunity", "era5_land", "chirps", "prefire_vegetation")
    condition_phase_ready = all(assets[key]["status"] in {"ready", "present_needs_temporal_validation"} for key in required)
    condition_phase_ready = condition_phase_ready and assets["viirs_outcome_and_opportunity"]["status"] == "ready"
    result = {
        "schema_version": "condition-phase-audit/v1",
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "peat x dry-hydrology/drainage/vegetation-stress interaction; separate from original access/transformation estimand",
        "condition_phase_ready": condition_phase_ready,
        "status": "ready_for_design_matrix" if condition_phase_ready else "blocked_missing_or_unvalidated_inputs",
        "assets": assets,
        "temporal_support_qa": temporal_support,
        "required_interactions": [
            "peat x low soil moisture",
            "peat x drainage/canal proximity",
            "peat x low prefire NDMI/EVI",
            "peat x rainfall deficit/high VPD/wind",
        ],
        "acceptance_rules": [
            "Fire outcome must have processed non-detection opportunities, not only positive points.",
            "All condition variables must be measured before the fire observation cutoff.",
            "Peat baseline is a static 2000-2020 reference, not a 2026 land-cover observation.",
            "Dadap 2017 canals are sensitivity/mediator evidence, not a dated 2014 construction series.",
            "Do not unlock the original Phase 1 access/transformation model from this condition audit.",
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, ensure_ascii=False))
