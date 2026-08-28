"""Inventory raw raster archives and enforce the zero-budget storage policy."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCES = {
    "chirps": ROOT / "data" / "raw" / "chirps",
    "mod13q1": ROOT / "data" / "raw" / "mod13q1",
    "viirs": ROOT / "data" / "raw" / "viirs",
}


def inventory(path: Path) -> dict[str, object]:
    files = [item for item in path.rglob("*") if item.is_file()] if path.exists() else []
    by_extension: dict[str, dict[str, int]] = {}
    total = 0
    for item in files:
        size = item.stat().st_size
        total += size
        ext = item.suffix.lower() or "[none]"
        bucket = by_extension.setdefault(ext, {"files": 0, "bytes": 0})
        bucket["files"] += 1
        bucket["bytes"] += size
    return {
        "path": path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path),
        "exists": path.exists(),
        "files": len(files),
        "bytes": total,
        "gib": round(total / (1024**3), 3),
        "by_extension": dict(sorted(by_extension.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "quality" / "raw_source_inventory.json")
    parser.add_argument("--max-gib", type=float, default=60.0)
    args = parser.parse_args()

    sources = {name: inventory(path) for name, path in DEFAULT_SOURCES.items()}
    total_bytes = sum(int(item["bytes"]) for item in sources.values())
    report = {
        "schema_version": "raw-source-inventory/v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "policy": {
            "full_archives_allowed": False,
            "paid_storage_allowed": False,
            "max_local_raw_gib": args.max_gib,
        },
        "sources": sources,
        "total": {
            "files": sum(int(item["files"]) for item in sources.values()),
            "bytes": total_bytes,
            "gib": round(total_bytes / (1024**3), 3),
            "within_policy": total_bytes <= args.max_gib * (1024**3),
        },
        "interpretation": "Inventory includes payloads and small manifests/metadata; it does not include ERA5-Land or derived outputs.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for name, item in sources.items():
        print(f"{name}: {item['files']} files, {item['gib']:.2f} GiB")
    print(f"TOTAL: {report['total']['files']} files, {report['total']['gib']:.2f} GiB")
    print(f"Policy ({args.max_gib:.0f} GiB): {'PASS' if report['total']['within_policy'] else 'STOP'}")
    print(f"Report: {args.output.relative_to(ROOT)}")
    return 0 if report["total"]["within_policy"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
