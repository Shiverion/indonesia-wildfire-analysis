"""Run the registered PPE feature-leakage and provenance gate."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from wildfire_research.feature_gate import audit_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "config" / "ppe_feature_manifest.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs" / "quality" / "ppe_feature_gate.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    result = audit_manifest(manifest)
    result["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    result["manifest"] = str(args.manifest.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print(f"PPE feature gate: {'PASS' if result['ready'] else 'FAIL'}")
    print(f"Audit: {args.output}")
    for row in result["candidates"]:
        print(f"  {row['decision'].upper():6} {row['name']} ({row['priority_score']:.2f})")
    for row in result["negative_controls"]:
        print(f"  CONTROL {row['decision'].upper():6} {row['name']}")
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
