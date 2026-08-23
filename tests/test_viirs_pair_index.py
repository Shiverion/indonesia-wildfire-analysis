from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wildfire_research.viirs import index_pairs, parse_granule_name, write_index


class ViirsPairIndexTests(unittest.TestCase):
    def test_parser_uses_acquisition_stamp_not_processing_stamp(self):
        parsed = parse_granule_name("VNP14IMG.A2015182.0554.002.2024064161121.nc")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["pair_key"], "2015182.0554")
        self.assertEqual(parsed["acquisition_utc"], "2015-07-01T05:54:00Z")

    def test_pairs_are_not_silently_converted_to_negatives(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            vnp14 = root / "data/raw/viirs/VNP14IMG"
            vnp03 = root / "data/raw/viirs/VNP03IMG"
            vnp14.mkdir(parents=True)
            vnp03.mkdir(parents=True)
            (vnp14 / "VNP14IMG.A2015001.0548.002.fake.nc").write_bytes(b"fire")
            (vnp03 / "VNP03IMG.A2015001.0548.002.fake.nc").write_bytes(b"geo")
            (vnp14 / "VNP14IMG.A2015002.0548.002.fake.nc").write_bytes(b"fire-only")
            result = index_pairs(root)
            self.assertEqual(result["summary"]["paired_rows"], 1)
            self.assertEqual(result["summary"]["unpaired_or_ambiguous_rows"], 1)
            self.assertFalse(result["denominator_ready"])
            self.assertTrue(all(row["negative_frame_status"] == "not_built" for row in result["rows"]))

    def test_writer_emits_machine_readable_csv_and_quality_receipt(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            vnp14 = root / "data/raw/viirs/VNP14IMG"
            vnp03 = root / "data/raw/viirs/VNP03IMG"
            vnp14.mkdir(parents=True)
            vnp03.mkdir(parents=True)
            (vnp14 / "VNP14IMG.A2015001.0548.002.fake.nc").write_bytes(b"fire")
            (vnp03 / "VNP03IMG.A2015001.0548.002.fake.nc").write_bytes(b"geo")
            payload = write_index(root)
            self.assertTrue((root / payload["outputs"]["csv"]).is_file())
            report = json.loads((root / payload["outputs"]["quality_json"]).read_text(encoding="utf-8"))
            self.assertEqual(report["summary"]["paired_rows"], 1)
            self.assertEqual(report["negative_frame"]["status"], "not_built")


if __name__ == "__main__":
    unittest.main()

