#!/usr/bin/env python3
"""Index downloaded VNP14/VNP03 pairs before building the true opportunity frame."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wildfire_research.viirs import write_index  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hash", action="store_true", help="hash every granule (reads the full files)")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "derived" / "viirs")
    parser.add_argument("--quality-path", type=Path, default=ROOT / "outputs" / "quality" / "viirs_pair_index.json")
    args = parser.parse_args()
    payload = write_index(ROOT, output_dir=args.output_dir, quality_path=args.quality_path, hash_files=args.hash)
    print(json.dumps({"summary": payload["summary"], "denominator_ready": payload["denominator_ready"], "outputs": payload["outputs"]}, indent=2))


if __name__ == "__main__":
    main()

