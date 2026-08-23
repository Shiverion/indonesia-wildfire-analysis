"""Aggregate a downloaded NASA FIRMS NRT global day to country and Indonesia ADM1 units.

This deliberately produces a country-level snapshot for the browser. It does
not publish latitude/longitude, acquisition times, or individual detections.
The result is a descriptive positive-detection count, not a fire occurrence
rate: satellite observation opportunity is not available in this snapshot.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "data" / "raw" / "firms" / "nrt_global"
DERIVED_ROOT = ROOT / "data" / "derived" / "firms_global"
QUALITY_ROOT = ROOT / "outputs" / "quality" / "firms_global_nrt"
GEOMETRY = ROOT / "apps" / "evidence-explorer" / "public" / "geo" / "global-countries.geojson"
INDONESIA_GEOMETRY = ROOT / "apps" / "evidence-explorer" / "public" / "geo" / "indonesia-adm1.geojson"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def aggregate(snapshot_date: str) -> dict[str, Any]:
    raw_dir = RAW_ROOT / snapshot_date
    metadata_path = QUALITY_ROOT / f"{snapshot_date}.json"
    if not raw_dir.is_dir() or not metadata_path.is_file():
        raise FileNotFoundError(f"Downloaded snapshot is missing: {raw_dir}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    frames: list[pd.DataFrame] = []
    sensor_files: list[dict[str, Any]] = []
    sensor_specs = metadata.get("sensors")
    if not sensor_specs:
        filename_prefixes = {
            "MODIS": "MODIS_C6_1_Global_MCD14DL_NRT_",
            "VIIRS_NOAA20": "J1_VIIRS_C2_Global_VJ114IMGTDL_NRT_",
            "VIIRS_NOAA21": "J2_VIIRS_C2_Global_VJ214IMGTDL_NRT_",
            "VIIRS_SNPP": "SUOMI_VIIRS_C2_Global_VNP14IMGTDL_NRT_",
        }
        sensor_specs = [
            {"sensor": sensor, "path": str(next(raw_dir.glob(f"{prefix}*.txt")).relative_to(ROOT))}
            for sensor, prefix in filename_prefixes.items()
        ]
    for item in sensor_specs:
        path = ROOT / item["path"]
        frame = pd.read_csv(path, usecols=lambda column: column in {"latitude", "longitude", "confidence"})
        frame["sensor"] = item["sensor"]
        frames.append(frame)
        sensor_files.append({"sensor": item["sensor"], "bytes": path.stat().st_size, "sha256": sha256(path)})
    detections = pd.concat(frames, ignore_index=True)
    detections["latitude"] = pd.to_numeric(detections["latitude"], errors="coerce")
    detections["longitude"] = pd.to_numeric(detections["longitude"], errors="coerce")
    detections = detections.dropna(subset=["latitude", "longitude"])
    detections = detections[detections["latitude"].between(-90, 90) & detections["longitude"].between(-180, 180)]

    countries = gpd.read_file(GEOMETRY)[["country_id", "country_name", "geometry"]]
    points = gpd.GeoDataFrame(
        detections,
        geometry=gpd.points_from_xy(detections["longitude"], detections["latitude"]),
        crs="EPSG:4326",
    )
    joined = gpd.sjoin(points, countries, how="left", predicate="within")
    joined["country_id"] = joined["country_id"].fillna("")
    joined["country_name"] = joined["country_name"].fillna("")

    by_country = joined.groupby(["country_id", "country_name"], dropna=False).size().to_dict()
    by_sensor = joined.groupby(["country_id", "sensor"], dropna=False).size().to_dict()
    matched_point_count = int((joined["country_id"] != "").sum())
    country_rows: list[dict[str, Any]] = []
    for row in countries[["country_id", "country_name"]].drop_duplicates().itertuples(index=False):
        country_id = str(row.country_id)
        country_name = str(row.country_name)
        country_rows.append({
            "country_id": country_id,
            "country": country_name,
            "positive_detection_count": int(by_country.get((country_id, country_name), 0)),
            "modis_count": int(by_sensor.get((country_id, "MODIS"), 0)),
            "viirs_noaa20_count": int(by_sensor.get((country_id, "VIIRS_NOAA20"), 0)),
            "viirs_noaa21_count": int(by_sensor.get((country_id, "VIIRS_NOAA21"), 0)),
            "viirs_snpp_count": int(by_sensor.get((country_id, "VIIRS_SNPP"), 0)),
            "status": "zero_returned_positive_detection" if int(by_country.get((country_id, country_name), 0)) == 0 else "positive_detection_records",
        })

    indonesia = gpd.read_file(INDONESIA_GEOMETRY)[["province_id", "province", "geometry"]]
    province_joined = gpd.sjoin(points, indonesia, how="left", predicate="within")
    province_joined["province_id"] = province_joined["province_id"].fillna("")
    province_joined["province"] = province_joined["province"].fillna("")
    by_province = province_joined.groupby(["province_id", "province"], dropna=False).size().to_dict()
    by_province_sensor = province_joined.groupby(["province_id", "sensor"], dropna=False).size().to_dict()
    matched_indonesia_point_count = int((province_joined["province_id"] != "").sum())
    province_rows: list[dict[str, Any]] = []
    for row in indonesia[["province_id", "province"]].drop_duplicates().itertuples(index=False):
        province_id = str(row.province_id)
        province_name = str(row.province)
        count = int(by_province.get((province_id, province_name), 0))
        province_rows.append({
            "province_id": province_id,
            "province": province_name,
            "positive_detection_count": count,
            "modis_count": int(by_province_sensor.get((province_id, "MODIS"), 0)),
            "viirs_noaa20_count": int(by_province_sensor.get((province_id, "VIIRS_NOAA20"), 0)),
            "viirs_noaa21_count": int(by_province_sensor.get((province_id, "VIIRS_NOAA21"), 0)),
            "viirs_snpp_count": int(by_province_sensor.get((province_id, "VIIRS_SNPP"), 0)),
            "status": "zero_returned_positive_detection" if count == 0 else "positive_detection_records",
        })

    DERIVED_ROOT.mkdir(parents=True, exist_ok=True)
    derived_path = DERIVED_ROOT / f"{snapshot_date}_country.csv"
    with derived_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(country_rows[0]))
        writer.writeheader()
        writer.writerows(country_rows)
    province_derived_path = DERIVED_ROOT / f"{snapshot_date}_indonesia_province.csv"
    with province_derived_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(province_rows[0]))
        writer.writeheader()
        writer.writerows(province_rows)

    status = {
        "schema_version": "firms-global-nrt-country/v1",
        "status": "validated_closed_day_aggregate",
        "snapshot_date": snapshot_date,
        "retrieved_at_utc": metadata.get("retrieved_at_utc"),
        "aggregation_completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "date_basis": "NASA FIRMS NRT portal acquisition date; closed UTC day",
        "metric": "positive FIRMS active-fire detection records",
        "source_url": metadata.get("source_url"),
        "sensor_files": sensor_files,
        "country_geometry": {
            "path": GEOMETRY.relative_to(ROOT).as_posix(),
            "sha256": sha256(GEOMETRY),
            "feature_count": len(countries),
        },
        "indonesia_province_geometry": {
            "path": INDONESIA_GEOMETRY.relative_to(ROOT).as_posix(),
            "sha256": sha256(INDONESIA_GEOMETRY),
            "feature_count": len(indonesia),
            "boundary_year_represented": 2017,
        },
        "raw_record_count": int(len(detections)),
        "matched_point_count": matched_point_count,
        "unmatched_point_count": int(len(detections) - matched_point_count),
        "positive_country_count": int(sum(row["positive_detection_count"] > 0 for row in country_rows)),
        "country_count": len(country_rows),
        "sensor_record_counts": {sensor: int((detections["sensor"] == sensor).sum()) for sensor in sorted(detections["sensor"].unique())},
        "derived_path": derived_path.relative_to(ROOT).as_posix(),
        "derived_sha256": sha256(derived_path),
        "indonesia_province_derived_path": province_derived_path.relative_to(ROOT).as_posix(),
        "indonesia_province_derived_sha256": sha256(province_derived_path),
        "indonesia_province_count": len(province_rows),
        "indonesia_province_positive_count": int(sum(row["positive_detection_count"] > 0 for row in province_rows)),
        "indonesia_matched_point_count": matched_indonesia_point_count,
        "raw_records_embedded": False,
        "has_observation_denominator": False,
        "interpretation": "Counts are positive satellite detection records, not unique fires, burned area, fire rates, or no-fire evidence.",
    }
    metadata_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True, help="snapshot date, YYYY-MM-DD")
    args = parser.parse_args()
    status = aggregate(args.date)
    print(json.dumps(status, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
