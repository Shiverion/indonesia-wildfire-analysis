from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wildfire_research.mapbiomas import validate_mapbiomas_export


def _write_valid_hand_off(root: Path) -> Path:
    export = root / "data" / "raw" / "mapbiomas_indonesia"
    export.mkdir(parents=True)
    (export / "class_crosswalk.json").write_text(json.dumps({
        "schema_version": "mapbiomas-class-crosswalk/v1",
        "collection": "4.1",
        "baseline_year": 2014,
        "legend_source_url": "https://landy.mapbiomas.id/en/legendcode",
        "natural_forest_codes": [999],
        "class_labels": {"999": "reviewed natural forest"},
    }), encoding="utf-8")
    (export / "mapbiomas_2014_provenance.json").write_text(json.dumps({
        "source_url": "https://landy.mapbiomas.id/en/gee",
        "retrieved_at_utc": "2026-08-25T00:00:00Z",
        "collection": "4.1",
        "baseline_year": 2014,
        "export_asset_id": "projects/example/assets/collection41",
        "export_kind": "land_cover_raster",
        "export_region_bbox_wgs84": [109.0, -5.0, 120.0, 8.0],
    }), encoding="utf-8")
    data = np.full((13, 11), 999, dtype=np.uint16)
    with rasterio.open(
        export / "mapbiomas_indonesia_c41_landcover_2014_kalimantan.tif",
        "w", driver="GTiff", height=13, width=11, count=1, dtype=data.dtype,
        crs="EPSG:4326", transform=from_origin(109, 8, 1, 1),
    ) as dataset:
        dataset.write(data, 1)
    return export


def test_missing_mapbiomas_export_is_blocked(tmp_path: Path) -> None:
    report = validate_mapbiomas_export(tmp_path)
    assert report["ready"] is False
    assert report["status"] == "blocked_mapbiomas_export_preflight"
    assert "export_directory_missing" in report["errors"]
    assert "missing_land_cover_raster" in report["errors"]


def test_valid_mapbiomas_hand_off_passes(tmp_path: Path) -> None:
    export = _write_valid_hand_off(tmp_path)
    report = validate_mapbiomas_export(tmp_path, export)
    assert report["ready"] is True
    assert report["status"] == "validated_collection_4_1_2014_export"
    assert report["raster_checks"][0]["readable"] is True


def test_collection_mismatch_never_passes(tmp_path: Path) -> None:
    export = _write_valid_hand_off(tmp_path)
    path = export / "mapbiomas_2014_provenance.json"
    metadata = json.loads(path.read_text(encoding="utf-8"))
    metadata["collection"] = "4"
    path.write_text(json.dumps(metadata), encoding="utf-8")
    report = validate_mapbiomas_export(tmp_path, export)
    assert report["ready"] is False
    assert "provenance_collection_must_be:4.1" in report["errors"]
