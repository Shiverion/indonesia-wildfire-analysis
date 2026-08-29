#!/usr/bin/env python3
"""Extract only registered prior-year AlphaEarth summaries for existing cells.

The default mode performs a bounded smoke test. Pass ``--full`` to process all
registered cell-years. Full-mode chunks are written atomically and skipped on
subsequent runs, so an interruption can be resumed without repeating completed
Earth Engine requests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import ee
import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import transform

from wildfire_research.alphaearth import (
    ALPHAEARTH_BANDS,
    build_cell_year_index,
    normalize_embedding_rows,
)


ROOT = Path(__file__).resolve().parents[1]
REGISTRATION_PATH = ROOT / "config" / "ppe_alphaearth_registration.json"
FEATURE_GATE_PATH = ROOT / "outputs" / "quality" / "ppe_feature_gate.json"
OPPORTUNITY_PATH = ROOT / "data" / "derived" / "viirs" / "opportunity_frame.csv"
PRIVATE_CELL_PATH = (
    ROOT / "data" / "derived" / "phase3" / "phase3_cell_centres_private.csv"
)
FOREST_GRID_PATH = (
    ROOT
    / "data"
    / "derived"
    / "mapbiomas"
    / "mapbiomas_c41_forest_fraction_1km_kalimantan.tif"
)
OUTPUT_PATH = (
    ROOT / "data" / "derived" / "ppe" / "alphaearth_prefire_embeddings_private.csv"
)
PARTS_DIR = ROOT / "data" / "derived" / "ppe" / "alphaearth_chunks_private"
RECEIPT_PATH = ROOT / "outputs" / "quality" / "alphaearth_prefire_export.json"
SMOKE_PATH = ROOT / "outputs" / "quality" / "alphaearth_prefire_smoke_test.json"
COLLECTION = "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL"
DEFAULT_PROJECT = "susenas-project"
ALGORITHM_REVISION = "alphaearth-prefire-polygon-mean-v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected an object in {path}")
    return value


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def validate_locked_inputs() -> tuple[dict[str, Any], pd.DataFrame]:
    registration = read_json(REGISTRATION_PATH)
    if registration.get("status") != "frozen_before_embedding_extraction":
        raise ValueError("AlphaEarth registration is not frozen")
    feature_gate = read_json(FEATURE_GATE_PATH)
    if feature_gate.get("ready") is not True:
        raise ValueError("PPE feature gate has not passed")

    opportunities = pd.read_csv(
        OPPORTUNITY_PATH,
        usecols=["cell_id", "acquisition_utc"],
        dtype={"cell_id": "string"},
    )
    cells = pd.read_csv(
        PRIVATE_CELL_PATH,
        usecols=["cell_id", "grid_row", "grid_col"],
        dtype={"cell_id": "string"},
    )
    years = registration["temporal_lock"]["eligible_event_years"]
    requests = build_cell_year_index(opportunities, cells, years)
    documented = set(registration["alphaearth_source"]["documented_years_used"])
    requested = set(requests["embedding_year"].astype(int))
    if not requested.issubset(documented):
        raise ValueError(
            f"requested embedding years are outside the documented lock: {sorted(requested - documented)}"
        )
    return registration, requests


def exact_polygon_records(records: pd.DataFrame) -> list[list[Any]]:
    """Reconstruct exact 1-km equal-area cells and return ephemeral lon/lat rings."""

    with rasterio.open(FOREST_GRID_PATH) as source:
        expected_transform = (1000.0, 0.0, 10516000.0, 0.0, -1000.0, 765000.0)
        if tuple(source.transform)[:6] != expected_transform:
            raise ValueError("registered forest grid transform changed unexpectedly")
        xs: list[float] = []
        ys: list[float] = []
        metadata: list[tuple[str, str, int, int]] = []
        for row in records.itertuples(index=False):
            x = source.transform.c + (int(row.grid_col) + 0.5) * source.transform.a
            y = source.transform.f + (int(row.grid_row) + 0.5) * source.transform.e
            xs.extend([x - 500, x + 500, x + 500, x - 500, x - 500])
            ys.extend([y - 500, y - 500, y + 500, y + 500, y - 500])
            metadata.append(
                (str(row.record_id), str(row.cell_id), int(row.event_year), int(row.embedding_year))
            )
        longitudes, latitudes = transform(source.crs, "EPSG:4326", xs, ys)

    output: list[list[Any]] = []
    for index, values in enumerate(metadata):
        start = index * 5
        ring = [
            [float(longitudes[offset]), float(latitudes[offset])]
            for offset in range(start, start + 5)
        ]
        output.append([*values, *ring])
    return output


def make_polygons(records: pd.DataFrame) -> ee.FeatureCollection:
    rows = exact_polygon_records(records)

    def to_feature(value: ee.ComputedObject) -> ee.Feature:
        row = ee.List(value)
        ring = ee.List([row.get(4), row.get(5), row.get(6), row.get(7), row.get(8)])
        geometry = ee.Geometry.Polygon(ee.List([ring]), "EPSG:4326", False)
        return ee.Feature(
            geometry,
            {
                "record_id": row.get(0),
                "cell_id": row.get(1),
                "event_year": row.get(2),
                "embedding_year": row.get(3),
            },
        )

    return ee.FeatureCollection(ee.List(rows).map(to_feature))


def build_reduction(records: pd.DataFrame, scale_m: int) -> ee.FeatureCollection:
    pieces: list[ee.FeatureCollection] = []
    for embedding_year, group in records.groupby("embedding_year", sort=True):
        polygons = make_polygons(group)
        image = (
            ee.ImageCollection(COLLECTION)
            .filterDate(f"{int(embedding_year)}-01-01", f"{int(embedding_year) + 1}-01-01")
            .filterBounds(polygons.geometry())
            .mosaic()
            .select(list(ALPHAEARTH_BANDS))
        )
        pieces.append(
            image.reduceRegions(
                collection=polygons,
                reducer=ee.Reducer.mean(),
                scale=scale_m,
                tileScale=8,
            )
        )
    combined = pieces[0]
    for piece in pieces[1:]:
        combined = combined.merge(piece)
    selectors = [
        "record_id",
        "cell_id",
        "event_year",
        "embedding_year",
        *ALPHAEARTH_BANDS,
    ]
    return combined.select(selectors, retainGeometry=False)


def download_chunk(records: pd.DataFrame, scale_m: int) -> pd.DataFrame:
    selectors = [
        "record_id",
        "cell_id",
        "event_year",
        "embedding_year",
        *ALPHAEARTH_BANDS,
    ]
    result = ee.data.computeFeatures(
        {
            "expression": build_reduction(records, scale_m),
            "fileFormat": "PANDAS_DATAFRAME",
            "pageSize": 500,
            "workloadTag": "alphaearth-prefire-cell-year",
        }
    )
    missing = sorted(set(selectors) - set(result.columns))
    if missing:
        raise ValueError(f"Earth Engine result missing columns: {missing}")
    result = normalize_embedding_rows(result[selectors].copy())
    expected = set(records["record_id"].astype(str))
    found = set(result["record_id"].astype(str))
    if found != expected:
        raise ValueError(
            f"Earth Engine record mismatch: missing={len(expected - found)}, unexpected={len(found - expected)}"
        )
    return result.sort_values("record_id", ignore_index=True)


def select_smoke_records(records: pd.DataFrame, per_year: int) -> pd.DataFrame:
    return (
        records.groupby("embedding_year", sort=True, group_keys=False)
        .head(per_year)
        .reset_index(drop=True)
    )


def run_smoke(args: argparse.Namespace, records: pd.DataFrame) -> int:
    sample = select_smoke_records(records, args.smoke_per_year)
    started = time.monotonic()
    result = download_with_retry(sample, args.scale_m, args.max_attempts)
    norms = np.linalg.norm(result[list(ALPHAEARTH_BANDS)].to_numpy(float), axis=1)
    receipt = {
        "schema_version": "alphaearth-prefire-smoke/v1",
        "algorithm_revision": ALGORITHM_REVISION,
        "generated_at_utc": utc_now(),
        "status": "pass",
        "project": args.project,
        "collection": COLLECTION,
        "scale_m": args.scale_m,
        "record_count": int(len(result)),
        "records_by_embedding_year": {
            str(int(year)): int(count)
            for year, count in result.groupby("embedding_year").size().items()
        },
        "band_count": len(ALPHAEARTH_BANDS),
        "minimum_normalized_l2_norm": float(norms.min()),
        "maximum_normalized_l2_norm": float(norms.max()),
        "all_years_equal_event_year_minus_one": bool(
            (result["embedding_year"].astype(int) == result["event_year"].astype(int) - 1).all()
        ),
        "duration_seconds": round(time.monotonic() - started, 2),
        "row_level_values_recorded": False,
        "coordinates_recorded": False,
    }
    write_json_atomic(SMOKE_PATH, receipt)
    print(json.dumps(receipt, indent=2))
    return 0


def download_with_retry(
    records: pd.DataFrame, scale_m: int, max_attempts: int
) -> pd.DataFrame:
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return download_chunk(records, scale_m)
        except Exception as exc:  # Earth Engine raises several transport exception types.
            last_error = exc
            if attempt == max_attempts:
                break
            time.sleep(min(60, 2 ** attempt))
    assert last_error is not None
    raise last_error


def part_path(index: int) -> Path:
    return PARTS_DIR / f"chunk_{index:04d}.csv"


def validate_existing_part(path: Path, expected: pd.DataFrame) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype={"record_id": "string", "cell_id": "string"})
    frame = normalize_embedding_rows(frame)
    if set(frame["record_id"].astype(str)) != set(expected["record_id"].astype(str)):
        raise ValueError(f"existing part does not match its registered chunk: {path}")
    return frame


def run_full(args: argparse.Namespace, records: pd.DataFrame) -> int:
    PARTS_DIR.mkdir(parents=True, exist_ok=True)
    chunks = [
        records.iloc[start : start + args.chunk_size].copy()
        for start in range(0, len(records), args.chunk_size)
    ]
    completed = 0
    for index, chunk in enumerate(chunks):
        path = part_path(index)
        if path.is_file():
            validate_existing_part(path, chunk)
            completed += 1
            continue
        result = download_with_retry(chunk, args.scale_m, args.max_attempts)
        temporary = path.with_suffix(".csv.tmp")
        result.to_csv(temporary, index=False, float_format="%.10g")
        temporary.replace(path)
        completed += 1
        write_full_receipt(args, records, len(chunks), completed, "active")
        print(f"AlphaEarth chunks: {completed}/{len(chunks)}", flush=True)

    parts = [validate_existing_part(part_path(i), chunk) for i, chunk in enumerate(chunks)]
    final = pd.concat(parts, ignore_index=True)
    if len(final) != len(records) or final["record_id"].astype(str).duplicated().any():
        raise ValueError("combined AlphaEarth table has invalid cell-year coverage")
    final = final.sort_values(["embedding_year", "cell_id"], ignore_index=True)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT_PATH.with_suffix(".csv.tmp")
    final.to_csv(temporary, index=False, float_format="%.10g")
    temporary.replace(OUTPUT_PATH)
    if not args.keep_parts:
        for index in range(len(chunks)):
            path = part_path(index)
            if path.is_file():
                path.unlink()
        if PARTS_DIR.is_dir() and not any(PARTS_DIR.iterdir()):
            PARTS_DIR.rmdir()
    write_full_receipt(args, records, len(chunks), completed, "complete")
    print(f"Complete: {OUTPUT_PATH} ({len(final):,} rows)")
    return 0


def write_full_receipt(
    args: argparse.Namespace,
    records: pd.DataFrame,
    chunk_count: int,
    completed_chunks: int,
    status: str,
) -> None:
    output = None
    if OUTPUT_PATH.is_file():
        output = {
            "path": str(OUTPUT_PATH.relative_to(ROOT)).replace("\\", "/"),
            "size_bytes": OUTPUT_PATH.stat().st_size,
            "sha256": sha256_file(OUTPUT_PATH),
        }
    receipt = {
        "schema_version": "alphaearth-prefire-export/v1",
        "algorithm_revision": ALGORITHM_REVISION,
        "updated_at_utc": utc_now(),
        "status": status,
        "project": args.project,
        "collection": COLLECTION,
        "scale_m": args.scale_m,
        "registered_record_count": int(len(records)),
        "records_by_event_year": {
            str(int(year)): int(count)
            for year, count in records.groupby("event_year").size().items()
        },
        "chunk_size": args.chunk_size,
        "chunk_count": chunk_count,
        "completed_chunks": completed_chunks,
        "resumable": True,
        "chunk_parts_retained_after_completion": bool(args.keep_parts),
        "registration_sha256": sha256_file(REGISTRATION_PATH),
        "feature_gate_sha256": sha256_file(FEATURE_GATE_PATH),
        "output": output,
        "row_level_values_recorded_in_receipt": False,
        "coordinates_recorded_in_receipt": False,
    }
    write_json_atomic(RECEIPT_PATH, receipt)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--smoke-per-year", type=int, default=2)
    parser.add_argument("--chunk-size", type=int, default=250)
    parser.add_argument("--scale-m", type=int, default=100)
    parser.add_argument("--max-attempts", type=int, default=4)
    parser.add_argument(
        "--keep-parts",
        action="store_true",
        help="Retain restart chunks after the validated final table is written.",
    )
    args = parser.parse_args()
    if args.smoke_per_year < 1 or args.smoke_per_year > 10:
        parser.error("--smoke-per-year must be between 1 and 10")
    if args.chunk_size < 25 or args.chunk_size > 500:
        parser.error("--chunk-size must be between 25 and 500")
    if args.scale_m < 10 or args.scale_m > 500:
        parser.error("--scale-m must be between 10 and 500")
    if args.max_attempts < 1 or args.max_attempts > 10:
        parser.error("--max-attempts must be between 1 and 10")

    ee.Initialize(project=args.project)
    _, records = validate_locked_inputs()
    if args.full:
        return run_full(args, records)
    return run_smoke(args, records)


if __name__ == "__main__":
    raise SystemExit(main())
