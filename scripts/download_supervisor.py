"""Keep a long-running download alive and retry a failed full job.

The first invocation can point at an already-running PID.  Once that process
exits, the supervisor checks its manifest; only an incomplete or failed
manifest triggers a restart.  Existing payloads are retained and the patched
downloaders skip them or retry only the missing requests.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAX_RESTARTS = 20


def pid_exists(pid: int) -> bool:
    try:
        import ctypes

        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        return False
    except (AttributeError, OSError):
        try:
            import os

            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False


def manifest_complete(kind: str, root: Path, started_at: datetime) -> bool:
    path = {
        "chirps": root / "data/raw/chirps/download_manifest.json",
        "mod13q1": root / "data/raw/mod13q1/download_manifest.json",
        "viirs": root / "data/raw/viirs/download_manifest.json",
    }[kind]
    if not path.is_file():
        return False
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        retrieved = datetime.fromisoformat(str(manifest["retrieved_at_utc"]).replace("Z", "+00:00"))
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False
    if retrieved < started_at or manifest.get("temporal") != ["2015-01-01", "2025-12-31"]:
        return False
    records = manifest.get("records", [])
    if not records or any(record.get("search_count", 0) < 1 for record in records):
        return False
    if kind == "chirps":
        return not any(record.get("status") == "download_error" for record in records)
    if kind == "viirs":
        bad = {"laads_access_error", "download_error", "vnp03_not_found", "unmatched_vnp14_name"}
        return not any(item.get("status") in bad for record in records for item in record.get("matches", []))
    return True


def command_for(kind: str) -> list[str]:
    """Return the historical full-archive command only for explicit use."""
    if kind == "chirps":
        return [
            sys.executable,
            "scripts/download_chirps.py",
            "--start",
            "2015-01-01",
            "--end",
            "2025-12-31",
            "--allow-large-download",
        ]
    return [
        sys.executable,
        "scripts/download_earthdata.py",
        kind,
        "--start",
        "2015-01-01",
        "--end",
        "2025-12-31",
        "--allow-large-download",
    ]


def supervise(kind: str, existing_pid: int, root: Path, max_restarts: int) -> int:
    log_dir = root / "outputs/download_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(timezone.utc)
    while pid_exists(existing_pid):
        time.sleep(10)
    if manifest_complete(kind, root, started_at):
        (log_dir / f"{kind}.watchdog.log").open("a", encoding="utf-8").write(
            f"{datetime.now(timezone.utc).isoformat()} existing job completed successfully\n"
        )
        return 0
    for attempt in range(1, max_restarts + 1):
        stdout_path = log_dir / f"{kind}_retry_{attempt:02d}.stdout.log"
        stderr_path = log_dir / f"{kind}_retry_{attempt:02d}.stderr.log"
        with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
            result = subprocess.run(command_for(kind), cwd=root, stdout=stdout, stderr=stderr, check=False)
        with (log_dir / f"{kind}.watchdog.log").open("a", encoding="utf-8") as log:
            log.write(f"{datetime.now(timezone.utc).isoformat()} retry={attempt} exit_code={result.returncode}\n")
        if result.returncode == 0 and manifest_complete(kind, root, started_at):
            return 0
        time.sleep(min(300, 10 * attempt))
    with (log_dir / f"{kind}.watchdog.log").open("a", encoding="utf-8") as log:
        log.write(f"{datetime.now(timezone.utc).isoformat()} exhausted {max_restarts} retries\n")
    return 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=("chirps", "mod13q1", "viirs"))
    parser.add_argument("--existing-pid", type=int, required=True)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--max-restarts", type=int, default=MAX_RESTARTS)
    parser.add_argument(
        "--allow-large-download",
        action="store_true",
        help="required to let this watchdog restart the historical 2015-2025 archive",
    )
    args = parser.parse_args()
    if not args.allow_large_download:
        parser.error(
            "full-archive watchdog is disabled by the zero-budget policy; "
            "use event-level/year-bounded acquisition instead"
        )
    return supervise(args.kind, args.existing_pid, args.root.resolve(), args.max_restarts)


if __name__ == "__main__":
    raise SystemExit(main())
