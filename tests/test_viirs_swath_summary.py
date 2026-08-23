from __future__ import annotations

import numpy as np
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from wildfire_research.viirs_opportunity import summarize_arrays


def _arrays():
    return (
        np.array([[0, 5], [7, 9]], dtype=np.uint8),
        np.array([[0.0, 1.0], [np.nan, 10.0]], dtype=np.float32),
        np.array([[110.0, 121.0], [110.0, 110.0]], dtype=np.float32),
        np.zeros((2, 2), dtype=np.uint8),
        np.ones((2, 2), dtype=np.uint8),
    )


def test_summary_counts_screening_classes_and_bbox():
    result = summarize_arrays(*_arrays(), bbox=(109, -5, 120, 8))
    assert result["pixel_count"] == 4
    assert result["fire_mask_class_counts"] == {"0": 1, "5": 1, "7": 1, "9": 1}
    assert result["prespecified_processed_or_fire_class_count"] == 3
    assert result["bbox_geolocation_pixels"] == 1
    assert result["opportunity_status"] == "screened_not_denominator_ready"


def test_summary_rejects_shape_mismatch():
    fire, lat, lon, quality, land = _arrays()
    with pytest.raises(ValueError, match="incompatible shapes"):
        summarize_arrays(fire, lat, lon, quality[:1], land)


def test_summary_rejects_invalid_bbox():
    with pytest.raises(ValueError, match="strictly increasing"):
        summarize_arrays(*_arrays(), bbox=(120, -5, 109, 8))
