#!/usr/bin/env python3
"""Screen paired VIIRS swaths without constructing a fire-opportunity denominator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wildfire_research.viirs_opportunity import DEFAULT_BBOX, build_summary  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, help="screen only the first N paired swaths")
    parser.add_argument("--bbox", nargs=4, type=float, metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"), default=DEFAULT_BBOX)
    args = parser.parse_args()
    payload = build_summary(ROOT, bbox=args.bbox, limit=args.limit)
    print(json.dumps({"summary": payload["summary"], "outputs": payload["outputs"]}, indent=2))
    return 0 if payload["summary"]["swaths_failed"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

