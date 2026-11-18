"""Autonomous Dashboard Generator: calculates metrics, builds figures, and validates quality."""

import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from analytics.anomaly import detect_anomalies_iqr
from analytics.predictive import forecast_linear_trend
from dashboard.chart_registry import (
    build_anomaly_chart,
    build_area_chart,
    build_bar_chart,
    build_box_plot,
    build_correlation_heatmap,
    build_donut_chart,
    build_forecast_chart,
    build_histogram,
    build_line_chart,
    build_pareto_chart,
    build_scatter_plot,
    build_treemap,
)
from dashboard.explanations import ChartExplanationEngine
from dashboard.filters import extract_filter_candidates
from dashboard.specification import ChartSpecification, DashboardSpecification
from dashboard.validator import DashboardValidator
from schemas.dataset import DatasetProfile

logger = logging.getLogger(__name__)


class DashboardGenerator:
    """Executes Pandas computations, renders Plotly figures, and assembles the complete dashboard."""

    def __init__(self):
        self.explanation_engine = ChartExplanationEngine()

    def generate_dashboard(
        self,
        df: pd.DataFrame,
        spec: DashboardSpecification,
        profile: DatasetProfile
    ) -> DashboardSpecification:
        """Process and populate all charts, figures, table records, and explanations."""
        logger.info(f"DashboardGenerator building visualizations for: {spec.title}")
        theme = spec.theme

        # Extract available filters for UI
        spec.available_filters = extract_filter_candidates(df, profile)

        # Iterate over all sections and charts
        for section in spec.sections:
            for chart in section.charts:
                try:
                    fig, records = self._build_chart_content(df, chart, theme)
                    chart.figure_dict = fig.to_dict() if fig else {}
                    chart.table_records = records

                    # Generate AI explanation
                    exp, ins = self.explanation_engine.explain_chart(
                        title=chart.title,
                        chart_type=chart.chart_type,
                        x_col=chart.x_col,
                        y_col=chart.y_col,
                        data_records=records
                    )
                    chart.explanation = exp
                    chart.insights = ins

                except Exception as err:
                    logger.error(f"Error generating chart '{chart.id}' ({chart.title}): {err}")
                    chart.explanation = f"Could not compute visualization: {str(err)}"

        # Validate dashboard quality
        is_valid, issues = DashboardValidator.validate_dashboard(spec)
        logger.info(f"Dashboard generated. Valid: {is_valid}")

        return spec

    def _build_chart_content(
        self,
        df: pd.DataFrame,
        chart: ChartSpecification,
        theme: str
    ) -> tuple[Any, List[Dict[str, Any]]]:
        """Compute values and build the corresponding Plotly figure for a chart specification."""
        c_type = chart.chart_type
        x_col = chart.x_col
        y_col = chart.y_col
        color_col = chart.color_col
        records = []

        # 1. Line Chart (Time Series Trend)
        if c_type == "line":
            sub = df.dropna(subset=[x_col, y_col]).copy()
            sub[x_col] = pd.to_datetime(sub[x_col], errors="coerce")
            sub = sub.dropna(subset=[x_col])
            # Resample monthly
            ts = sub.set_index(x_col).resample("ME")[y_col].sum().reset_index()
            ts["Period"] = ts[x_col].dt.strftime("%Y-%m")
            records = ts[["Period", y_col]].to_dict(orient="records")
            fig = build_line_chart(ts, x_col="Period", y_col=y_col, title=chart.title, theme=theme, show_moving_avg=True)
            return fig, records

        # 2. Area Chart
        elif c_type == "area":
            sub = df.dropna(subset=[x_col, y_col]).copy()
            sub[x_col] = pd.to_datetime(sub[x_col], errors="coerce")
            sub = sub.dropna(subset=[x_col])
            ts = sub.set_index(x_col).resample("ME")[y_col].sum().reset_index()
            ts["Period"] = ts[x_col].dt.strftime("%Y-%m")
            records = ts[["Period", y_col]].to_dict(orient="records")
            fig = build_area_chart(ts, x_col="Period", y_col=y_col, title=chart.title, theme=theme)
            return fig, records

        # 3. Bar Chart
        elif c_type == "bar":
            if y_col and y_col in df.columns:
                grouped = df.groupby(x_col)[y_col].sum().reset_index()
                grouped = grouped.sort_values(by=y_col, ascending=False).head(chart.top_n or 15)
                records = grouped.to_dict(orient="records")
                fig = build_bar_chart(grouped, x_col=x_col, y_col=y_col, color_col=color_col, title=chart.title, theme=theme)
            else:
                counts = df[x_col].value_counts().head(chart.top_n or 15).reset_index()
                counts.columns = [x_col, "Count"]
                records = counts.to_dict(orient="records")
                fig = build_bar_chart(counts, x_col=x_col, y_col="Count", title=chart.title, theme=theme)
            return fig, records

        # 4. Horizontal Bar Chart
        elif c_type == "horizontal_bar":
            grouped = df.groupby(x_col)[y_col].sum().reset_index()
            grouped = grouped.sort_values(by=y_col, ascending=False).head(chart.top_n or 10)
            records = grouped.to_dict(orient="records")
            fig = build_bar_chart(grouped, x_col=x_col, y_col=y_col, orientation="h", title=chart.title, theme=theme)
            return fig, records

        # 5. Pareto Chart
        elif c_type == "pareto":
            fig = build_pareto_chart(df, cat_col=x_col, val_col=y_col, title=chart.title, theme=theme)
            grouped = df.groupby(x_col)[y_col].sum().sort_values(ascending=False).head(10).reset_index()
            records = grouped.to_dict(orient="records")
            return fig, records

        # 6. Donut / Pie Chart
        elif c_type in ["donut", "pie"]:
            grouped = df.groupby(x_col)[y_col].sum().reset_index()
            grouped = grouped.sort_values(by=y_col, ascending=False).head(8)
            records = grouped.to_dict(orient="records")
            fig = build_donut_chart(df, names_col=x_col, values_col=y_col, title=chart.title, theme=theme)
            return fig, records

        # 7. Histogram
        elif c_type == "histogram":
            clean_series = df[x_col].dropna()
            records = clean_series.describe().reset_index().to_dict(orient="records")
            fig = build_histogram(df, x_col=x_col, title=chart.title, theme=theme)
            return fig, records

        # 8. Box Plot
        elif c_type == "box":
            grouped = df.groupby(x_col)[y_col].describe().reset_index()
            records = grouped.to_dict(orient="records")
            fig = build_box_plot(df, x_col=x_col, y_col=y_col, title=chart.title, theme=theme)
            return fig, records

        # 9. Scatter Plot
        elif c_type in ["scatter", "bubble"]:
            sub = df[[x_col, y_col]].dropna().head(300)
            records = sub.describe().reset_index().to_dict(orient="records")
            fig = build_scatter_plot(df, x_col=x_col, y_col=y_col, color_col=color_col, title=chart.title, theme=theme)
            return fig, records

        # 10. Correlation Heatmap
        elif c_type == "heatmap":
            num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            corr_df = df[num_cols[:6]].corr().round(2).reset_index()
            records = corr_df.to_dict(orient="records")
            fig = build_correlation_heatmap(df, numeric_cols=num_cols[:6], title=chart.title, theme=theme)
            return fig, records

        # 11. Forward Forecast
        elif c_type == "forecast":
            forecast_res = forecast_linear_trend(df, date_col=x_col, metric_col=y_col, horizon_periods=6)
            hist = forecast_res.get("historical", [])
            fc = forecast_res.get("forecast", [])
            records = hist + fc
            fig = build_forecast_chart(historical_data=hist, forecast_data=fc, title=chart.title, theme=theme)
            return fig, records

        # 12. Anomaly Detection
        elif c_type == "anomaly":
            outlier_info = detect_anomalies_iqr(df, col=x_col)
            top_outliers = outlier_info.get("top_outliers", [])
            outlier_indices = [df.index[df[x_col] == o[x_col]][0] for o in top_outliers if o[x_col] in df[x_col].values]
            records = top_outliers[:10]
            fig = build_anomaly_chart(df, x_col=x_col, y_col=y_col, outlier_indices=outlier_indices, title=chart.title, theme=theme)
            return fig, records

        else:
            fig = build_bar_chart(df.head(10), x_col=x_col or df.columns[0], y_col=y_col or df.columns[1], title=chart.title, theme=theme)
            return fig, records
