from datetime import date, datetime, timezone
from pathlib import Path
import json
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wildfire_research.enso import RoniRecord
from wildfire_research.explorer import build_explorer_bundle, render_explorer_html
from wildfire_research.gwis import GwisMonthlyRecord
from wildfire_research.sipongi import SipongiRecord


class ExplorerTests(unittest.TestCase):
    def _bundle(self, year: int = 2015):
        roni = [
            RoniRecord("JJA", year, date(year, 8, 31), 0.4),
            RoniRecord("JAS", year, date(year, 9, 30), 0.6),
            RoniRecord("ASO", year, date(year, 10, 31), 0.8),
            RoniRecord("SON", year, date(year, 11, 30), 1.0),
        ]
        gwis = [
            GwisMonthlyRecord("IDN.12_1", "Kalimantan Barat", year, 7, 100.0, 2),
        ]
        sipongi = [
            SipongiRecord("11", "Kalimantan Barat", "local", "local", "local", date(year, 7, 2), "10:00 WIB", "NASA-MODIS", "High", 0.1, 110.0, "raw.txt", "abc"),
            SipongiRecord("11", "Kalimantan Barat", "local", "local", "local", date(year, 7, 3), "10:00 WIB", "S-NPP", "Medium", 0.2, 110.1, "raw.txt", "abc", True),
        ]
        return build_explorer_bundle(
            roni_records=roni,
            gwis_rows=gwis,
            sipongi_records=sipongi,
            protocol_report={"phase_1_ready": False, "phase_1_gates": [{"asset_id": "viirs", "gate_ready": False}]},
            provenance=[],
            ledger_state={"valid": True},
            generated_at=datetime(2026, 8, 21, tzinfo=timezone.utc),
        )

    def test_bundle_is_aggregate_only_and_conserves_portal_counts(self):
        bundle = self._bundle()
        serialized = json.dumps(bundle).casefold()
        for prohibited in ("\"latitude\"", "\"longitude\"", "\"district\"", "\"village\"", "\"reported_time\"", "\"source_file\""):
            self.assertNotIn(prohibited, serialized)
        self.assertEqual(bundle["quality"]["sipongi"]["record_count"], 2)
        self.assertEqual(bundle["quality"]["sipongi"]["excluded_years"], [2024])
        self.assertEqual(sum(row["record_count"] for row in bundle["sipongi_annual"]), 2)
        self.assertEqual(sum(row["record_count"] for row in bundle["sipongi_monthly"]), 2)
        self.assertEqual(bundle["roni_annual"][0]["mean_aug_nov_c"], 0.7)
        self.assertFalse(bundle["quality"]["sipongi"]["raw_records_embedded"])
        self.assertEqual(bundle["display_status"]["primary_association"], "NI - Not identifiable")

    def test_rejects_quarantined_sipongi_year(self):
        with self.assertRaisesRegex(ValueError, "2024"):
            self._bundle(year=2024)

    def test_allows_validated_2025_archive_year(self):
        bundle = self._bundle(year=2025)
        self.assertEqual(bundle["scope"]["sipongi_years"], [2025, 2025])

    def test_partial_snapshot_is_aggregate_only_and_not_an_archive_year(self):
        snapshot_records = [
            SipongiRecord(identifier, province, "local", "local", "local", date(2026, 8, 20), "10:00 WIB", "NASA-MODIS", "High", 0.0, 110.0, "snapshot.txt", "abc")
            for identifier, province in (
                ("11", "Kalimantan Barat"),
                ("12", "Kalimantan Selatan"),
                ("13", "Kalimantan Tengah"),
                ("14", "Kalimantan Timur"),
                ("15", "Kalimantan Utara"),
            )
        ]
        metadata = {
            "snapshot_id": "snapshot-2026-08-20",
            "status": "validated_partial",
            "season": {"year": 2026, "start_date": "2026-07-01", "end_date": "2026-11-30", "complete": False},
            "through_date": "2026-08-20",
            "retrieved_at_utc": "2026-08-21T00:00:00+00:00",
            "record_count": 5,
            "files": [{"province_id": identifier, "rejected_response_count": 0} for identifier in ("11", "12", "13", "14", "15")],
            "comparison_guardrail": {
                "included_in_annual_archive": False,
                "eligible_for_year_slider": False,
                "eligible_for_annual_chart": False,
                "comparable_to_completed_jul_nov_seasons": False,
            },
            "validation": {
                "expected_province_responses": 5,
                "validated_province_responses": 5,
                "raw_inventory_sha256": "raw",
                "provider_configuration_sha256": "config",
                "province_catalogue_sha256": "provinces",
            },
        }
        bundle = build_explorer_bundle(
            roni_records=[RoniRecord("MJJ", 2026, date(2026, 7, 31), 0.98)],
            gwis_rows=[GwisMonthlyRecord("IDN.12_1", "Kalimantan Barat", 2024, 7, 100.0, 2)],
            sipongi_records=[SipongiRecord("11", "Kalimantan Barat", "local", "local", "local", date(2025, 7, 2), "10:00 WIB", "NASA-MODIS", "High", 0.1, 110.0, "raw.txt", "abc")],
            protocol_report={"phase_1_ready": False, "phase_1_gates": [{"asset_id": "viirs", "gate_ready": False}]},
            provenance=[],
            ledger_state={"valid": True},
            sipongi_snapshot_records=snapshot_records,
            sipongi_snapshot_metadata=metadata,
            generated_at=datetime(2026, 8, 21, tzinfo=timezone.utc),
        )
        snapshot = bundle["sipongi_current_snapshot"]
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot["total_record_count"], 5)
        self.assertEqual(len(snapshot["province_platform_counts"]), 20)
        self.assertNotIn(2026, [row["year"] for row in bundle["sipongi_annual"]])
        self.assertFalse(snapshot["comparison_guardrail"]["eligible_for_year_slider"])

    def test_html_keeps_descriptive_boundary_visible(self):
        html = render_explorer_html(self._bundle())
        self.assertIn("Primary association: NI", html)
        self.assertIn("not a causal or operational fire map", html)
        self.assertIn('id="interactive-globe"', html)
        self.assertIn("pointerdown", html)
        self.assertIn("Generalized aggregate anchors", html)
        self.assertIn("Use arrow keys to rotate", html)
        self.assertNotIn('id="province-map"', html)
        self.assertIn('type="application/json"', html)
        self.assertNotIn('src="https://', html)


if __name__ == "__main__":
    unittest.main()
