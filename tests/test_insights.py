from datetime import date
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wildfire_research.enso import RoniRecord
from wildfire_research.insights import build_enso_context_markdown, classify_episodes


class InsightTests(unittest.TestCase):
    def test_identifies_five_season_el_nino_run(self):
        records = [
            RoniRecord("JFM", 2023, date(2023, 3, 31), 0.6),
            RoniRecord("FMA", 2023, date(2023, 4, 30), 0.7),
            RoniRecord("MAM", 2023, date(2023, 5, 31), 0.8),
            RoniRecord("AMJ", 2023, date(2023, 6, 30), 0.9),
            RoniRecord("MJJ", 2023, date(2023, 7, 31), 1.0),
        ]
        episodes = classify_episodes(records)
        self.assertEqual(len(episodes), 1)
        self.assertEqual(episodes[0].state, "El Niño threshold")
        self.assertEqual(episodes[0].peak_anomaly_c, 1.0)

    def test_report_declares_non_causal_scope(self):
        records = [
            RoniRecord("JJA", 2015, date(2015, 8, 31), 0.5),
            RoniRecord("JAS", 2015, date(2015, 9, 30), 0.7),
            RoniRecord("ASO", 2015, date(2015, 10, 31), 0.9),
            RoniRecord("SON", 2015, date(2015, 11, 30), 1.1),
        ]
        report = build_enso_context_markdown(records)
        self.assertIn("does **not** test the human-accessibility wildfire hypothesis", report)
        self.assertIn("2015", report)


if __name__ == "__main__":
    unittest.main()
