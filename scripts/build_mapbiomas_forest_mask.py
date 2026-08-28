"""Build the frozen 2014 natural-forest mask from a MapBiomas C4.1 export.

The country-wide MapBiomas GeoTIFF is intentionally kept as the immutable
source.  This script reads only tiled windows covering the registered
Kalimantan bbox and writes a compact binary mask: 1 for the frozen natural-
forest crosswalk (codes 3, 5, and 76), 0 for all other valid classes and
outside-data pixels.  It never loads the 10+ billion-pixel country raster into
memory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "raw" / "mapbiomas_indonesia" / "mapbiomas_indonesia_c41_landcover_2014.tif"
DEFAULT_OUTPUT = ROOT / "data" / "derived" / "mapbiomas" / "mapbiomas_c41_natural_forest_mask_2014_kalimantan.tif"
DEFAULT_REPORT = ROOT / "outputs" / "quality" / "mapbiomas_2014_forest_mask.json"
KALIMANTAN_BBOX = (109.0, -5.0, 120.0, 6.0)
FOREST_CODES = (3, 5, 76)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_mask(source: Path, output: Path, report_path: Path) -> dict[str, Any]:
    try:
        import numpy as np
        import rasterio
        from rasterio.windows import Window, from_bounds
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise RuntimeError("rasterio and numpy are required to build the forest mask") from exc

    source = source.resolve()
    output = output.resolve()
    report_path = report_path.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(source) as src:
        if src.count != 1:
            raise ValueError(f"expected one MapBiomas band, got {src.count}")
        if src.crs is None or src.crs.to_epsg() != 4326:
            raise ValueError(f"expected EPSG:4326 source, got {src.crs}")
        if src.nodata not in (0, 0.0, None):
            raise ValueError(f"unexpected source nodata value: {src.nodata}")

        raw_window = from_bounds(*KALIMANTAN_BBOX, transform=src.transform)
        window = raw_window.round_offsets().round_lengths()
        if window.width <= 0 or window.height <= 0:
            raise ValueError("Kalimantan window is empty")
        source_window_bounds = rasterio.windows.bounds(window, src.transform)
        out_transform = src.window_transform(window)
        profile = src.profile.copy()
        profile.update(
            driver="GTiff",
            dtype="uint8",
            count=1,
            nodata=0,
            width=int(window.width),
            height=int(window.height),
            transform=out_transform,
            compress="deflate",
            predictor=2,
            tiled=True,
            blockxsize=512,
            blockysize=512,
            BIGTIFF="IF_SAFER",
            photometric="minisblack",
        )

        class_counts: dict[str, int] = {}
        forest_pixels = 0
        valid_pixels = 0
        output_tmp = output.with_suffix(output.suffix + ".part")
        if output_tmp.exists():
            output_tmp.unlink()
        with rasterio.open(output_tmp, "w", **profile) as dst:
            for _, dst_window in dst.block_windows(1):
                read_window = Window(
                    window.col_off + dst_window.col_off,
                    window.row_off + dst_window.row_off,
                    dst_window.width,
                    dst_window.height,
                )
                values = src.read(1, window=read_window, boundless=False)
                unique, counts = np.unique(values, return_counts=True)
                for code, count in zip(unique.tolist(), counts.tolist(), strict=True):
                    class_counts[str(int(code))] = class_counts.get(str(int(code)), 0) + int(count)
                valid = values != 0
                forest = valid & np.isin(values, FOREST_CODES)
                valid_pixels += int(valid.sum())
                forest_pixels += int(forest.sum())
                dst.write(forest.astype("uint8"), 1, window=dst_window)
            dst.update_tags(
                mapbiomas_collection="4.1",
                mapbiomas_collection_version="4.1.1",
                baseline_year="2014",
                mask_definition="1 where MapBiomas class code is 3, 5, or 76; 0 otherwise",
                forest_codes=",".join(str(code) for code in FOREST_CODES),
                source_raster=str(source),
            )
        output_tmp.replace(output)

    report = {
        "schema_version": "mapbiomas-natural-forest-mask/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "validated",
        "source": {
            "path": source.relative_to(ROOT).as_posix(),
            "sha256": _sha256(source),
            "collection": "4.1",
            "collection_version": "4.1.1",
            "baseline_year": 2014,
        },
        "output": {
            "path": output.relative_to(ROOT).as_posix(),
            "sha256": _sha256(output),
            "forest_codes": list(FOREST_CODES),
            "bbox_wgs84": list(KALIMANTAN_BBOX),
            "bounds_wgs84_from_window": list(source_window_bounds),
            "width": int(window.width),
            "height": int(window.height),
            "valid_source_pixels": valid_pixels,
            "natural_forest_pixels": forest_pixels,
            "natural_forest_fraction_of_valid_source": forest_pixels / valid_pixels if valid_pixels else None,
            "class_counts": class_counts,
        },
        "method": "Tiled read of the country-wide MapBiomas raster; no resampling; class codes preserved before binary conversion.",
        "limitations": [
            "This is a 30 m class mask, not a fire-occurrence map.",
            "The 0 class combines MapBiomas nodata and non-natural-forest classes; source class codes remain in the immutable TIFF.",
            "VIIRS forest_fraction still requires grid/pixel intersection and must not be inferred from this mask alone.",
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
    report = build_mask(args.source, args.output, args.report)
    print(json.dumps({
        "status": report["status"],
        "output": report["output"]["path"],
        "report": args.report.resolve().relative_to(ROOT).as_posix(),
        "width": report["output"]["width"],
        "height": report["output"]["height"],
        "natural_forest_fraction_of_valid_source": report["output"]["natural_forest_fraction_of_valid_source"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
