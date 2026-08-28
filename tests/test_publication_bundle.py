from __future__ import annotations

import json
from pathlib import Path

from scripts.build_publication_bundle import FORBIDDEN_COLUMN_PARTS, build_manifest


ROOT = Path(__file__).resolve().parents[1]


def test_publication_manifest_is_coordinate_and_credential_free() -> None:
    manifest = build_manifest()
    assert manifest["contains_coordinates"] is False
    assert manifest["contains_credentials"] is False
    for item in manifest["files"]:
        lowered = {column.lower() for column in item.get("columns", [])}
        assert not lowered.intersection(FORBIDDEN_COLUMN_PARTS)
        assert ".env" not in item["archive_path"].lower()
        assert "cell_centres" not in item["archive_path"].lower()


def test_report_artifact_has_complete_reading_path() -> None:
    artifact = json.loads(
        (ROOT / "publication" / "report-artifact.json").read_text(encoding="utf-8")
    )
    assert artifact["surface"] == "report"
    block_types = [item["type"] for item in artifact["manifest"]["blocks"]]
    assert block_types[0] == "markdown"
    assert "metric-strip" in block_types
    assert "chart" in block_types
    assert "table" in block_types
    joined = json.dumps(artifact).lower()
    assert "api_key" not in joined
    assert "longitude" not in joined
    assert "latitude" not in joined
