#!/usr/bin/env python3
"""Verify coordinate-free inputs and reproduce Phase 3 publication outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "publication" / "data" / "manifest.json"
RECEIPT_PATH = ROOT / "outputs" / "quality" / "publication_reproduction.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(command: list[str], cwd: Path = ROOT) -> dict:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    result = {
        "command": command,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }
    if completed.returncode:
        raise RuntimeError(json.dumps(result, indent=2))
    return result


def extract_bundle(bundle_path: Path) -> None:
    with zipfile.ZipFile(bundle_path) as bundle:
        names = set(bundle.namelist())
        manifest = json.loads(bundle.read("publication/data/manifest.json"))
        for entry in manifest["files"]:
            archive_path = entry["archive_path"]
            if archive_path not in names:
                raise ValueError(f"Bundle is missing {archive_path}")
            target = (ROOT / archive_path).resolve()
            if ROOT.resolve() not in target.parents:
                raise ValueError(f"Unsafe bundle target: {archive_path}")
            if target.exists() and sha256_file(target) != entry["sha256"]:
                raise FileExistsError(
                    f"Refusing to overwrite a different local file: {target}. Move it first."
                )
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(archive_path) as source, target.open("wb") as destination:
                    for block in iter(lambda: source.read(1024 * 1024), b""):
                        destination.write(block)


def verify_inputs(manifest: dict) -> list[dict]:
    results = []
    for entry in manifest["files"]:
        path = ROOT / entry["source_path"]
        actual = sha256_file(path) if path.is_file() else None
        results.append(
            {
                "path": entry["source_path"],
                "expected_sha256": entry["sha256"],
                "actual_sha256": actual,
                "passed": actual == entry["sha256"],
            }
        )
    if not all(item["passed"] for item in results):
        raise ValueError("One or more publication inputs failed manifest verification")
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--include-dashboard", action="store_true")
    parser.add_argument("--receipt", type=Path, default=RECEIPT_PATH)
    args = parser.parse_args()
    if args.bundle:
        extract_bundle(args.bundle.resolve())
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    checks = verify_inputs(manifest)
    commands = [
        run([sys.executable, "analysis/phase3_land_change.py", "--run-models"]),
        run([sys.executable, "analysis/phase3_publication_robustness.py"]),
        run([sys.executable, "-m", "pytest", "-q"]),
    ]
    if args.include_dashboard:
        commands.append(run(["npm.cmd", "run", "build"], ROOT / "apps" / "evidence-explorer"))
    receipt = {
        "schema_version": "publication-reproduction/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "manifest": str(MANIFEST_PATH.relative_to(ROOT)).replace("\\", "/"),
        "input_checks": checks,
        "commands": commands,
        "status": "passed",
        "dashboard_included": args.include_dashboard,
    }
    receipt_path = args.receipt if args.receipt.is_absolute() else ROOT / args.receipt
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "passed", "receipt": str(receipt_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
