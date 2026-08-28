"""Download bounded ERA5-Land monthly condition inputs from CDS.

Credentials are read from the project ``.env`` (``cds_api_key``/``url``) when
present, otherwise by ``cdsapi`` from the local ``.cdsapirc`` file. The
default unit is one month so jobs can be resumed without re-requesting a
multi-year archive.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VARIABLES = [
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "2m_temperature",
    "2m_dewpoint_temperature",
    "total_precipitation",
    "volumetric_soil_water_layer_1",
    "volumetric_soil_water_layer_2",
    "volumetric_soil_water_layer_3",
]
TIMES = [f"{hour:02d}:00" for hour in range(24)]
DEFAULT_REQUEST_RETRIES = 2
DEFAULT_RETRY_DELAY_SECONDS = 30.0


def _read_project_env() -> dict[str, str]:
    """Read only simple KEY=VALUE pairs from the project .env.

    This deliberately does not print or persist credential values. The CDS
    profile screenshot uses a token-only key, so the accepted names include
    ``cds_api_key`` and ``key`` for this local project file. A normal
    ``.cdsapirc`` remains fully supported by cdsapi when no project key is
    present.
    """
    path = ROOT / ".env"
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[name.strip()] = value
    return values


def _make_cds_client(cdsapi: Any) -> tuple[Any, str]:
    local_env = _read_project_env()
    key = local_env.get("cds_api_key") or local_env.get("CDS_API_KEY") or local_env.get("key")
    url = local_env.get("cds_api_url") or local_env.get("CDSAPI_URL") or local_env.get("url")
    if key:
        return cdsapi.Client(url=url or "https://cds.climate.copernicus.eu/api", key=key), "project .env"
    return cdsapi.Client(), "cdsapirc/environment"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _retrieve_with_retries(
    client: Any,
    request: dict[str, Any],
    target: Path,
    *,
    request_retries: int = DEFAULT_REQUEST_RETRIES,
    retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
) -> None:
    """Submit a month-level job again when CDS marks a job failed.

    The ECMWF client already retries transient polling errors, but it raises
    on a terminal job failure (often a 400 response from ``/results``).  This
    outer retry handles that case.  Results are written to ``.part`` and
    atomically renamed only after a non-empty response exists, so a failed job
    can never masquerade as a complete NetCDF file on the next resume.
    """
    if request_retries < 0:
        raise ValueError("request_retries must be non-negative")
    if retry_delay_seconds < 0:
        raise ValueError("retry_delay_seconds must be non-negative")
    partial = target.with_name(target.name + ".part")
    attempts = request_retries + 1
    for attempt in range(1, attempts + 1):
        partial.unlink(missing_ok=True)
        try:
            client.retrieve("reanalysis-era5-land", request, str(partial))
            if not partial.is_file() or partial.stat().st_size <= 0:
                raise RuntimeError("CDS returned no non-empty payload")
            partial.replace(target)
            return
        except Exception as exc:
            partial.unlink(missing_ok=True)
            if attempt >= attempts:
                raise
            print(
                f"CDS month job failed ({type(exc).__name__}: {exc}); "
                f"resubmitting attempt {attempt + 1}/{attempts} after {retry_delay_seconds:g}s",
                flush=True,
            )
            time.sleep(retry_delay_seconds)


def run(
    year: int,
    months: list[str],
    output_root: Path,
    dry_run: bool,
    *,
    request_retries: int = DEFAULT_REQUEST_RETRIES,
    retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
) -> dict[str, Any]:
    client = None
    credential_source = "not_used_dry_run"
    if not dry_run:
        try:
            import cdsapi
        except ImportError as exc:
            raise SystemExit("Install the CDS client first: python -m pip install cdsapi") from exc
        client, credential_source = _make_cds_client(cdsapi)
    records: list[dict[str, Any]] = []
    manifest_path = output_root / "download_manifest.json"
    existing_records: dict[tuple[int, str], dict[str, Any]] = {}
    if manifest_path.is_file():
        try:
            previous = json.loads(manifest_path.read_text(encoding="utf-8"))
            for item in previous.get("records", []):
                if isinstance(item, dict) and "year" in item and "month" in item:
                    existing_records[(int(item["year"]), f"{int(item['month']):02d}")] = item
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            # A corrupt control-plane manifest must not hide payload files; the
            # new manifest below will be rebuilt from this request only.
            existing_records = {}
    for month in months:
        month_int = int(month)
        import calendar
        days = [f"{day:02d}" for day in range(1, calendar.monthrange(year, month_int)[1] + 1)]
        target = output_root / str(year) / f"era5_land_{year}_{month}.nc"
        target.parent.mkdir(parents=True, exist_ok=True)
        request = {
            "product_type": ["reanalysis"],
            "variable": VARIABLES,
            "year": [str(year)],
            "month": [month],
            "day": days,
            "time": TIMES,
            "area": [8, 109, -5, 120],  # north, west, south, east
            "data_format": "netcdf",
            "download_format": "unarchived",
        }
        if target.exists() and target.stat().st_size > 0:
            records.append({"year": year, "month": month, "status": "existing", "path": target.relative_to(ROOT).as_posix(), "sha256": sha256(target)})
            print(f"Skip existing {target}")
            continue
        print(f"Requesting ERA5-Land {year}-{month} ({len(days)} days × 24 hours) …")
        if dry_run:
            records.append({"year": year, "month": month, "status": "dry_run", "target": target.relative_to(ROOT).as_posix(), "request": request})
            continue
        assert client is not None
        try:
            _retrieve_with_retries(
                client,
                request,
                target,
                request_retries=request_retries,
                retry_delay_seconds=retry_delay_seconds,
            )
        except Exception as exc:
            message = str(exc)
            if "licence" in message.lower() or "license" in message.lower():
                raise SystemExit(
                    "CDS requires the ERA5-Land dataset licence to be accepted first. "
                    "Open https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=download#manage-licences, "
                    "accept the required licence, then rerun this command."
                ) from None
            raise
        records.append({"year": year, "month": month, "status": "downloaded", "path": target.relative_to(ROOT).as_posix(), "sha256": sha256(target)})
    merged_records = {**existing_records, **{(int(item["year"]), f"{int(item['month']):02d}"): item for item in records if "year" in item and "month" in item}}
    manifest = {
        "schema_version": "era5-land-download/v1",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": "reanalysis-era5-land",
        "source_url": "https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land?tab=documentation",
        "variables": VARIABLES,
        "area": [8, 109, -5, 120],
        "credential_source": credential_source,
        "records": [merged_records[key] for key in sorted(merged_records)],
        "time_basis": "CDS ERA5-Land UTC timestamps; event-level lagging is validated downstream.",
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Manifest: {manifest_path.relative_to(ROOT)}")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", action="append", dest="months", required=True, help="repeat for each month, e.g. --month 01 --month 02")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--request-retries", type=int, default=DEFAULT_REQUEST_RETRIES, help="month-level CDS resubmissions after a terminal job failure")
    parser.add_argument("--retry-delay-seconds", type=float, default=DEFAULT_RETRY_DELAY_SECONDS, help="delay between month-level CDS resubmissions")
    parser.add_argument("--output-root", type=Path, default=ROOT / "data" / "raw" / "era5_land")
    args = parser.parse_args()
    months = sorted({f"{int(value):02d}" for value in args.months})
    if any(int(value) < 1 or int(value) > 12 for value in months):
        parser.error("months must be between 01 and 12")
    run(
        args.year,
        months,
        args.output_root,
        args.dry_run,
        request_retries=args.request_retries,
        retry_delay_seconds=args.retry_delay_seconds,
    )


if __name__ == "__main__":
    main()
