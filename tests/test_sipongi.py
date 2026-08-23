from datetime import date
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wildfire_research.enso import RoniRecord
from wildfire_research.sipongi import (
    SipongiRecord,
    build_sipongi_context_markdown,
    parse_sipongi_payload,
)


class SipongiTests(unittest.TestCase):
    def test_parses_portal_rows_and_preserves_display_time(self):
        payload = (
            "Provinsi, Kab Kota, Kecamatan, Desa, Tanggal,Waktu, Satelit, Confidence, Latitude, Longitude \n"
            "Kalimantan Barat,KETAPANG,JELAI HULU,KESUMA JAYA,30-09-2015,17:55 WIB,NASA-MODIS,High,-1.951,110.826\n"
        ).encode("utf-8")
        records = parse_sipongi_payload(
            payload,
            province_id="11",
            start_date=date(2015, 9, 1),
            end_date=date(2015, 9, 30),
            source_file="data/raw/sipongi/2015/sample.txt",
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].reported_date, date(2015, 9, 30))
        self.assertEqual(records[0].reported_time, "17:55 WIB")
        self.assertEqual(records[0].satellite, "NASA-MODIS")

    def test_rejects_records_outside_requested_period(self):
        payload = (
            "Provinsi, Kab Kota, Kecamatan, Desa, Tanggal,Waktu, Satelit, Confidence, Latitude, Longitude\n"
            "Kalimantan Barat,KETAPANG,JELAI HULU,KESUMA JAYA,01-10-2015,17:55 WIB,NASA-MODIS,High,-1.951,110.826\n"
        ).encode("utf-8")
        with self.assertRaises(ValueError):
            parse_sipongi_payload(
                payload,
                province_id="11",
                start_date=date(2015, 9, 1),
                end_date=date(2015, 9, 30),
                source_file="sample.txt",
            )

    def test_repairs_an_unquoted_comma_only_in_administrative_label(self):
        payload = (
            "Provinsi, Kab Kota, Kecamatan, Desa, Tanggal,Waktu, Satelit, Confidence, Latitude, Longitude\n"
            "Kalimantan Selatan,TABALONG,TANTA,PULAU KU,U,14-09-2015,17:55 WIB,NASA-MODIS,Medium,-2.298,115.379\n"
        ).encode("utf-8")
        records = parse_sipongi_payload(
            payload,
            province_id="12",
            start_date=date(2015, 9, 1),
            end_date=date(2015, 9, 30),
            source_file="sample.txt",
        )
        self.assertEqual(records[0].village, "PULAU KU,U")
        self.assertEqual(records[0].reported_date, date(2015, 9, 14))
        self.assertTrue(records[0].source_schema_repaired)

    def test_allows_provider_empty_json_response_without_fabricating_a_row(self):
        records = parse_sipongi_payload(
            b'{"data":[]}',
            province_id="11",
            start_date=date(2015, 9, 1),
            end_date=date(2015, 9, 30),
            source_file="sample.txt",
        )
        self.assertEqual(records, [])

    def test_report_is_explicitly_nonprimary_and_sensor_stratified(self):
        records = [
            SipongiRecord("11", "Kalimantan Barat", "A", "B", "C", date(2015, 8, 2), "10:00 WIB", "NASA-MODIS", "High", 0.0, 110.0, "a", "a"),
            SipongiRecord("11", "Kalimantan Barat", "A", "B", "C", date(2016, 8, 2), "10:00 WIB", "NASA-MODIS", "High", 0.0, 110.0, "b", "b"),
            SipongiRecord("11", "Kalimantan Barat", "A", "B", "C", date(2017, 8, 2), "10:00 WIB", "S-NPP", "High", 0.0, 110.0, "c", "c"),
        ]
        roni = [
            RoniRecord("JJA", 2015, date(2015, 8, 31), 1.0),
            RoniRecord("JJA", 2016, date(2016, 8, 31), -1.0),
            RoniRecord("JJA", 2017, date(2017, 8, 31), 0.0),
        ]
        report = build_sipongi_context_markdown(records, roni)
        self.assertIn("not the primary 1 km", report)
        self.assertIn("NASA-MODIS", report)
        self.assertIn("portal-reported dates", report)
        self.assertIn("cannot test the human-accessibility", report)


if __name__ == "__main__":
    unittest.main()
