from datetime import date
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wildfire_research.enso import latest_complete_before, parse_roni_text


RONI_FIXTURE = """SEAS   YR  ANOM
NDJ  2024 -1.01
DJF  2025 -1.10
JFM  2025 -0.80
"""


class RoniParsingTests(unittest.TestCase):
    def test_parses_end_dates_across_year_boundary(self):
        records = parse_roni_text(RONI_FIXTURE)
        self.assertEqual(records[0].end_date, date(2025, 1, 31))
        self.assertEqual(records[1].end_date, date(2025, 2, 28))

    def test_selects_only_a_fully_completed_season(self):
        records = parse_roni_text(RONI_FIXTURE)
        selected = latest_complete_before(records, date(2025, 3, 1))
        self.assertEqual(selected.season, "DJF")
        self.assertEqual(selected.season_year, 2025)

    def test_rejects_unknown_season(self):
        with self.assertRaises(ValueError):
            parse_roni_text("SEAS YR ANOM\nBAD 2025 0.1\n")


if __name__ == "__main__":
    unittest.main()
