from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wildfire_research.phase1b import check_mapbiomas_1km_grid, check_mapbiomas_forest_mask, validate_opportunity_frame


def test_missing_opportunity_frame_is_a_hard_block(tmp_path: Path) -> None:
    result = validate_opportunity_frame(tmp_path)
    assert result["denominator_ready"] is False
    assert result["status"] == "blocked_missing_opportunity_frame"


def test_frame_requires_both_positive_and_negative_rows(tmp_path: Path) -> None:
    path = tmp_path / "data/derived/viirs/opportunity_frame.csv"
    path.parent.mkdir(parents=True)
    fields = [
        "opportunity_id", "pair_key", "cell_id", "acquisition_utc", "outcome_status",
        "valid_opportunity", "forest_fraction", "quality_pass", "coverage_fraction", "negative_lookback_hours",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow({field: "x" for field in fields} | {"opportunity_id": "1", "cell_id": "a", "outcome_status": "positive", "valid_opportunity": "true"})
    result = validate_opportunity_frame(tmp_path)
    assert result["positive_rows"] == 1
    assert result["negative_rows"] == 0
    assert result["denominator_ready"] is False


def test_frame_rejects_coordinates_and_duplicate_keys(tmp_path: Path) -> None:
    path = tmp_path / "data/derived/viirs/opportunity_frame.csv"
    path.parent.mkdir(parents=True)
    fields = [
        "opportunity_id", "pair_key", "cell_id", "acquisition_utc", "outcome_status",
        "valid_opportunity", "forest_fraction", "quality_pass", "coverage_fraction", "negative_lookback_hours", "latitude",
    ]
    rows = [
        {field: "x" for field in fields} | {"opportunity_id": "1", "cell_id": "a", "outcome_status": "positive", "valid_opportunity": "true"},
        {field: "x" for field in fields} | {"opportunity_id": "1", "cell_id": "a", "outcome_status": "negative", "valid_opportunity": "true"},
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    result = validate_opportunity_frame(tmp_path)
    assert any(item.startswith("forbidden_column:latitude") for item in result["errors"])
    assert any(item.startswith("duplicate_key") for item in result["errors"])
    assert result["denominator_ready"] is False


def test_forest_mask_requires_matching_hash_receipt(tmp_path: Path) -> None:
    mask = tmp_path / "data/derived/mapbiomas/mapbiomas_c41_natural_forest_mask_2014_kalimantan.tif"
    mask.parent.mkdir(parents=True)
    mask.write_bytes(b"mask")
    digest = hashlib.sha256(b"mask").hexdigest()
    report = tmp_path / "outputs/quality/mapbiomas_2014_forest_mask.json"
    report.parent.mkdir(parents=True)
    report.write_text(json.dumps({
        "status": "validated",
        "output": {
            "path": "data/derived/mapbiomas/mapbiomas_c41_natural_forest_mask_2014_kalimantan.tif",
            "sha256": digest,
            "forest_codes": [3, 5, 76],
            "bbox_wgs84": [109, -5, 120, 6],
            "natural_forest_fraction_of_valid_source": 0.5,
        },
    }), encoding="utf-8")
    result = check_mapbiomas_forest_mask(tmp_path)
    assert result["gate_ready"] is True
    mask.write_bytes(b"changed")
    result = check_mapbiomas_forest_mask(tmp_path)
    assert result["gate_ready"] is False
    assert "forest_mask_sha256_mismatch" in result["errors"]


def test_1km_grid_requires_projection_and_hash_receipt(tmp_path: Path) -> None:
    grid = tmp_path / "data/derived/mapbiomas/mapbiomas_c41_forest_fraction_1km_kalimantan.tif"
    grid.parent.mkdir(parents=True)
    grid.write_bytes(b"grid")
    digest = hashlib.sha256(b"grid").hexdigest()
    report = tmp_path / "outputs/quality/mapbiomas_2014_forest_fraction_1km.json"
    report.parent.mkdir(parents=True)
    report.write_text(json.dumps({
        "status": "validated",
        "output": {
            "path": "data/derived/mapbiomas/mapbiomas_c41_forest_fraction_1km_kalimantan.tif",
            "sha256": digest,
            "crs": "EPSG:6933",
            "cell_size_m": 1000,
            "anchor": [0, 0],
            "cells_at_or_above_70_percent": 2,
            "cells_at_or_above_50_percent": 3,
        },
    }), encoding="utf-8")
    result = check_mapbiomas_1km_grid(tmp_path)
    assert result["gate_ready"] is True
    grid.write_bytes(b"changed")
    result = check_mapbiomas_1km_grid(tmp_path)
    assert result["gate_ready"] is False
    assert "1km_forest_fraction_sha256_mismatch" in result["errors"]
