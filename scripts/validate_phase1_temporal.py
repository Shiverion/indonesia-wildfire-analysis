#!/usr/bin/env python3
"""Run local-only temporal support QA for Phase 1 assets."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wildfire_research.temporal_qa import run_temporal_qa  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="outputs/quality/temporal_support_qa.json")
    args = parser.parse_args()
    payload = run_temporal_qa(ROOT)
    payload["validated_at_utc"] = datetime.now(timezone.utc).isoformat()
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": output.relative_to(ROOT).as_posix(),
        "status": payload["status"],
        "phase_1_unlock": payload["phase_1_unlock"],
        "assets": {key: value["status"] for key, value in payload["assets"].items()},
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
