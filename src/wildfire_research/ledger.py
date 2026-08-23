"""Hash-linked implementation ledger for protocol-phase evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LEDGER_SCHEMA_VERSION = "1.0"


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _read_entries(path: Path) -> list[dict]:
    if not path.exists():
        return []
    entries: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"ledger line {line_number} is not valid JSON") from exc
    return entries


def append_phase_entry(
    path: Path,
    *,
    phase: str,
    status: str,
    note: str,
    evidence: list[str] | None = None,
    logged_at: datetime | None = None,
) -> dict:
    """Append a hash-linked phase entry. Existing records are never rewritten."""
    entries = _read_entries(path)
    previous_hash = entries[-1]["entry_sha256"] if entries else None
    entry = {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "sequence": len(entries) + 1,
        "logged_at_utc": (logged_at or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat(),
        "phase": phase,
        "status": status,
        "note": note,
        "evidence": evidence or [],
        "previous_entry_sha256": previous_hash,
    }
    entry["entry_sha256"] = _canonical_hash({key: value for key, value in entry.items() if key != "entry_sha256"})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def verify_phase_ledger(path: Path) -> dict:
    """Verify JSON, sequence, hash, and predecessor linkage for an evidence ledger."""
    try:
        entries = _read_entries(path)
    except ValueError as exc:
        return {"valid": False, "reason": "invalid_json", "detail": str(exc), "entry_count": 0}
    previous_hash = None
    for expected_sequence, entry in enumerate(entries, start=1):
        if entry.get("schema_version") != LEDGER_SCHEMA_VERSION:
            return {"valid": False, "reason": "unsupported_schema", "sequence": expected_sequence}
        if entry.get("sequence") != expected_sequence:
            return {"valid": False, "reason": "sequence_gap", "sequence": expected_sequence}
        if entry.get("previous_entry_sha256") != previous_hash:
            return {"valid": False, "reason": "broken_predecessor_link", "sequence": expected_sequence}
        expected_hash = _canonical_hash({key: value for key, value in entry.items() if key != "entry_sha256"})
        if entry.get("entry_sha256") != expected_hash:
            return {"valid": False, "reason": "entry_tampered", "sequence": expected_sequence}
        previous_hash = entry["entry_sha256"]
    return {
        "valid": True,
        "reason": "valid",
        "entry_count": len(entries),
        "latest_entry_sha256": previous_hash,
    }
