#!/usr/bin/env python3
"""Run and resume the compact Phase 3 MapBiomas extraction in Earth Engine.

The runner sends exact locked 1 km polygons transiently, reduces each annual
pre/post pair to a class-transition histogram, and stores only coordinate-free
chunk tables in private Earth Engine assets. Histograms are expanded locally
into the registered 307-column model input. No paid object storage or national
raster-stack download is used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import ee
import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import transform

from phase3_land_change import (
    DESTINATIONS,
    FOREST_GRID_PATH,
    REGISTRATION_PATH,
    TRANSITION_SUMMARY_PATH,
    expected_transition_columns,
    read_json,
)


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_CELL_PATH = (
    ROOT / "data" / "derived" / "phase3" / "phase3_cell_centres_private.csv"
)
RECEIPT_PATH = ROOT / "outputs" / "quality" / "phase3_earthengine_export.json"
DEFAULT_PROJECT = "susenas-project"
DEFAULT_FOLDER = "projects/susenas-project/assets/indonesia_wildfire_analysis"
DEFAULT_ASSET_PREFIX = DEFAULT_FOLDER + "/mapbiomas_c41_phase3_histogram_chunk"
MAPBIOMAS_ASSET = (
    "projects/mapbiomas-public/assets/indonesia/lulc/collection4/"
    "mapbiomas_indonesia_collection4_coverage_v2"
)
ALGORITHM_REVISION = "phase3-ee-transition-histograms-v3"
NATURAL_CODES = {3, 5, 76}
NOT_OBSERVED_CODES = {0, 27}
TERMINAL_SUCCESS = {"COMPLETED", "SUCCEEDED"}
TERMINAL_FAILURE = {"CANCELLED", "FAILED"}
DESTINATION_CODES = {
    "nonforest_natural": {13},
    "rice_paddy": {40},
    "oil_palm": {35},
    "pulpwood_plantation": {9},
    "other_agriculture": {21},
    "mining": {30},
    "urban": {24},
    "other_nonvegetated": {25},
    "aquaculture": {31},
    "water": {33},
}

if tuple(DESTINATION_CODES) != DESTINATIONS:
    raise RuntimeError("Phase 3 destination order is inconsistent")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_receipt(value: dict[str, Any]) -> None:
    RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = RECEIPT_PATH.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    temporary.replace(RECEIPT_PATH)


def read_receipt() -> dict[str, Any]:
    if not RECEIPT_PATH.is_file():
        return {}
    value = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def asset_exists(asset_id: str) -> bool:
    try:
        ee.data.getAsset(asset_id)
    except ee.EEException:
        return False
    return True


def ensure_private_folder(folder_id: str) -> None:
    if not asset_exists(folder_id):
        ee.data.createAsset({"type": "FOLDER"}, folder_id)


def validate_sources(registration: dict[str, Any]) -> tuple[pd.DataFrame, list[str]]:
    if not PRIVATE_CELL_PATH.is_file():
        raise FileNotFoundError(PRIVATE_CELL_PATH)
    cells = pd.read_csv(PRIVATE_CELL_PATH, dtype={"cell_id": "string"})
    required = {"grid_row", "grid_col", "cell_id", "longitude", "latitude"}
    missing = sorted(required - set(cells.columns))
    if missing:
        raise ValueError(f"Private cell table is missing columns: {missing}")
    if cells["cell_id"].duplicated().any():
        raise ValueError("Private cell table contains duplicate cell_id values")
    if cells[list(required)].isna().any().any():
        raise ValueError("Private cell table contains missing required values")
    if not cells["longitude"].between(-180, 180).all():
        raise ValueError("Private cell table contains invalid longitude")
    if not cells["latitude"].between(-90, 90).all():
        raise ValueError("Private cell table contains invalid latitude")

    band_names = ee.Image(MAPBIOMAS_ASSET).bandNames().getInfo()
    expected_bands = [f"classification_{year}" for year in range(1990, 2025)]
    missing_bands = sorted(set(expected_bands) - set(band_names))
    if missing_bands:
        raise ValueError(f"MapBiomas asset is missing bands: {missing_bands}")
    return cells, expected_transition_columns(registration)


def transition_specs(registration: dict[str, Any]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    event_years = registration["time_alignment"]["eligible_event_years_by_horizon"]
    for horizon_text, years in event_years.items():
        horizon = int(horizon_text)
        for event_year in years:
            specs.append(
                {
                    "event_year": int(event_year),
                    "horizon": horizon,
                    "pre_year": int(event_year) - 1,
                    "post_year": int(event_year) + horizon,
                    "property": f"transition_{event_year}_h{horizon}",
                }
            )
    return specs


def exact_polygon_records(cells: pd.DataFrame) -> list[list[Any]]:
    with rasterio.open(FOREST_GRID_PATH) as source:
        expected_transform = (
            1000.0,
            0.0,
            10516000.0,
            0.0,
            -1000.0,
            765000.0,
        )
        if tuple(source.transform)[:6] != expected_transform:
            raise ValueError("Registered forest grid transform changed unexpectedly")
        xs: list[float] = []
        ys: list[float] = []
        ids: list[str] = []
        for row in cells.itertuples(index=False):
            x = source.transform.c + (int(row.grid_col) + 0.5) * source.transform.a
            y = source.transform.f + (int(row.grid_row) + 0.5) * source.transform.e
            xs.extend([x - 500, x + 500, x + 500, x - 500, x - 500])
            ys.extend([y - 500, y - 500, y + 500, y + 500, y - 500])
            ids.append(str(row.cell_id))
        longitudes, latitudes = transform(source.crs, "EPSG:4326", xs, ys)

    records: list[list[Any]] = []
    for index, cell_id in enumerate(ids):
        start = index * 5
        ring = [
            [float(longitudes[offset]), float(latitudes[offset])]
            for offset in range(start, start + 5)
        ]
        records.append([cell_id, *ring])
    return records


def make_private_polygons(cells: pd.DataFrame) -> ee.FeatureCollection:
    records = exact_polygon_records(cells)

    def to_feature(value: ee.ComputedObject) -> ee.Feature:
        row = ee.List(value)
        ring = ee.List([row.get(1), row.get(2), row.get(3), row.get(4), row.get(5)])
        geometry = ee.Geometry.Polygon(ee.List([ring]), "EPSG:4326", False)
        return ee.Feature(geometry, {"cell_id": row.get(0)})

    return ee.FeatureCollection(ee.List(records).map(to_feature))


def build_transition_image(specs: list[dict[str, Any]]) -> ee.Image:
    land_cover = ee.Image(MAPBIOMAS_ASSET)
    bands = []
    for spec in specs:
        pre = land_cover.select(f"classification_{spec['pre_year']}").unmask(0)
        post = land_cover.select(f"classification_{spec['post_year']}").unmask(0)
        bands.append(
            pre.multiply(100)
            .add(post)
            .toInt16()
            .rename(str(spec["property"]))
        )
    return ee.Image.cat(bands)


def expand_transition_histograms(
    reduced: ee.FeatureCollection,
    specs: list[dict[str, Any]],
    selectors: list[str],
) -> ee.FeatureCollection:
    metric_names = [
        "total",
        "pre_observed",
        "post_observed",
        "pre_natural",
        "loss",
        *[f"to_{destination}" for destination in DESTINATIONS],
    ]
    initial_metrics = ee.Dictionary({name: 0 for name in metric_names})

    def expand(feature_value: ee.ComputedObject) -> ee.Feature:
        feature = ee.Feature(feature_value)
        output = ee.Dictionary({"cell_id": feature.get("cell_id")})
        for spec in specs:
            histogram = ee.Dictionary(feature.get(str(spec["property"])))

            def accumulate(key_value: ee.ComputedObject, state: ee.ComputedObject) -> ee.Dictionary:
                key = ee.String(key_value)
                count = ee.Number(histogram.get(key))
                packed_code = ee.Number.parse(key)
                pre_code = packed_code.divide(100).floor()
                post_code = packed_code.mod(100)
                pre_observed = pre_code.neq(0).And(pre_code.neq(27))
                post_observed = post_code.neq(0).And(post_code.neq(27))
                pre_natural = pre_code.eq(3).Or(pre_code.eq(5)).Or(pre_code.eq(76))
                post_natural = post_code.eq(3).Or(post_code.eq(5)).Or(post_code.eq(76))
                valid_pair = pre_observed.And(post_observed)
                metrics = ee.Dictionary(state)

                def add_if(name: str, condition: ee.ComputedObject) -> ee.Dictionary:
                    increment = ee.Number(ee.Algorithms.If(condition, count, 0))
                    return metrics.set(name, ee.Number(metrics.get(name)).add(increment))

                metrics = metrics.set("total", ee.Number(metrics.get("total")).add(count))
                metrics = add_if("pre_observed", pre_observed)
                metrics = add_if("post_observed", post_observed)
                metrics = add_if("pre_natural", pre_natural.And(pre_observed))
                metrics = add_if(
                    "loss", pre_natural.And(post_natural.Not()).And(valid_pair)
                )
                for destination, codes in DESTINATION_CODES.items():
                    destination_code = next(iter(codes))
                    metrics = add_if(
                        f"to_{destination}",
                        pre_natural.And(post_code.eq(destination_code)).And(valid_pair),
                    )
                return metrics

            metrics = ee.Dictionary(
                histogram.keys().iterate(accumulate, initial_metrics)
            )
            total = ee.Number(metrics.get("total"))
            event_year = int(spec["event_year"])
            horizon = int(spec["horizon"])
            if horizon == 1:
                output = output.set(
                    f"pre_natural_fraction_{event_year}",
                    ee.Number(metrics.get("pre_natural")).divide(total),
                )
                output = output.set(
                    f"pre_observed_fraction_{event_year}",
                    ee.Number(metrics.get("pre_observed")).divide(total),
                )
            output = output.set(
                f"post_observed_fraction_{event_year}_h{horizon}",
                ee.Number(metrics.get("post_observed")).divide(total),
            )
            output = output.set(
                f"loss_fraction_cell_{event_year}_h{horizon}",
                ee.Number(metrics.get("loss")).divide(total),
            )
            for destination in DESTINATIONS:
                output = output.set(
                    f"to_{destination}_fraction_cell_{event_year}_h{horizon}",
                    ee.Number(metrics.get(f"to_{destination}")).divide(total),
                )
        return ee.Feature(feature.geometry(), output)

    return reduced.map(expand).select(selectors, retainGeometry=True)


def build_chunk_collection(
    cells: pd.DataFrame,
    specs: list[dict[str, Any]],
    selectors: list[str],
) -> ee.FeatureCollection:
    polygons = make_private_polygons(cells)
    land_cover = ee.Image(MAPBIOMAS_ASSET)
    packed = build_transition_image(specs)
    reduced = packed.reduceRegions(
        collection=polygons,
        reducer=ee.Reducer.frequencyHistogram(),
        scale=30,
        crs=land_cover.projection(),
        tileScale=8,
    )
    # Dictionary histograms cannot be stored in an Earth Engine table asset.
    # Expand them into the registered scalar fractions after reduction, not
    # into hundreds of raster bands before reduction.
    return expand_transition_histograms(reduced, specs, selectors)


def task_status(task_id: str) -> dict[str, Any]:
    values = ee.data.getTaskStatus(task_id)
    return values[0] if values else {"id": task_id, "state": "UNKNOWN"}


def initial_chunks(
    cells: pd.DataFrame, asset_prefix: str, chunk_size: int
) -> list[dict[str, Any]]:
    chunks = []
    for index, start in enumerate(range(0, len(cells), chunk_size)):
        end = min(start + chunk_size, len(cells))
        chunks.append(
            {
                "index": index,
                "row_start": start,
                "row_end_exclusive": end,
                "expected_rows": end - start,
                "asset_id": f"{asset_prefix}_{index:03d}",
                "attempt": 0,
                "state": "NOT_STARTED",
                "attempt_history": [],
            }
        )
    return chunks


def state_counts(chunks: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for chunk in chunks:
        state = str(chunk.get("state", "UNKNOWN")).upper()
        counts[state] = counts.get(state, 0) + 1
    return dict(sorted(counts.items()))


def submit_chunk(
    chunk: dict[str, Any],
    cells: pd.DataFrame,
    specs: list[dict[str, Any]],
    selectors: list[str],
) -> None:
    start = int(chunk["row_start"])
    end = int(chunk["row_end_exclusive"])
    collection = build_chunk_collection(cells.iloc[start:end].copy(), specs, selectors)
    attempt = int(chunk.get("attempt", 0)) + 1
    task = ee.batch.Export.table.toAsset(
        collection=collection,
        description=f"phase3_mapbiomas_hist_chunk_{chunk['index']:03d}_attempt_{attempt}",
        assetId=str(chunk["asset_id"]),
    )
    task.start()
    status = task_status(task.id)
    chunk.update(
        {
            "attempt": attempt,
            "task_id": task.id,
            "submitted_at_utc": utc_now(),
            "state": str(status.get("state", "READY")).upper(),
            "last_task_status": status,
        }
    )


def refresh_and_retry(
    chunks: list[dict[str, Any]],
    cells: pd.DataFrame,
    specs: list[dict[str, Any]],
    selectors: list[str],
    max_attempts: int,
) -> None:
    for chunk in chunks:
        if asset_exists(str(chunk["asset_id"])):
            chunk["state"] = "COMPLETED"
            continue
        task_id = chunk.get("task_id")
        if task_id:
            status = task_status(str(task_id))
            state = str(status.get("state", "UNKNOWN")).upper()
            chunk["state"] = state
            chunk["last_task_status"] = status
            if state in TERMINAL_FAILURE:
                history = chunk.setdefault("attempt_history", [])
                if not history or history[-1].get("task_id") != task_id:
                    history.append(
                        {
                            "attempt": chunk.get("attempt"),
                            "task_id": task_id,
                            "state": state,
                            "error_message": status.get("error_message"),
                            "closed_at_utc": utc_now(),
                        }
                    )
                chunk.pop("task_id", None)
        if chunk["state"] in TERMINAL_SUCCESS and not asset_exists(str(chunk["asset_id"])):
            chunk["state"] = "AWAITING_ASSET_VISIBILITY"
        if chunk["state"] in TERMINAL_FAILURE | {"NOT_STARTED", "UNKNOWN"}:
            if int(chunk.get("attempt", 0)) < max_attempts:
                submit_chunk(chunk, cells, specs, selectors)
            else:
                chunk["state"] = "FAILED_RETRY_LIMIT"


def parse_histogram(value: Any) -> dict[int, float]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return {}
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, dict):
        raise ValueError(f"Unexpected histogram value: {type(value).__name__}")
    return {int(float(key)): float(count) for key, count in value.items()}


def expand_histogram_chunk(
    frame: pd.DataFrame, specs: list[dict[str, Any]], selectors: list[str]
) -> pd.DataFrame:
    output: dict[str, Any] = {"cell_id": frame["cell_id"].astype(str).to_numpy()}
    for column in selectors:
        if column != "cell_id":
            output[column] = np.full(len(frame), np.nan, dtype=float)

    for row_index, row in frame.reset_index(drop=True).iterrows():
        for spec in specs:
            event_year = int(spec["event_year"])
            horizon = int(spec["horizon"])
            histogram = parse_histogram(row.get(str(spec["property"])))
            total = float(sum(histogram.values()))
            if not math.isfinite(total) or total <= 0:
                continue
            pre_observed = post_observed = pre_natural = loss = 0.0
            destination_counts = {destination: 0.0 for destination in DESTINATIONS}
            for packed_code, count in histogram.items():
                pre_code = packed_code // 100
                post_code = packed_code % 100
                pre_is_observed = pre_code not in NOT_OBSERVED_CODES
                post_is_observed = post_code not in NOT_OBSERVED_CODES
                pre_is_natural = pre_code in NATURAL_CODES
                post_is_natural = post_code in NATURAL_CODES
                if pre_is_observed:
                    pre_observed += count
                if post_is_observed:
                    post_observed += count
                if pre_is_natural and pre_is_observed:
                    pre_natural += count
                if pre_is_natural and not post_is_natural and pre_is_observed and post_is_observed:
                    loss += count
                if pre_is_natural and pre_is_observed and post_is_observed:
                    for destination, codes in DESTINATION_CODES.items():
                        if post_code in codes:
                            destination_counts[destination] += count
            if horizon == 1:
                output[f"pre_natural_fraction_{event_year}"][row_index] = pre_natural / total
                output[f"pre_observed_fraction_{event_year}"][row_index] = pre_observed / total
            output[f"post_observed_fraction_{event_year}_h{horizon}"][row_index] = post_observed / total
            output[f"loss_fraction_cell_{event_year}_h{horizon}"][row_index] = loss / total
            for destination in DESTINATIONS:
                output[f"to_{destination}_fraction_cell_{event_year}_h{horizon}"][row_index] = (
                    destination_counts[destination] / total
                )
    return pd.DataFrame(output)[selectors]


def download_chunks(
    chunks: list[dict[str, Any]],
    cells: pd.DataFrame,
    specs: list[dict[str, Any]],
    selectors: list[str],
) -> dict[str, Any]:
    parts = []
    for chunk in chunks:
        frame = ee.data.computeFeatures(
            {
                "expression": ee.FeatureCollection(str(chunk["asset_id"])).select(
                    selectors, retainGeometry=False
                ),
                "fileFormat": "PANDAS_DATAFRAME",
                "pageSize": 250,
                "workloadTag": "phase3-mapbiomas-histogram-download",
            }
        )
        expected_ids = set(
            cells.iloc[int(chunk["row_start"]) : int(chunk["row_end_exclusive"])][
                "cell_id"
            ].astype(str)
        )
        found_ids = set(frame["cell_id"].astype(str))
        if found_ids != expected_ids:
            raise ValueError(
                f"Chunk {chunk['index']} cell mismatch: missing={len(expected_ids - found_ids)}, "
                f"unexpected={len(found_ids - expected_ids)}"
            )
        missing_columns = sorted(set(selectors) - set(frame.columns))
        if missing_columns:
            raise ValueError(
                f"Chunk {chunk['index']} is missing columns: {missing_columns}"
            )
        parts.append(frame[selectors].copy())
        chunk["downloaded_rows"] = int(len(frame))
        chunk["downloaded_at_utc"] = utc_now()
    final = pd.concat(parts, ignore_index=True)
    if final["cell_id"].duplicated().any() or len(final) != len(cells):
        raise ValueError("Combined Phase 3 transition table has invalid cell coverage")
    final = final.sort_values("cell_id").reset_index(drop=True)
    TRANSITION_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = TRANSITION_SUMMARY_PATH.with_suffix(".csv.tmp")
    final.to_csv(temporary, index=False, float_format="%.10g")
    temporary.replace(TRANSITION_SUMMARY_PATH)
    return {
        "path": str(TRANSITION_SUMMARY_PATH.relative_to(ROOT)).replace("\\", "/"),
        "row_count": int(len(final)),
        "column_count": int(len(final.columns)),
        "size_bytes": TRANSITION_SUMMARY_PATH.stat().st_size,
        "sha256": sha256_file(TRANSITION_SUMMARY_PATH),
    }


def remove_temporary_assets(chunks: list[dict[str, Any]]) -> int:
    removed = 0
    for chunk in chunks:
        asset_id = str(chunk["asset_id"])
        if asset_exists(asset_id):
            ee.data.deleteAsset(asset_id)
            removed += 1
        chunk["temporary_asset_deleted"] = not asset_exists(asset_id)
        chunk["temporary_asset_deleted_at_utc"] = utc_now()
    return removed


def build_or_resume_receipt(
    args: argparse.Namespace,
    cells: pd.DataFrame,
    selectors: list[str],
    specs: list[dict[str, Any]],
) -> dict[str, Any]:
    previous = read_receipt()
    private_sha = sha256_file(PRIVATE_CELL_PATH)
    compatible = (
        previous.get("algorithm_revision") == ALGORITHM_REVISION
        and previous.get("project") == args.project
        and previous.get("asset_prefix") == args.asset_prefix
        and previous.get("chunk_size") == args.chunk_size
        and previous.get("private_input", {}).get("sha256") == private_sha
    )
    chunks = previous.get("chunks", []) if compatible else initial_chunks(
        cells, args.asset_prefix, args.chunk_size
    )
    return {
        "schema_version": "phase3-earthengine-export/v2",
        "algorithm_revision": ALGORITHM_REVISION,
        "created_at_utc": previous.get("created_at_utc", utc_now()) if compatible else utc_now(),
        "updated_at_utc": utc_now(),
        "status": "preparing_chunk_exports",
        "project": args.project,
        "mapbiomas_asset": MAPBIOMAS_ASSET,
        "asset_prefix": args.asset_prefix,
        "chunk_size": args.chunk_size,
        "chunk_count": len(chunks),
        "private_input": {
            "path": str(PRIVATE_CELL_PATH.relative_to(ROOT)).replace("\\", "/"),
            "row_count": int(len(cells)),
            "sha256": private_sha,
            "uploaded_as_persistent_asset": False,
            "tracked_by_git": False,
        },
        "cloud_method": "24 packed annual transition histograms expanded server-side per small chunk into registered fractions",
        "temporary_private_assets_contain_coordinates": True,
        "temporary_asset_policy": "Delete all chunk assets after the coordinate-free local table is validated and downloaded.",
        "expected_histogram_property_count": len(specs),
        "expected_output_column_count": len(selectors),
        "credential_values_recorded": False,
        "chunks": chunks,
    }


def run(args: argparse.Namespace) -> int:
    ee.Initialize(project=args.project)
    registration = read_json(REGISTRATION_PATH)
    cells, selectors = validate_sources(registration)
    specs = transition_specs(registration)
    ensure_private_folder(args.asset_prefix.rsplit("/", 1)[0])
    receipt = build_or_resume_receipt(args, cells, selectors, specs)

    refresh_and_retry(receipt["chunks"], cells, specs, selectors, args.max_attempts)
    receipt["updated_at_utc"] = utc_now()
    receipt["state_counts"] = state_counts(receipt["chunks"])
    receipt["status"] = "earth_engine_chunk_tasks_active"
    write_receipt(receipt)

    if not args.wait:
        print(
            json.dumps(
                {
                    "status": receipt["status"],
                    "chunk_count": receipt["chunk_count"],
                    "state_counts": receipt["state_counts"],
                },
                indent=2,
            )
        )
        return 0

    while True:
        refresh_and_retry(receipt["chunks"], cells, specs, selectors, args.max_attempts)
        counts = state_counts(receipt["chunks"])
        receipt["updated_at_utc"] = utc_now()
        receipt["state_counts"] = counts
        if counts.get("FAILED_RETRY_LIMIT", 0):
            receipt["status"] = "failed_retry_limit"
            write_receipt(receipt)
            raise RuntimeError("At least one Earth Engine chunk reached the retry limit")
        if counts.get("COMPLETED", 0) == len(receipt["chunks"]):
            break
        receipt["status"] = "earth_engine_chunk_tasks_active"
        write_receipt(receipt)
        print(
            json.dumps({"time": receipt["updated_at_utc"], "state_counts": counts}),
            flush=True,
        )
        time.sleep(args.poll_seconds)

    receipt["status"] = "downloading_coordinate_free_histograms"
    write_receipt(receipt)
    output = download_chunks(receipt["chunks"], cells, specs, selectors)
    removed_assets = 0
    if not args.keep_assets:
        removed_assets = remove_temporary_assets(receipt["chunks"])
    receipt["updated_at_utc"] = utc_now()
    receipt["status"] = "complete_local_transition_table"
    receipt["state_counts"] = state_counts(receipt["chunks"])
    receipt["output"] = output
    receipt["temporary_assets_removed"] = removed_assets
    receipt["temporary_assets_retained_by_request"] = bool(args.keep_assets)
    write_receipt(receipt)
    if not args.skip_models:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "analysis" / "phase3_land_change.py"), "--run-models"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        receipt["updated_at_utc"] = utc_now()
        receipt["status"] = "complete_phase3_model_run"
        receipt["phase3_model_command"] = {
            "command": "python analysis/phase3_land_change.py --run-models",
            "exit_code": completed.returncode,
            "stdout": completed.stdout.strip(),
        }
        write_receipt(receipt)
    print(json.dumps({"status": receipt["status"], "output": output}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument("--asset-prefix", default=DEFAULT_ASSET_PREFIX)
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=30)
    parser.add_argument("--max-attempts", type=int, default=4)
    parser.add_argument(
        "--keep-assets",
        action="store_true",
        help="Retain the temporary private Earth Engine chunk assets after download.",
    )
    parser.add_argument(
        "--skip-models",
        action="store_true",
        help="Stop after the validated transition table instead of fitting Phase 3.",
    )
    args = parser.parse_args()
    if args.chunk_size < 100 or args.chunk_size > 2000:
        parser.error("--chunk-size must be between 100 and 2000")
    if args.poll_seconds < 10:
        parser.error("--poll-seconds must be at least 10")
    if args.max_attempts < 1:
        parser.error("--max-attempts must be at least 1")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
