"""Descriptive analytics library for univariate and bivariate summary calculations."""

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from scipy import stats


def compute_descriptive_stats(df: pd.DataFrame, columns: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
    """Compute comprehensive descriptive statistics for specified numeric columns."""
    if columns is None:
        target_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    else:
        target_cols = [c for c in columns if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]

    results: Dict[str, Dict[str, Any]] = {}

    for col in target_cols:
        series = df[col].dropna()
        if len(series) == 0:
            continue
        
        mode_val = None
        try:
            m = series.mode()
            if not m.empty:
                mode_val = float(m.iloc[0])
        except Exception:
            pass

        results[col] = {
            "count": int(len(series)),
            "mean": float(round(series.mean(), 4)),
            "std": float(round(series.std(), 4)) if len(series) > 1 else 0.0,
            "variance": float(round(series.var(), 4)) if len(series) > 1 else 0.0,
            "median": float(round(series.median(), 4)),
            "mode": mode_val,
            "min": float(series.min()),
            "q25": float(round(series.quantile(0.25), 4)),
            "q50": float(round(series.quantile(0.50), 4)),
            "q75": float(round(series.quantile(0.75), 4)),
            "max": float(series.max()),
            "skewness": float(round(series.skew(), 4)) if len(series) > 2 else 0.0,
            "kurtosis": float(round(series.kurt(), 4)) if len(series) > 3 else 0.0,
        }

    return results


def compute_correlation_matrix(df: pd.DataFrame, columns: Optional[List[str]] = None) -> Dict[str, Any]:
    """Compute Pearson and Spearman correlation matrices with p-values."""
    if columns is None:
        cols = df.select_dtypes(include=[np.number]).columns.tolist()
    else:
        cols = [c for c in columns if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]

    if len(cols) < 2:
        return {"columns": cols, "correlation_matrix": {}, "pairs": []}

    sub_df = df[cols].dropna()
    if len(sub_df) < 3:
        return {"columns": cols, "correlation_matrix": {}, "pairs": []}

    corr_df = sub_df.corr(method="pearson").round(4)
    corr_dict = corr_df.to_dict()

    pairs = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            col1, col2 = cols[i], cols[j]
            r = corr_df.loc[col1, col2]
            try:
                stat, p_val = stats.pearsonr(sub_df[col1], sub_df[col2])
            except Exception:
                p_val = 1.0

            pairs.append({
                "column_1": col1,
                "column_2": col2,
                "correlation": float(r),
                "p_value": float(round(p_val, 6)),
                "statistically_significant": bool(p_val < 0.05),
                "strength": (
                    "strong positive" if r >= 0.7 else
                    "moderate positive" if r >= 0.3 else
                    "weak positive" if r > 0.05 else
                    "strong negative" if r <= -0.7 else
                    "moderate negative" if r <= -0.3 else
                    "weak negative" if r < -0.05 else "negligible"
                )
            })

    pairs.sort(key=lambda x: abs(x["correlation"]), reverse=True)

    return {
        "columns": cols,
        "matrix": corr_dict,
        "ranked_pairs": pairs
    }


def compute_frequency_distribution(df: pd.DataFrame, column: str, top_n: int = 15) -> List[Dict[str, Any]]:
    """Compute value counts, percentages, and cumulative sums for a categorical column."""
    if column not in df.columns:
        return []

    series = df[column].dropna().astype(str)
    total = len(series)
    if total == 0:
        return []

    counts = series.value_counts().head(top_n)
    distribution = []
    running_pct = 0.0

    for val, count in counts.items():
        pct = round((count / total) * 100.0, 2)
        running_pct = round(running_pct + pct, 2)
        distribution.append({
            "category": str(val),
            "count": int(count),
            "percentage": pct,
            "cumulative_percentage": min(running_pct, 100.0)
        })

    return distribution
