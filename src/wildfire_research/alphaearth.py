"""Pure helpers for leakage-safe AlphaEarth cell-year features."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd


ALPHAEARTH_BANDS = tuple(f"A{index:02d}" for index in range(64))


def build_cell_year_index(
    opportunities: pd.DataFrame,
    private_cells: pd.DataFrame,
    eligible_event_years: Iterable[int],
) -> pd.DataFrame:
    """Create the unique registered cell-year requests without coordinates in IDs."""

    required_opportunity = {"cell_id", "acquisition_utc"}
    required_cells = {"cell_id", "grid_row", "grid_col"}
    missing_opportunity = sorted(required_opportunity - set(opportunities.columns))
    missing_cells = sorted(required_cells - set(private_cells.columns))
    if missing_opportunity:
        raise ValueError(f"opportunity frame missing columns: {missing_opportunity}")
    if missing_cells:
        raise ValueError(f"private cell table missing columns: {missing_cells}")
    if private_cells["cell_id"].astype(str).duplicated().any():
        raise ValueError("private cell table contains duplicate cell_id values")

    years = {int(year) for year in eligible_event_years}
    if not years:
        raise ValueError("eligible_event_years must not be empty")
    frame = opportunities[["cell_id", "acquisition_utc"]].copy()
    frame["cell_id"] = frame["cell_id"].astype(str)
    timestamps = pd.to_datetime(frame["acquisition_utc"], utc=True, errors="coerce")
    if timestamps.isna().any():
        raise ValueError("opportunity frame contains invalid acquisition_utc values")
    frame["event_year"] = timestamps.dt.year.astype(int)
    frame = frame.loc[frame["event_year"].isin(years), ["cell_id", "event_year"]]
    frame = frame.drop_duplicates().reset_index(drop=True)
    if frame.empty:
        raise ValueError("no opportunity rows fall within the registered event years")

    cells = private_cells[["cell_id", "grid_row", "grid_col"]].copy()
    cells["cell_id"] = cells["cell_id"].astype(str)
    result = frame.merge(cells, on="cell_id", how="left", validate="many_to_one")
    if result[["grid_row", "grid_col"]].isna().any().any():
        missing_count = int(result["grid_row"].isna().sum())
        raise ValueError(f"{missing_count} requested cell(s) lack private grid indices")

    result["event_year"] = result["event_year"].astype(int)
    result["embedding_year"] = result["event_year"] - 1
    result["grid_row"] = result["grid_row"].astype(int)
    result["grid_col"] = result["grid_col"].astype(int)
    result["record_id"] = (
        result["cell_id"] + ":" + result["event_year"].astype(str)
    )
    if result["record_id"].duplicated().any():
        raise ValueError("cell-year request contains duplicate record_id values")
    return result[
        ["record_id", "cell_id", "event_year", "embedding_year", "grid_row", "grid_col"]
    ].sort_values(["embedding_year", "cell_id"], ignore_index=True)


def normalize_embedding_rows(
    frame: pd.DataFrame,
    bands: Iterable[str] = ALPHAEARTH_BANDS,
) -> pd.DataFrame:
    """Validate and L2-normalize polygon-mean embedding vectors."""

    band_names = list(bands)
    missing = sorted(set(band_names) - set(frame.columns))
    if missing:
        raise ValueError(f"embedding result missing bands: {missing}")
    if not {"record_id", "cell_id", "event_year", "embedding_year"}.issubset(frame):
        raise ValueError("embedding result is missing identifier/year columns")
    if frame["record_id"].astype(str).duplicated().any():
        raise ValueError("embedding result contains duplicate record_id values")

    values = frame[band_names].apply(pd.to_numeric, errors="coerce").to_numpy(float)
    if not np.isfinite(values).all():
        raise ValueError("embedding result contains missing or non-finite values")
    norms = np.linalg.norm(values, axis=1)
    if not np.isfinite(norms).all() or np.any(norms <= 0):
        raise ValueError("embedding result contains zero or invalid vector norms")

    event_year = pd.to_numeric(frame["event_year"], errors="raise").to_numpy(int)
    embedding_year = pd.to_numeric(
        frame["embedding_year"], errors="raise"
    ).to_numpy(int)
    if not np.array_equal(embedding_year, event_year - 1):
        raise ValueError("temporal leakage: embedding_year must equal event_year - 1")

    result = frame.copy()
    result.loc[:, band_names] = values / norms[:, None]
    return result
