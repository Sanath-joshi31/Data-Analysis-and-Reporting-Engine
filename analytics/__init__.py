"""Analytics library for Autonomous Data Analyst AI."""

from analytics.profiling import load_dataset, profile_dataset, profile_dataframe, profile_column
from analytics.cleaning import generate_cleaning_proposals, apply_cleaning_actions
from analytics.descriptive import compute_descriptive_stats, compute_correlation_matrix, compute_frequency_distribution
from analytics.diagnostic import compare_segments, compute_growth_and_variance
from analytics.predictive import forecast_linear_trend, perform_segmentation
from analytics.anomaly import detect_anomalies_iqr, detect_multivariate_anomalies

__all__ = [
    "load_dataset",
    "profile_dataset",
    "profile_dataframe",
    "profile_column",
    "generate_cleaning_proposals",
    "apply_cleaning_actions",
    "compute_descriptive_stats",
    "compute_correlation_matrix",
    "compute_frequency_distribution",
    "compare_segments",
    "compute_growth_and_variance",
    "forecast_linear_trend",
    "perform_segmentation",
    "detect_anomalies_iqr",
    "detect_multivariate_anomalies",
]
