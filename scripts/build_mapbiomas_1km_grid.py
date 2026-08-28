"""Aggregate the frozen natural-forest mask to the registered 1-km grid.

The grid is anchored at integer multiples of 1,000 m in EPSG:6933.  Average
resampling of the binary 30 m mask yields the proportion of each 1-km cell
covered by the frozen 2014 natural-forest footprint.  Cells are not silently
filled, and the output remains a descriptive cohort frame until the VIIRS
observation denominator is constructed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "derived" / "mapbiomas" / "mapbiomas_c41_natural_forest_mask_2014_kalimantan.tif"
DEFAULT_OUTPUT = ROOT / "data" / "derived" / "mapbiomas" / "mapbiomas_c41_forest_fraction_1km_kalimantan.tif"
DEFAULT_REPORT = ROOT / "outputs" / "quality" / "mapbiomas_2014_forest_fraction_1km.json"
GRID_CRS = "EPSG:6933"
CELL_SIZE_M = 1000


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_grid(source: Path, output: Path, report_path: Path) -> dict[str, Any]:
    try:
        import numpy as np
        import rasterio
        from rasterio.enums import Resampling
        from rasterio.transform import from_origin
        from rasterio.warp import calculate_default_transform, reproject, transform_bounds
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise RuntimeError("rasterio and numpy are required to build the 1-km grid") from exc

    source = source.resolve()
    output = output.resolve()
    report_path = report_path.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(source) as src:
        bounds = transform_bounds(src.crs, GRID_CRS, *src.bounds, densify_pts=21)
        left, bottom, right, top = bounds
        x0 = math.floor(left / CELL_SIZE_M) * CELL_SIZE_M
        y0 = math.floor(bottom / CELL_SIZE_M) * CELL_SIZE_M
        x1 = math.ceil(right / CELL_SIZE_M) * CELL_SIZE_M
        y1 = math.ceil(top / CELL_SIZE_M) * CELL_SIZE_M
        width = int(round((x1 - x0) / CELL_SIZE_M))
        height = int(round((y1 - y0) / CELL_SIZE_M))
        transform = from_origin(x0, y1, CELL_SIZE_M, CELL_SIZE_M)
        destination = np.zeros((height, width), dtype="float32")
        reproject(
            source=rasterio.band(src, 1),
            destination=destination,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=transform,
            dst_crs=GRID_CRS,
            # The binary mask uses 0 for valid non-forest as well as the
            # source's outside-data convention.  Override the source nodata
            # tag with an impossible value so zeros are included in the
            # area-weighted fraction rather than ignored as nodata.
            src_nodata=255,
            dst_nodata=0.0,
            resampling=Resampling.average,
            init_dest_nodata=0.0,
        )

    destination = np.clip(destination, 0.0, 1.0)
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "nodata": -9999.0,
        "width": width,
        "height": height,
        "count": 1,
        "crs": GRID_CRS,
        "transform": transform,
        "compress": "deflate",
        "predictor": 2,
        "tiled": True,
        "blockxsize": 256,
        "blockysize": 256,
        "BIGTIFF": "IF_SAFER",
    }
    output_tmp = output.with_suffix(output.suffix + ".part")
    if output_tmp.exists():
        output_tmp.unlink()
    with rasterio.open(output_tmp, "w", **profile) as dst:
        dst.write(destination, 1)
        dst.update_tags(
            grid_crs=GRID_CRS,
            cell_size_m=str(CELL_SIZE_M),
            anchor="integer multiples of 1000 m from projected origin (0, 0)",
            source_mask=str(source),
            definition="mean binary natural-forest mask per 1-km cell",
        )
    output_tmp.replace(output)

    valid = np.isfinite(destination)
    report = {
        "schema_version": "mapbiomas-forest-fraction-1km/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated",
        "source": {
            "path": source.relative_to(ROOT).as_posix(),
            "sha256": _sha256(source),
        },
        "output": {
            "path": output.relative_to(ROOT).as_posix(),
            "sha256": _sha256(output),
            "crs": GRID_CRS,
            "cell_size_m": CELL_SIZE_M,
            "anchor": [0, 0],
            "width": width,
            "height": height,
            "bounds_projected": [x0, y0, x1, y1],
            "cell_count": int(valid.sum()),
            "cells_at_or_above_70_percent": int((destination >= 0.70).sum()),
            "cells_at_or_above_50_percent": int((destination >= 0.50).sum()),
            "min_fraction": float(destination[valid].min()) if valid.any() else None,
            "max_fraction": float(destination[valid].max()) if valid.any() else None,
            "mean_fraction": float(destination[valid].mean()) if valid.any() else None,
        },
        "definition": "Forest fraction is the area-weighted mean of the validated 30 m binary mask within each 1-km EPSG:6933 cell; it is not an observation denominator.",
        "limitations": [
            "Cells include zero-valued source pixels where MapBiomas is non-forest or outside the mapped land footprint; coastal cells therefore receive conservative fractions.",
            "The 70% threshold defines the primary cohort but does not establish fire occurrence or causality.",
            "VIIRS valid negatives still require paired geolocation, quality, cloud/water, coverage, and prior-negative rules.",
        ],
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = build_grid(args.source, args.output, args.report)
    print(json.dumps({
        "status": report["status"],
        "output": report["output"]["path"],
        "report": args.report.resolve().relative_to(ROOT).as_posix(),
        "cell_count": report["output"]["cell_count"],
        "cells_at_or_above_70_percent": report["output"]["cells_at_or_above_70_percent"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
