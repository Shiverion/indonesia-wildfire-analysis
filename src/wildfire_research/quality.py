"""Local-only provenance and phase-gate checks for the wildfire protocol.

These helpers intentionally make no network requests and do not depend on a
provider account.  They distinguish a populated local archive from an empty
directory placeholder, and provide a one-way file lock for a frozen analysis
archive.  A file lock establishes byte-level reproducibility; it cannot by
itself prove that a researcher did not inspect a locked test outcome before
the lock was written.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .paths import logical_relative


LOCK_SCHEMA_VERSION = "1.0"
_PLACEHOLDER_FILENAMES = frozenset({".gitkeep", ".DS_Store", "Thumbs.db"})


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of one regular file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_json_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def workspace_path(root: Path, relative_path: str | Path) -> Path:
    """Resolve a manifest path while allowing the approved data junction.

    The repository's ``data/raw`` directory may be a deliberate Windows
    junction to a larger local disk.  Validate the manifest path lexically so
    that this approved storage relocation does not look like an escape, while
    still rejecting absolute paths and explicit ``..`` traversal.
    """
    root = root.absolute()
    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise ValueError(f"manifest path must be workspace-relative: {relative_path!s}")
    if ".." in candidate.parts:
        raise ValueError(f"manifest path must not contain parent traversal: {relative_path!s}")
    resolved = root / candidate
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"manifest path escapes the workspace: {relative_path!s}") from exc
    return resolved


def is_payload_file(path: Path) -> bool:
    """Return whether a file is evidence of a retrieved/provider data payload."""
    return (
        path.is_file()
        and path.name not in _PLACEHOLDER_FILENAMES
        and "__pycache__" not in path.parts
    )


def payload_files(path: Path) -> list[Path]:
    """Return deterministic, non-placeholder files under an expected asset path."""
    if not path.exists():
        return []
    if path.is_file():
        return [path] if is_payload_file(path) else []
    return sorted(
        (candidate for candidate in path.rglob("*") if is_payload_file(candidate)),
        key=lambda candidate: candidate.as_posix().casefold(),
    )


def fingerprint_paths(root: Path, source_paths: Iterable[str | Path]) -> dict[str, Any]:
    """Build a deterministic full-content inventory for existing local inputs.

    Every requested source must exist and contain at least one non-placeholder
    file.  Directories are recursive so later additions and deletions are
    detectable when the fingerprint is verified.
    """
    root = root.resolve()
    sources = sorted({Path(path).as_posix() for path in source_paths})
    if not sources:
        raise ValueError("at least one source path is required for a fingerprint")

    entries_by_path: dict[str, dict[str, Any]] = {}
    for source in sources:
        resolved = workspace_path(root, source)
        if not resolved.exists():
            raise FileNotFoundError(f"lock input is missing: {source}")
        files = payload_files(resolved)
        if not files:
            raise ValueError(f"lock input has no non-placeholder files: {source}")
        for file_path in files:
            relative = logical_relative(root, file_path)
            entries_by_path[relative] = {
                "path": relative,
                "size_bytes": file_path.stat().st_size,
                "sha256": sha256_file(file_path),
            }

    files = [entries_by_path[path] for path in sorted(entries_by_path)]
    return {
        "inputs": sources,
        "files": files,
        "file_count": len(files),
        "inventory_sha256": _canonical_json_sha256(files),
    }


def asset_local_evidence(root: Path, asset: dict[str, Any], *, include_hashes: bool = False) -> dict[str, Any]:
    """Inspect an asset without contacting its provider.

    ``status == 'ready'`` is deliberately insufficient: an expected directory
    must contain at least one real payload file.  Hashing is optional because
    full swath archives can be large; freeze hashes before opening the locked
    test, not by relying on a directory's existence.
    """
    asset_id = str(asset.get("id", "<unknown>"))
    expected_path = asset.get("expected_local_path")
    if not isinstance(expected_path, str) or not expected_path:
        raise ValueError(f"asset {asset_id!r} has no expected_local_path")
    resolved = workspace_path(root, expected_path)
    files = payload_files(resolved)
    evidence_files: list[dict[str, Any]] = []
    for file_path in files:
        row: dict[str, Any] = {
            "path": logical_relative(root, file_path),
            "size_bytes": file_path.stat().st_size,
        }
        if include_hashes:
            row["sha256"] = sha256_file(file_path)
        evidence_files.append(row)

    return {
        "asset_id": asset_id,
        "manifest_status": asset.get("status"),
        "expected_local_path": expected_path,
        "local_path_exists": resolved.exists(),
        "payload_file_count": len(evidence_files),
        "locally_populated": bool(evidence_files),
        "files": evidence_files,
        "gate_ready": asset.get("status") == "ready" and bool(evidence_files),
    }


def create_immutable_lock(
    root: Path,
    lock_path: Path,
    source_paths: Iterable[str | Path],
    *,
    label: str,
    created_at: datetime | None = None,
) -> dict[str, Any]:
    """Create a new immutable archive lock; overwrite is always refused.

    The caller should create this before unlocking the 2024--2025 test archive.
    It covers configuration, manifests, and frozen inputs supplied in
    ``source_paths``.  It must be stored outside all listed input directories,
    otherwise its own creation would mutate the inventory it records.
    """
    root = root.resolve()
    lock_path = lock_path.resolve()
    try:
        lock_path.relative_to(root)
    except ValueError as exc:
        raise ValueError("lock path must remain inside the workspace") from exc
    if lock_path.exists():
        raise FileExistsError(f"immutable lock already exists: {lock_path}")

    fingerprint = fingerprint_paths(root, source_paths)
    for source in fingerprint["inputs"]:
        source_path = workspace_path(root, source)
        if source_path.is_dir() and lock_path.is_relative_to(source_path):
            raise ValueError("lock path must not be inside a locked input directory")
        if source_path == lock_path:
            raise ValueError("lock path cannot be one of its own inputs")

    created_at = created_at or datetime.now(timezone.utc)
    lock = {
        "schema_version": LOCK_SCHEMA_VERSION,
        "label": label,
        "created_at_utc": created_at.astimezone(timezone.utc).isoformat(),
        "purpose": "Byte-level reproducibility lock; does not prove outcome blinding before lock creation.",
        **fingerprint,
    }
    lock["lock_sha256"] = _canonical_json_sha256({key: value for key, value in lock.items() if key != "lock_sha256"})
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(lock, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return lock


def verify_immutable_lock(root: Path, lock_path: Path) -> dict[str, Any]:
    """Verify an immutable lock against its current local input inventory."""
    root = root.resolve()
    lock_path = lock_path.resolve()
    public_lock_path = logical_relative(root, lock_path)
    if not lock_path.exists():
        return {"valid": False, "reason": "lock_missing", "lock_path": public_lock_path}
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"valid": False, "reason": "lock_invalid_json", "detail": str(exc), "lock_path": public_lock_path}
    if lock.get("schema_version") != LOCK_SCHEMA_VERSION:
        return {"valid": False, "reason": "unsupported_lock_schema", "lock_path": public_lock_path}

    recorded_lock_hash = lock.get("lock_sha256")
    computed_lock_hash = _canonical_json_sha256({key: value for key, value in lock.items() if key != "lock_sha256"})
    if recorded_lock_hash != computed_lock_hash:
        return {"valid": False, "reason": "lock_file_tampered", "lock_path": public_lock_path}
    try:
        current = fingerprint_paths(root, lock["inputs"])
    except (FileNotFoundError, ValueError) as exc:
        return {"valid": False, "reason": "locked_input_unavailable", "detail": str(exc), "lock_path": public_lock_path}

    same_files = current["files"] == lock.get("files")
    same_inventory_hash = current["inventory_sha256"] == lock.get("inventory_sha256")
    return {
        "valid": same_files and same_inventory_hash,
        "reason": "valid" if same_files and same_inventory_hash else "locked_input_changed",
        "lock_path": public_lock_path,
        "recorded_inventory_sha256": lock.get("inventory_sha256"),
        "current_inventory_sha256": current["inventory_sha256"],
        "recorded_file_count": lock.get("file_count"),
        "current_file_count": current["file_count"],
    }
