from datetime import date
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wildfire_research.enso import RoniRecord
from wildfire_research.gwis import GwisMonthlyRecord
from wildfire_research.sipongi import SipongiRecord
from wildfire_research.synthesis import build_preliminary_synthesis_markdown


class SynthesisTests(unittest.TestCase):
    def test_synthesis_keeps_primary_hypothesis_not_identifiable(self):
        roni = [
            RoniRecord("JJA", 2015, date(2015, 8, 31), 1.0),
            RoniRecord("JJA", 2016, date(2016, 8, 31), 0.0),
            RoniRecord("JJA", 2017, date(2017, 8, 31), -1.0),
        ]
        gwis = [
            GwisMonthlyRecord("IDN.12_1", "Kalimantan Barat", 2015, 8, 100.0, 1),
            GwisMonthlyRecord("IDN.12_1", "Kalimantan Barat", 2016, 8, 70.0, 1),
            GwisMonthlyRecord("IDN.12_1", "Kalimantan Barat", 2017, 8, 50.0, 1),
        ]
        sipongi = [
            SipongiRecord("11", "Kalimantan Barat", "A", "B", "C", date(2015, 8, 2), "10:00 WIB", "NASA-MODIS", "High", 0.0, 110.0, "a", "a"),
            SipongiRecord("11", "Kalimantan Barat", "A", "B", "C", date(2016, 8, 2), "10:00 WIB", "NASA-MODIS", "High", 0.0, 110.0, "b", "b"),
            SipongiRecord("11", "Kalimantan Barat", "A", "B", "C", date(2017, 8, 2), "10:00 WIB", "S-NPP", "High", 0.0, 110.0, "c", "c"),
        ]
        protocol = {
            "phase_1_ready": False,
            "phase_1_gates": [{"asset_id": "viirs", "gate_ready": False}],
        }
        report = build_preliminary_synthesis_markdown(
            roni_records=roni,
            gwis_rows=gwis,
            sipongi_records=sipongi,
            protocol_report=protocol,
        )
        self.assertIn("NI -- Not identifiable", report)
        self.assertIn("not evidence that accessibility caused fire", report)
        self.assertIn("viirs", report)


if __name__ == "__main__":
    unittest.main()
