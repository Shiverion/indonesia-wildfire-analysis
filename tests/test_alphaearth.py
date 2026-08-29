from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from wildfire_research.alphaearth import (
    ALPHAEARTH_BANDS,
    build_cell_year_index,
    normalize_embedding_rows,
)


def test_build_cell_year_index_deduplicates_and_lags() -> None:
    opportunities = pd.DataFrame(
        {
            "cell_id": ["a", "a", "a", "b"],
            "acquisition_utc": [
                "2018-01-02T00:00:00Z",
                "2018-02-02T00:00:00Z",
                "2019-01-02T00:00:00Z",
                "2020-01-02T00:00:00Z",
            ],
        }
    )
    cells = pd.DataFrame(
        {"cell_id": ["a", "b"], "grid_row": [1, 2], "grid_col": [3, 4]}
    )
    result = build_cell_year_index(opportunities, cells, [2018, 2019])
    assert result["record_id"].tolist() == ["a:2018", "a:2019"]
    assert result["embedding_year"].tolist() == [2017, 2018]


def test_build_cell_year_index_rejects_unmapped_cells() -> None:
    opportunities = pd.DataFrame(
        {"cell_id": ["missing"], "acquisition_utc": ["2018-01-02T00:00:00Z"]}
    )
    cells = pd.DataFrame({"cell_id": ["a"], "grid_row": [1], "grid_col": [3]})
    with pytest.raises(ValueError, match="lack private grid indices"):
        build_cell_year_index(opportunities, cells, [2018])


def embedding_frame(event_year: int = 2018, embedding_year: int = 2017) -> pd.DataFrame:
    values = {band: [1.0] for band in ALPHAEARTH_BANDS}
    return pd.DataFrame(
        {
            "record_id": ["a:2018"],
            "cell_id": ["a"],
            "event_year": [event_year],
            "embedding_year": [embedding_year],
            **values,
        }
    )


def test_normalize_embedding_rows_produces_unit_norm() -> None:
    result = normalize_embedding_rows(embedding_frame())
    norm = np.linalg.norm(result[list(ALPHAEARTH_BANDS)].to_numpy(float), axis=1)
    assert norm[0] == pytest.approx(1.0)


def test_normalize_embedding_rows_rejects_temporal_leakage() -> None:
    with pytest.raises(ValueError, match="temporal leakage"):
        normalize_embedding_rows(embedding_frame(2018, 2018))
