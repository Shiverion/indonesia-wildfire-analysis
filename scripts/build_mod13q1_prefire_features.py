#!/usr/bin/env python3
"""Extract conservative MOD13Q1 EVI/QA summaries for the registered bbox.

The Earthdata download is HDF4 and the bundled runtime does not ship an HDF4
reader.  This script is intentionally small and auditable: it reads only the
EVI, VI Quality, and composite-day SDSs, clips each tile to the registered
WGS84 bbox, applies the product bit-field rules, and writes one receipt row per
tile/composite.  It is a QA/timing closure artifact, not an event-level
covariate table; event linkage still requires the complete VIIRS opportunity
frame and all study years.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from datetime import date, timedelta, timezone, datetime
from pathlib import Path

import numpy as np
from pyhdf.SD import SD, SDC
from pyproj import CRS, Transformer


ROOT = Path(__file__).resolve().parents[1]
HDF_RE = re.compile(r"MOD13Q1\.A(?P<year>\d{4})(?P<doy>\d{3})\.h(?P<h>\d{2})v(?P<v>\d{2})\..+\.hdf$")
STRUCT_RE = re.compile(
    r"UpperLeftPointMtrs=\((?P<ulx>[-0-9.]+),(?P<uly>[-0-9.]+)\).*?"
    r"LowerRightMtrs=\((?P<lrx>[-0-9.]+),(?P<lry>[-0-9.]+)\)",
    re.S,
)

PRODUCT_EVI = "250m 16 days EVI"
PRODUCT_QA = "250m 16 days VI Quality"
PRODUCT_DOY = "250m 16 days composite day of the year"
SINUSOIDAL = CRS.from_proj4("+proj=sinu +R=6371007.181 +lon_0=0 +x_0=0 +y_0=0 +units=m +no_defs")
WGS84 = CRS.from_epsg(4326)
TO_SINU = Transformer.from_crs(WGS84, SINUSOIDAL, always_xy=True)
FROM_SINU = Transformer.from_crs(SINUSOIDAL, WGS84, always_xy=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def parse_struct_metadata(raw: str) -> tuple[float, float, float, float]:
    match = STRUCT_RE.search(raw)
    if not match:
        raise ValueError("StructMetadata.0 has no MODIS tile bounds")
    return tuple(float(match.group(key)) for key in ("ulx", "uly", "lrx", "lry"))


def window_for_bbox(ulx: float, uly: float, lrx: float, lry: float, bbox: tuple[float, float, float, float]):
    # MOD13Q1 250-m sinusoidal pixels are exactly the tile span divided by 4800.
    width = height = 4800
    px = (lrx - ulx) / width
    py = (uly - lry) / height
    min_lon, min_lat, max_lon, max_lat = bbox
    xs, ys = zip(*[TO_SINU.transform(lon, lat) for lon, lat in ((min_lon, min_lat), (min_lon, max_lat), (max_lon, min_lat), (max_lon, max_lat))])
    left = max(0, int(math.floor((min(xs) - ulx) / px)) - 2)
    right = min(width, int(math.ceil((max(xs) - ulx) / px)) + 2)
    top = max(0, int(math.floor((uly - max(ys)) / py)) - 2)
    bottom = min(height, int(math.ceil((uly - min(ys)) / py)) + 2)
    if right <= left or bottom <= top:
        return None
    return left, top, right, bottom, px, py


def process_hdf(path: Path, bbox: tuple[float, float, float, float]) -> dict[str, object]:
    match = HDF_RE.fullmatch(path.name)
    if not match:
        raise ValueError(f"Malformed MOD13Q1 filename: {path.name}")
    year = int(match["year"])
    doy = int(match["doy"])
    tile = f"h{match['h']}v{match['v']}"
    composite_start = date(year, 1, 1) + timedelta(days=doy - 1)
    composite_end = composite_start + timedelta(days=15)

    hdf = SD(str(path), SDC.READ)
    try:
        attrs = hdf.attributes()
        ulx, uly, lrx, lry = parse_struct_metadata(str(attrs.get("StructMetadata.0", "")))
        window = window_for_bbox(ulx, uly, lrx, lry, bbox)
        if window is None:
            return {"path": path.relative_to(ROOT).as_posix(), "year": year, "doy": doy, "tile": tile, "intersects_bbox": False}
        left, top, right, bottom, px, py = window
        shape = (bottom - top, right - left)
        evi_sds = hdf.select(PRODUCT_EVI)
        qa_sds = hdf.select(PRODUCT_QA)
        doy_sds = hdf.select(PRODUCT_DOY)
        evi = np.asarray(evi_sds[top:bottom, left:right], dtype=np.int32)
        qa = np.asarray(qa_sds[top:bottom, left:right], dtype=np.uint16)
        comp_doy = np.asarray(doy_sds[top:bottom, left:right], dtype=np.int16)
        rows = np.arange(top, bottom, dtype=np.float64)[:, None]
        cols = np.arange(left, right, dtype=np.float64)[None, :]
        x = ulx + (cols + 0.5) * px
        y = uly - (rows + 0.5) * py
        x, y = np.broadcast_arrays(x, y)
        lon, lat = FROM_SINU.transform(x, y)
        in_bbox = (lon >= bbox[0]) & (lon <= bbox[2]) & (lat >= bbox[1]) & (lat <= bbox[3])
        valid_range = (evi >= -2000) & (evi <= 10000)
        not_fill = qa != 65535
        modland_good = (qa & 0b11) == 0
        usefulness = (qa >> 2) & 0b1111
        adjacent_cloud_clear = (qa & (1 << 8)) == 0
        mixed_cloud_clear = (qa & (1 << 10)) == 0
        land_only = ((qa >> 11) & 0b111) == 1
        snow_clear = (qa & (1 << 14)) == 0
        shadow_clear = (qa & (1 << 15)) == 0
        qa_pass = in_bbox & valid_range & not_fill & modland_good & (usefulness <= 1) & adjacent_cloud_clear & mixed_cloud_clear & land_only & snow_clear & shadow_clear
        bbox_pixels = int(in_bbox.sum())
        valid_pixels = int((in_bbox & valid_range & not_fill).sum())
        qa_pixels = int(qa_pass.sum())
        evi_values = evi[qa_pass].astype(np.float64) / 10000.0
        return {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": sha256(path),
            "year": year,
            "doy": doy,
            "tile": tile,
            "composite_start": composite_start.isoformat(),
            "composite_end": composite_end.isoformat(),
            "intersects_bbox": True,
            "bbox_window": [left, top, right, bottom],
            "window_pixels": int(shape[0] * shape[1]),
            "bbox_pixels": bbox_pixels,
            "valid_evi_pixels": valid_pixels,
            "qa_pass_pixels": qa_pixels,
            "qa_pass_fraction_of_valid": round(qa_pixels / valid_pixels, 6) if valid_pixels else None,
            "evi_mean_qa": round(float(evi_values.mean()), 6) if evi_values.size else None,
            "evi_p05_qa": round(float(np.quantile(evi_values, 0.05)), 6) if evi_values.size else None,
            "evi_p50_qa": round(float(np.quantile(evi_values, 0.50)), 6) if evi_values.size else None,
            "evi_p95_qa": round(float(np.quantile(evi_values, 0.95)), 6) if evi_values.size else None,
            "composite_doy_min": int(comp_doy[in_bbox].min()) if bbox_pixels else None,
            "composite_doy_max": int(comp_doy[in_bbox].max()) if bbox_pixels else None,
        }
    finally:
        hdf.end()


def build(root: Path, output_csv: Path, report_path: Path, bbox: tuple[float, float, float, float]) -> dict[str, object]:
    files = sorted((root / "data" / "raw" / "mod13q1" / "MOD13Q1").glob("MOD13Q1.*.hdf"))
    rows = [process_hdf(path, bbox) for path in files]
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    study_rows = [row for row in rows if row.get("year") == 2015 and row.get("intersects_bbox")]
    report = {
        "schema_version": "mod13q1-prefire-qa/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "qa_validated_tile_composite_summary",
        "product": "MOD13Q1.061",
        "bbox_wgs84": list(bbox),
        "qa_rule": {
            "modland_qa": "bits 0-1 == 0 (good quality)",
            "vi_usefulness": "bits 2-5 <= 1 (highest or lower quality)",
            "adjacent_cloud": "bit 8 == 0",
            "mixed_cloud": "bit 10 == 0",
            "land_water": "bits 11-13 == 001 (land only)",
            "snow": "bit 14 == 0",
            "shadow": "bit 15 == 0",
            "evi_valid_range": "-2000..10000, scaled by 1/10000",
        },
        "input": {"hdf_file_count": len(files), "sha256_recorded": True},
        "output": {"path": output_csv.relative_to(root).as_posix(), "sha256": sha256(output_csv), "row_count": len(rows)},
        "summary": {
            "study_year": 2015,
            "study_composite_count": len({(int(row["year"]), int(row["doy"])) for row in study_rows}),
            "study_tile_count": len({row["tile"] for row in study_rows}),
            "study_rows": len(study_rows),
            "bbox_pixels": sum(int(row.get("bbox_pixels", 0)) for row in study_rows),
            "valid_evi_pixels": sum(int(row.get("valid_evi_pixels", 0)) for row in study_rows),
            "qa_pass_pixels": sum(int(row.get("qa_pass_pixels", 0)) for row in study_rows),
        },
        "qa_mask_validated": True,
        "prefire_support_validated": False,
        "prefire_support_status": "tile_composite_summary_only",
        "limitations": [
            "Local Earthdata payloads cover 2014-2015 only, not every registered study year 2015-2025.",
            "This receipt validates SDS bit rules and geographic clipping but does not link a QA-valid composite to each qualifying VIIRS cutoff.",
            "A complete event-level table remains blocked until the full paired VIIRS opportunity frame and temporal support are available.",
        ],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=ROOT / "data/derived/mod13q1/mod13q1_2015_tile_summary.csv")
    parser.add_argument("--report", type=Path, default=ROOT / "outputs/quality/mod13q1_2015_prefire_qa.json")
    parser.add_argument("--bbox", nargs=4, type=float, default=[109.0, -5.0, 120.0, 8.0], metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"))
    args = parser.parse_args()
    report = build(args.root.resolve(), args.output.resolve(), args.report.resolve(), tuple(args.bbox))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
