from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WINDOWS_USER_PATH = re.compile(r"[A-Za-z]:\\\\Users\\\\", re.IGNORECASE)


def test_tracked_quality_receipts_do_not_publish_windows_user_paths() -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "outputs/quality/*.json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    for relative in tracked:
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        assert not WINDOWS_USER_PATH.search(text), f"workstation path leaked by {path.relative_to(ROOT)}"
