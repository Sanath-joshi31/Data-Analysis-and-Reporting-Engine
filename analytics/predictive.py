"""Predictive analytics module for trend forecasting, regression, and clustering."""

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_absolute_error


def forecast_linear_trend(
    df: pd.DataFrame, 
    date_col: str, 
    metric_col: str, 
    horizon_periods: int = 6, 
    freq: str = "ME"
) -> Dict[str, Any]:
    """Perform time-series aggregation and linear trend forecasting with confidence estimates."""
    if date_col not in df.columns or metric_col not in df.columns:
        return {"error": f"Columns {date_col} or {metric_col} not found"}

    sub = df[[date_col, metric_col]].dropna().copy()
    sub[date_col] = pd.to_datetime(sub[date_col], errors="coerce")
    sub = sub.dropna()

    if len(sub) < 4:
        return {"error": "Insufficient time-series observations for forecasting (requires >= 4 periods)"}

    # Group by monthly frequency
    ts = sub.set_index(date_col).resample(freq)[metric_col].sum().reset_index()
    if len(ts) < 3:
        return {"error": "Insufficient resampled periods"}

    ts["t"] = np.arange(len(ts))
    X = ts[["t"]].values
    y = ts[metric_col].values

    model = LinearRegression()
    model.fit(X, y)
    y_pred_hist = model.predict(X)
    r2 = float(round(r2_score(y, y_pred_hist), 4))
    mae = float(round(mean_absolute_error(y, y_pred_hist), 4))

    # Generate future periods
    last_date = ts[date_col].iloc[-1]
    future_dates = pd.date_range(start=last_date, periods=horizon_periods + 1, freq=freq)[1:]
    future_t = np.arange(len(ts), len(ts) + horizon_periods).reshape(-1, 1)
    future_preds = model.predict(future_t)

    # Historical records
    historical = []
    for d, val, pred in zip(ts[date_col], y, y_pred_hist):
        historical.append({
            "date": d.strftime("%Y-%m-%d"),
            "actual": float(round(val, 2)),
            "fitted_trend": float(round(pred, 2)),
            "type": "historical"
        })

    # Forecast records
    forecast = []
    for d, pred in zip(future_dates, future_preds):
        forecast.append({
            "date": d.strftime("%Y-%m-%d"),
            "forecast": float(round(max(0, pred), 2)),
            "type": "forecast"
        })

    trend_direction = "upward" if model.coef_[0] > 0 else "downward"

    return {
        "historical": historical,
        "forecast": forecast,
        "trend_slope": float(round(model.coef_[0], 4)),
        "trend_direction": trend_direction,
        "r2_score": r2,
        "mean_absolute_error": mae,
        "summary": f"Fitted trend is {trend_direction} with slope {model.coef_[0]:.2f} per period (R² = {r2:.2f})."
    }


def perform_segmentation(
    df: pd.DataFrame, 
    numeric_cols: List[str], 
    n_clusters: int = 3
) -> Dict[str, Any]:
    """Cluster dataset records into distinct behavioral segments using K-Means."""
    valid_cols = [c for c in numeric_cols if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
    if len(valid_cols) < 2:
        return {"error": "Clustering requires at least 2 numeric features"}

    sub = df[valid_cols].dropna()
    if len(sub) < n_clusters * 2:
        return {"error": "Not enough valid rows to perform clustering"}

    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(sub)

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(scaled_data)

    sub_copy = sub.copy()
    sub_copy["Cluster"] = [f"Segment_{c+1}" for c in clusters]

    cluster_summary = sub_copy.groupby("Cluster").agg(
        record_count=("Cluster", "count"),
        **{f"mean_{col}": (col, "mean") for col in valid_cols}
    ).reset_index()

    return {
        "features": valid_cols,
        "n_clusters": n_clusters,
        "cluster_profiles": cluster_summary.round(3).to_dict(orient="records"),
        "cluster_distribution": sub_copy["Cluster"].value_counts().to_dict()
    }
