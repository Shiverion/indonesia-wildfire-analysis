from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wildfire_research.quality import (
    asset_local_evidence,
    create_immutable_lock,
    fingerprint_paths,
    verify_immutable_lock,
    workspace_path,
)


class QualityHelpersTests(unittest.TestCase):
    def test_ready_directory_with_only_gitkeep_does_not_pass_gate(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            asset_dir = root / "data" / "raw" / "viirs"
            asset_dir.mkdir(parents=True)
            (asset_dir / ".gitkeep").write_text("\n", encoding="utf-8")
            asset = {
                "id": "viirs",
                "status": "ready",
                "expected_local_path": "data/raw/viirs",
            }

            evidence = asset_local_evidence(root, asset)

            self.assertTrue(evidence["local_path_exists"])
            self.assertEqual(evidence["payload_file_count"], 0)
            self.assertFalse(evidence["gate_ready"])

    def test_populated_ready_asset_passes_local_evidence_gate(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / "data" / "raw" / "chirps" / "rainfall.tif"
            payload.parent.mkdir(parents=True)
            payload.write_bytes(b"rainfall")
            asset = {
                "id": "chirps",
                "status": "ready",
                "expected_local_path": "data/raw/chirps",
            }

            evidence = asset_local_evidence(root, asset, include_hashes=True)

            self.assertTrue(evidence["gate_ready"])
            self.assertEqual(evidence["payload_file_count"], 1)
            self.assertEqual(len(evidence["files"][0]["sha256"]), 64)

    def test_workspace_path_rejects_escape(self):
        with TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                workspace_path(Path(directory), "../outside")

    def test_lock_verifies_then_detects_content_and_membership_changes(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config").mkdir()
            (root / "data" / "raw").mkdir(parents=True)
            (root / "outputs" / "locks").mkdir(parents=True)
            (root / "config" / "study.json").write_text(json.dumps({"locked_test": [2024, 2025]}), encoding="utf-8")
            raw_file = root / "data" / "raw" / "provider.bin"
            raw_file.write_bytes(b"first-version")
            lock_path = root / "outputs" / "locks" / "preunlock.json"

            lock = create_immutable_lock(
                root,
                lock_path,
                ["config/study.json", "data/raw"],
                label="pre-unlock 2024-2025 archive",
                created_at=datetime(2026, 8, 20, tzinfo=timezone.utc),
            )

            self.assertEqual(lock["file_count"], 2)
            self.assertTrue(verify_immutable_lock(root, lock_path)["valid"])
            with self.assertRaises(FileExistsError):
                create_immutable_lock(root, lock_path, ["config/study.json"], label="replacement")

            raw_file.write_bytes(b"changed-version")
            changed = verify_immutable_lock(root, lock_path)
            self.assertFalse(changed["valid"])
            self.assertEqual(changed["reason"], "locked_input_changed")

            raw_file.write_bytes(b"first-version")
            (root / "data" / "raw" / "later-arrival.bin").write_bytes(b"new data")
            membership_changed = verify_immutable_lock(root, lock_path)
            self.assertFalse(membership_changed["valid"])
            self.assertEqual(membership_changed["reason"], "locked_input_changed")

    def test_fingerprint_requires_actual_payload(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            empty = root / "data" / "raw"
            empty.mkdir(parents=True)
            (empty / ".gitkeep").write_text("\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                fingerprint_paths(root, ["data/raw"])


if __name__ == "__main__":
    unittest.main()
