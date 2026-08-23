from datetime import datetime, timezone
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wildfire_research.ledger import append_phase_entry, verify_phase_ledger


class PhaseLedgerTests(unittest.TestCase):
    def test_hash_linked_entries_verify(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            timestamp = datetime(2026, 8, 20, tzinfo=timezone.utc)
            first = append_phase_entry(path, phase="Phase 0", status="complete", note="config frozen", logged_at=timestamp)
            second = append_phase_entry(path, phase="Phase 1", status="blocked", note="awaiting swaths", logged_at=timestamp)
            result = verify_phase_ledger(path)
            self.assertTrue(result["valid"])
            self.assertEqual(second["previous_entry_sha256"], first["entry_sha256"])
            self.assertEqual(result["entry_count"], 2)

    def test_tampered_entry_fails_verification(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            append_phase_entry(path, phase="Phase 0", status="complete", note="original")
            path.write_text(path.read_text(encoding="utf-8").replace("original", "altered"), encoding="utf-8")
            result = verify_phase_ledger(path)
            self.assertFalse(result["valid"])
            self.assertEqual(result["reason"], "entry_tampered")


if __name__ == "__main__":
    unittest.main()
