from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wildfire_research.temporal_qa import check_chirps, check_era5, check_mod13, check_viirs


def _root(tmp_path: Path) -> Path:
    (tmp_path / "data/raw/era5_land/2015").mkdir(parents=True)
    (tmp_path / "data/raw/chirps/2015").mkdir(parents=True)
    (tmp_path / "data/raw/mod13q1/MOD13Q1").mkdir(parents=True)
    (tmp_path / "data/derived/viirs").mkdir(parents=True)
    (tmp_path / "outputs/quality").mkdir(parents=True)
    return tmp_path


def test_era5_reports_complete_year_but_not_full_study_window(tmp_path: Path) -> None:
    root = _root(tmp_path)
    for month in range(1, 13):
        (root / f"data/raw/era5_land/2015/era5_land_2015_{month:02d}.nc").write_bytes(b"x")
    result = check_era5(root, [2015, 2016])
    assert result["status"] == "calibration_year_complete_only"
    assert result["complete_years"] == [2015]
    assert result["missing_months_by_study_year"]["2016"] == list(range(1, 13))
    assert result["temporal_event_lag_validated"] is False


def test_chirps_detects_missing_and_extra_dates(tmp_path: Path) -> None:
    root = _root(tmp_path)
    for name in ("2015.07.01", "2015.07.03", "2015.12.31"):
        (root / f"data/raw/chirps/2015/chirps-v3.0.rnl.{name}.cog").write_bytes(b"x")
    (root / "data/raw/chirps/download_manifest.json").write_text(json.dumps({"temporal": ["2015-07-01", "2015-07-03"]}), encoding="utf-8")
    result = check_chirps(root, [2015])
    assert result["missing_dates"] == ["2015-07-02"]
    assert result["extra_dates"] == ["2015-12-31"]
    assert result["lag_features_validated"] is False


def test_mod13_inventory_does_not_claim_qa(tmp_path: Path) -> None:
    root = _root(tmp_path)
    (root / "data/raw/mod13q1/MOD13Q1/MOD13Q1.A2015001.h30v08.061.test.hdf").write_bytes(b"x")
    result = check_mod13(root, [2015])
    assert result["composite_count"] == 1
    assert result["qa_mask_validated"] is False
    assert result["prefire_support_validated"] is False


def test_viirs_screening_never_unlocks_denominator(tmp_path: Path) -> None:
    root = _root(tmp_path)
    (root / "data/derived/viirs/viirs_pair_index.csv").write_text(
        "pair_key,acquisition_utc,pair_status\n2015001.0548,2015-01-01T05:48:00Z,paired\n", encoding="utf-8",
    )
    (root / "data/derived/viirs/viirs_swath_summary.csv").write_text("pair_key\n2015001.0548\n", encoding="utf-8")
    result = check_viirs(root, [2015])
    assert result["paired_swath_count"] == 1
    assert result["negative_frame_ready"] is False
    assert result["denominator_ready"] is False
