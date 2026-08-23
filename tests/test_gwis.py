from datetime import date
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wildfire_research.enso import RoniRecord
from wildfire_research.gwis import GwisMonthlyRecord, build_gwis_context_markdown, parse_gwis_zip


class GwisTests(unittest.TestCase):
    def test_rejects_noncanonical_archive_member(self):
        import io
        import zipfile

        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("wrong.csv", "gid_0;gid_1;year;month;ba_area_ha;ba_count\n")
        with self.assertRaises(ValueError):
            parse_gwis_zip(stream.getvalue())

    def test_report_remains_explicitly_nonprimary(self):
        rows = [
            GwisMonthlyRecord("IDN.12_1", "Kalimantan Barat", 2015, 8, 100.0, 1),
            GwisMonthlyRecord("IDN.12_1", "Kalimantan Barat", 2016, 8, 50.0, 1),
            GwisMonthlyRecord("IDN.12_1", "Kalimantan Barat", 2017, 8, 75.0, 1),
        ]
        roni = [
            RoniRecord("JJA", 2015, date(2015, 8, 31), 1.0),
            RoniRecord("JJA", 2016, date(2016, 8, 31), -1.0),
            RoniRecord("JJA", 2017, date(2017, 8, 31), 0.0),
        ]
        report = build_gwis_context_markdown(rows, roni)
        self.assertIn("not the primary 1 km", report)
        self.assertIn("not a test of the human-accessibility hypothesis", report)


if __name__ == "__main__":
    unittest.main()
