"""Diagnostic analytics library for segment comparisons, variance breakdown, and hypothesis checks."""

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from scipy import stats


def compare_segments(
    df: pd.DataFrame, 
    group_col: str, 
    metric_col: str, 
    top_n: int = 15
) -> Dict[str, Any]:
    """Compare a numeric metric across categories of a grouping variable with statistical tests."""
    if group_col not in df.columns or metric_col not in df.columns:
        return {"error": f"Columns {group_col} or {metric_col} not found"}

    sub = df[[group_col, metric_col]].dropna()
    if sub.empty:
        return {"error": "No non-null data for comparison"}

    grouped = sub.groupby(group_col)[metric_col].agg(
        count="count",
        sum="sum",
        mean="mean",
        median="median",
        std="std",
        min="min",
        max="max"
    ).reset_index()

    total_sum = grouped["sum"].sum()
    if total_sum != 0:
        grouped["share_of_total_pct"] = (grouped["sum"] / total_sum * 100.0).round(2)
    else:
        grouped["share_of_total_pct"] = 0.0

    grouped = grouped.sort_values(by="sum", ascending=False).head(top_n)

    # Perform One-Way ANOVA if at least 2 groups have >= 3 records
    groups_list = [grp[metric_col].values for _, grp in sub.groupby(group_col) if len(grp) >= 3]
    anova_p_value = None
    significant_difference = False

    if len(groups_list) >= 2:
        try:
            f_stat, p_val = stats.f_oneway(*groups_list)
            anova_p_value = float(round(p_val, 6))
            significant_difference = bool(p_val < 0.05)
        except Exception:
            pass

    records = grouped.round(4).to_dict(orient="records")

    return {
        "group_column": group_col,
        "metric_column": metric_col,
        "segments": records,
        "total_sum": float(round(total_sum, 4)),
        "anova_p_value": anova_p_value,
        "is_statistically_significant": significant_difference
    }


def compute_growth_and_variance(
    df: pd.DataFrame, 
    date_col: str, 
    metric_col: str, 
    freq: str = "ME"
) -> Dict[str, Any]:
    """Calculate period-over-period trend, absolute delta, and percentage growth."""
    if date_col not in df.columns or metric_col not in df.columns:
        return {"error": f"Columns {date_col} or {metric_col} missing"}

    sub = df[[date_col, metric_col]].dropna().copy()
    sub[date_col] = pd.to_datetime(sub[date_col], errors="coerce")
    sub = sub.dropna(subset=[date_col])

    if sub.empty:
        return {"error": "No valid datetime entries"}

    # Resample
    ts = sub.set_index(date_col).resample(freq)[metric_col].sum().reset_index()
    ts["period"] = ts[date_col].dt.strftime("%Y-%m")
    ts["previous_value"] = ts[metric_col].shift(1)
    ts["absolute_change"] = ts[metric_col] - ts["previous_value"]
    ts["growth_rate_pct"] = ((ts["absolute_change"] / ts["previous_value"].replace(0, np.nan)) * 100.0).round(2)

    return {
        "periods": ts[["period", metric_col, "absolute_change", "growth_rate_pct"]].fillna(0).to_dict(orient="records"),
        "total": float(ts[metric_col].sum()),
        "average_growth_rate": float(round(ts["growth_rate_pct"].mean(), 2))
    }
