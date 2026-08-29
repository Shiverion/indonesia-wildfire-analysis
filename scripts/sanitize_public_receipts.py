#!/usr/bin/env python3
"""Remove workstation-specific path prefixes from tracked quality receipts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
QUALITY_ROOT = ROOT / "outputs" / "quality"


def sanitize_text(value: str) -> str:
    replacements = (
        (str(ROOT), "<REPO_ROOT>"),
        (str(ROOT).replace("\\", "\\\\"), "<REPO_ROOT>"),
        (ROOT.as_posix(), "<REPO_ROOT>"),
        (str(Path.home()), "<USER_HOME>"),
        (str(Path.home()).replace("\\", "\\\\"), "<USER_HOME>"),
        (Path.home().as_posix(), "<USER_HOME>"),
    )
    sanitized = value
    for source, replacement in replacements:
        sanitized = sanitized.replace(source, replacement)
    lowered = sanitized.lower().replace("/", "\\")
    if lowered.endswith("\\scripts\\python.exe") and sanitized.startswith(("<REPO_ROOT>", "<USER_HOME>")):
        return "python"
    return sanitized


def sanitize(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, dict):
        return {key: sanitize(item) for key, item in value.items()}
    return value


def main() -> int:
    changed: list[str] = []
    for path in sorted(QUALITY_ROOT.glob("*.json")):
        original = json.loads(path.read_text(encoding="utf-8"))
        public = sanitize(original)
        if public == original:
            continue
        path.write_text(json.dumps(public, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        changed.append(path.relative_to(ROOT).as_posix())
    print(json.dumps({"status": "passed", "sanitized_receipts": changed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
