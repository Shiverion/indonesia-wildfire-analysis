"""Path helpers that preserve logical repository paths across data junctions."""

from __future__ import annotations

from pathlib import Path


def logical_relative(root: Path, path: Path) -> str:
    """Return a repository-relative path even when ``data/raw`` is junctioned."""

    root = root.absolute()
    path = Path(path)
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        pass

    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        pass

    raw_anchor = root / "data" / "raw"
    try:
        suffix = resolved.relative_to(raw_anchor.resolve())
    except ValueError as exc:
        raise ValueError(f"Path is outside the repository and approved data junction: {path}") from exc
    return (Path("data/raw") / suffix).as_posix()
