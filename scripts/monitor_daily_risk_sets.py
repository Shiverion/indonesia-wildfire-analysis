"""Print a concise live snapshot of the resumable Phase 1B pipeline."""

from __future__ import annotations

import json
from pathlib import Path

import psutil


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "derived" / "viirs" / "daily_risk_sets"
CLIMATE = ROOT / "data" / "derived" / "viirs" / "daily_risk_sets_with_era5"
FINAL_REPORT = ROOT / "outputs" / "quality" / "daily_risk_set_frame.json"
EXPECTED = 1683


def main() -> int:
    source_receipts = list(SOURCE.rglob("*.json")) if SOURCE.exists() else []
    complete = 0
    no_observation = 0
    matched_cases = 0
    matched_controls = 0
    for path in source_receipts:
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if receipt.get("status") in {"complete", "complete_no_observation"}:
            complete += 1
            no_observation += int(receipt.get("status") == "complete_no_observation")
            matched_cases += int(receipt.get("matched_cases", 0))
            matched_controls += int(receipt.get("matched_controls", 0))
    climate = len(list(CLIMATE.rglob("*.parquet"))) if CLIMATE.exists() else 0
    try:
        final_report = json.loads(FINAL_REPORT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        final_report = {}
    workers = []
    for process in psutil.process_iter(["pid", "name", "cmdline"]):
        command = " ".join(process.info.get("cmdline") or [])
        process_name = str(process.info.get("name") or "").casefold()
        if process_name.startswith("python") and ("build_gee_daily_risk_sets.py" in command or "complete_phase1b_pipeline.py" in command):
            workers.append({"pid": process.info["pid"], "command": command})
    size_bytes = sum(path.stat().st_size for path in SOURCE.rglob("*.parquet")) if SOURCE.exists() else 0
    print(json.dumps({
        "phase": "Phase 1B daily environmental risk set",
        "completed_days": complete,
        "expected_days": EXPECTED,
        "progress_percent": round(100 * complete / EXPECTED, 2),
        "extracted_cases_before_final_deduplication": matched_cases,
        "extracted_controls_before_final_deduplication": matched_controls,
        "validated_case_count": final_report.get("case_count"),
        "validated_control_count": final_report.get("control_count"),
        "validated_matched_set_count": final_report.get("matched_set_count"),
        "final_frame_status": final_report.get("status", "not_finalized"),
        "no_observation_days_so_far": no_observation,
        "era5_days_finalized": climate,
        "local_chunk_size_mib": round(size_bytes / 1024**2, 2),
        "active_workers": workers,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
