"""Wait for parallel extraction, recover failures, finalize, lock, and refresh outputs."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil


ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "outputs" / "quality" / "phase1b_pipeline_supervisor.log"
FINAL_STATUS = ROOT / "outputs" / "quality" / "phase1b_pipeline_supervisor.json"


def log(message: str) -> None:
    stamp = datetime.now(timezone.utc).isoformat()
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"{stamp} {message}\n")
    print(message, flush=True)


def run(command: list[str], *, allowed: set[int] = {0}, cwd: Path = ROOT) -> int:
    log("RUN " + " ".join(command))
    result = subprocess.run(command, cwd=cwd, check=False)
    if result.returncode not in allowed:
        raise RuntimeError(f"command failed with exit code {result.returncode}: {' '.join(command)}")
    return result.returncode


def wait_for_processes(pids: list[int]) -> None:
    remaining = set(pids)
    while remaining:
        remaining = {pid for pid in remaining if psutil.pid_exists(pid)}
        if remaining:
            log(f"Waiting for extraction workers: {sorted(remaining)}")
            time.sleep(60)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wait-pids", nargs="*", type=int, default=[])
    args = parser.parse_args()
    status = {"started_at_utc": datetime.now(timezone.utc).isoformat(), "status": "running"}
    try:
        wait_for_processes(args.wait_pids)
        # A complete rerun is cheap for completed days: the extractor verifies
        # their parquet+receipt pair and skips them. It therefore recovers any
        # day that exhausted retries in the parallel pass.
        run([sys.executable, "scripts/build_gee_daily_risk_sets.py", "--worker-id", "recovery", "--retries", "12"])
        run([sys.executable, "scripts/finalize_daily_risk_sets.py"])
        run([sys.executable, "scripts/research.py", "phase1b-audit"])
        lock_path = ROOT / "outputs" / "locks" / "locked_test_inputs.json"
        if not lock_path.exists():
            run([sys.executable, "scripts/research.py", "lock-test"])
        else:
            run([sys.executable, "scripts/research.py", "verify-test-lock"])
        run([sys.executable, "scripts/research.py", "phase1b-audit"])
        run([sys.executable, "scripts/research.py", "build-explorer"])
        app_root = ROOT / "apps" / "evidence-explorer"
        run(["npm.cmd", "run", "check"], cwd=app_root)
        run(["npm.cmd", "run", "build"], cwd=app_root)
        run([
            "git", "add",
            "outputs/quality/daily_risk_set_frame.json",
            "outputs/quality/phase1b_readiness.json",
            "outputs/locks/locked_test_inputs.json",
            "outputs/evidence-explorer",
            "apps/evidence-explorer/data/evidence-explorer.json",
        ])
        status["status"] = "complete"
        status["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
        status["phase1b_readiness"] = "outputs/quality/phase1b_readiness.json"
    except Exception as exc:
        status["status"] = "failed"
        status["failed_at_utc"] = datetime.now(timezone.utc).isoformat()
        status["error"] = f"{type(exc).__name__}: {exc}"
        log(status["error"])
    FINAL_STATUS.parent.mkdir(parents=True, exist_ok=True)
    FINAL_STATUS.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    return 0 if status["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
