"""Unit tests for dataset profiling and structural quality assessment."""

import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from analytics.profiling import load_dataset, profile_dataframe, profile_dataset
from schemas.dataset import DatasetProfile


@pytest.fixture
def sample_test_df() -> pd.DataFrame:
    """Create a synthetic test DataFrame with known metrics and defects."""
    return pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "category": ["A", "B", "A", "B", "C"],
        "sales": [100.0, 200.0, 150.0, np.nan, 500.0],
        "date": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
    })


def test_profile_dataframe(sample_test_df):
    """Verify statistical and type profiling on an in-memory DataFrame."""
    profile = profile_dataframe(sample_test_df, filename="test.csv")

    assert isinstance(profile, DatasetProfile)
    assert profile.row_count == 5
    assert profile.column_count == 4
    assert "sales" in profile.numeric_columns
    assert "category" in profile.categorical_columns
    assert "date" in profile.datetime_columns
    assert profile.columns["sales"].missing_count == 1
    assert profile.columns["sales"].missing_percentage == 20.0
    assert profile.columns["sales"].min_value == 100.0
    assert profile.columns["sales"].max_value == 500.0
    assert profile.columns["id"].is_primary_key_candidate is True
    assert profile.health_score > 0.0


def test_load_dataset_csv(sample_test_df):
    """Verify loading from CSV file."""
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        sample_test_df.to_csv(f.name, index=False)
        temp_csv = f.name

    try:
        loaded = load_dataset(temp_csv)
        assert len(loaded) == 5
        assert list(loaded.columns) == ["id", "category", "sales", "date"]
    finally:
        Path(temp_csv).unlink(missing_ok=True)


def test_load_dataset_excel(sample_test_df):
    """Verify loading from Excel file."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        temp_excel = f.name

    try:
        sample_test_df.to_excel(temp_excel, index=False)
        loaded = load_dataset(temp_excel)
        assert len(loaded) == 5
    finally:
        Path(temp_excel).unlink(missing_ok=True)
