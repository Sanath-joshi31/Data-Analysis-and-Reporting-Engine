"""Interactive dataset filtering engine for the Autonomous Dashboard Builder."""

from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from schemas.dataset import DatasetProfile
from dashboard.specification import DashboardFilterState


def extract_filter_candidates(df: pd.DataFrame, profile: DatasetProfile) -> Dict[str, List[str]]:
    """Identify dimensions suitable for interactive dashboard dropdowns and multi-select filters."""
    filter_candidates: Dict[str, List[str]] = {}

    for col in profile.categorical_columns:
        if col in df.columns:
            non_null = df[col].dropna()
            unique_cnt = non_null.nunique()
            # Dimensions with 2 to 40 unique values make great filters
            if 2 <= unique_cnt <= 40:
                filter_candidates[col] = sorted([str(x) for x in non_null.unique().tolist()])

    return filter_candidates


def apply_dashboard_filters(df: pd.DataFrame, filter_state: DashboardFilterState) -> pd.DataFrame:
    """Filter the source DataFrame based on active date range and category criteria."""
    filtered_df = df.copy()

    # 1. Date Range Filter
    if filter_state.date_column and filter_state.date_range:
        date_col = filter_state.date_column
        if date_col in filtered_df.columns:
            start_date, end_date = filter_state.date_range
            try:
                # Convert column to datetime for filtering
                d_series = pd.to_datetime(filtered_df[date_col], errors="coerce")
                mask = pd.Series(True, index=filtered_df.index)
                if start_date:
                    mask &= (d_series >= pd.to_datetime(start_date))
                if end_date:
                    mask &= (d_series <= pd.to_datetime(end_date))
                filtered_df = filtered_df[mask]
            except Exception:
                pass

    # 2. Categorical Multi-Select Filters
    for col_name, selected_values in filter_state.selected_categories.items():
        if col_name in filtered_df.columns and selected_values:
            filtered_df = filtered_df[filtered_df[col_name].astype(str).isin(selected_values)]

    return filtered_df
