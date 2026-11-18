"""Anomaly and outlier detection using statistical thresholds and Isolation Forest."""

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


def detect_anomalies_iqr(
    df: pd.DataFrame, 
    col: str, 
    multiplier: float = 1.5
) -> Dict[str, Any]:
    """Identify outliers using the Interquartile Range (IQR) technique."""
    if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
        return {"error": f"Column '{col}' is not numeric or not found"}

    series = df[col].dropna()
    if len(series) < 4:
        return {"error": "Insufficient data"}

    q25 = float(series.quantile(0.25))
    q75 = float(series.quantile(0.75))
    iqr = q75 - q25

    if iqr == 0:
        return {"column": col, "outliers_count": 0, "outliers": []}

    lower_bound = float(q25 - multiplier * iqr)
    upper_bound = float(q75 + multiplier * iqr)

    mask = (series < lower_bound) | (series > upper_bound)
    outlier_df = df.loc[series[mask].index]

    return {
        "column": col,
        "method": "IQR",
        "lower_bound": round(lower_bound, 4),
        "upper_bound": round(upper_bound, 4),
        "outliers_count": int(mask.sum()),
        "outliers_percentage": round((mask.sum() / len(series)) * 100.0, 2),
        "top_outliers": outlier_df.head(10).to_dict(orient="records")
    }


def detect_multivariate_anomalies(
    df: pd.DataFrame, 
    features: List[str], 
    contamination: float = 0.02
) -> Dict[str, Any]:
    """Detect unusual multi-dimensional combinations using Isolation Forest."""
    valid_features = [f for f in features if f in df.columns and pd.api.types.is_numeric_dtype(df[f])]
    if len(valid_features) < 2:
        return {"error": "Multivariate anomaly detection requires at least 2 numeric features"}

    sub = df[valid_features].dropna()
    if len(sub) < 20:
        return {"error": "Need at least 20 records for reliable Isolation Forest"}

    clf = IsolationForest(contamination=contamination, random_state=42)
    labels = clf.fit_predict(sub)
    anomaly_indices = sub.index[labels == -1]

    anomaly_rows = df.loc[anomaly_indices]

    return {
        "features_evaluated": valid_features,
        "method": "IsolationForest",
        "anomalies_detected": int(len(anomaly_indices)),
        "anomaly_percentage": round((len(anomaly_indices) / len(sub)) * 100.0, 2),
        "sample_anomalies": anomaly_rows.head(10).to_dict(orient="records")
    }
