"""Chart selection heuristics and automated visualization engine."""

from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from schemas.report import ChartArtifact


def select_best_chart_type(
    has_date: bool = False,
    is_distribution: bool = False,
    is_correlation: bool = False,
    num_categories: int = 5,
    metric_count: int = 1
) -> str:
    """Heuristic rule engine to select the most informative chart type."""
    if is_correlation:
        return "scatter" if metric_count == 2 else "heatmap"
    if has_date:
        return "line"
    if is_distribution:
        return "histogram"
    if num_categories <= 20:
        return "bar"
    return "box"


def build_chart_from_table(
    table_name: str,
    records: List[Dict[str, Any]],
    title: Optional[str] = None,
    preferred_type: Optional[str] = None
) -> Optional[ChartArtifact]:
    """Dynamically generate a Plotly ChartArtifact from tabular output records."""
    if not records:
        return None

    df = pd.DataFrame(records)
    if df.empty:
        return None

    cols = df.columns.tolist()
    num_cols = df.select_dtypes(include=["number"]).columns.tolist()
    non_num_cols = [c for c in cols if c not in num_cols]

    fig = None
    chart_type = preferred_type or "bar"
    chart_title = title or f"Analysis: {table_name.replace('_', ' ').title()}"

    # Check for date column
    date_col = None
    for c in non_num_cols:
        if any(d in c.lower() for d in ["date", "period", "month", "year", "time", "day"]):
            date_col = c
            break

    # 1. Line Chart (Time series)
    if (chart_type == "line" or date_col) and num_cols:
        x_col = date_col or (non_num_cols[0] if non_num_cols else cols[0])
        y_col = num_cols[0]
        fig = px.line(
            df,
            x=x_col,
            y=y_col,
            title=chart_title,
            markers=True,
            template="plotly_white"
        )
        chart_type = "line"

    # 2. Scatter Plot (Two numeric variables)
    elif chart_type == "scatter" and len(num_cols) >= 2:
        x_col, y_col = num_cols[0], num_cols[1]
        fig = px.scatter(
            df,
            x=x_col,
            y=y_col,
            title=chart_title,
            trendline="ols",
            template="plotly_white"
        )

    # 3. Bar Chart (Category vs Metric)
    elif non_num_cols and num_cols:
        cat_col = non_num_cols[0]
        metric_col = num_cols[0]
        # Top 15 records if many
        plot_df = df.head(15)
        fig = px.bar(
            plot_df,
            x=cat_col,
            y=metric_col,
            color=cat_col,
            title=chart_title,
            template="plotly_white",
            text_auto=".2s"
        )
        fig.update_layout(showlegend=False)
        chart_type = "bar"

    # 4. Histogram (Single numeric distribution)
    elif num_cols:
        metric_col = num_cols[0]
        fig = px.histogram(
            df,
            x=metric_col,
            nbins=25,
            title=chart_title,
            marginal="box",
            template="plotly_white"
        )
        chart_type = "histogram"

    if fig is None:
        return None

    fig.update_layout(
        font=dict(family="Inter, -apple-system, sans-serif"),
        title_font_size=16,
        margin=dict(l=40, r=40, t=50, b=40)
    )

    explanation = (
        f"This {chart_type} chart illustrates the computed {chart_title.lower()}, highlighting "
        f"primary trends, segment variations, and value distributions directly from the dataset."
    )

    return ChartArtifact(
        chart_id=f"chart_{table_name}",
        title=chart_title,
        chart_type=chart_type,
        figure_dict=fig.to_dict(),
        explanation=explanation,
        insights=[
            f"Evaluates {len(df)} computed data points.",
            f"Generated from output table '{table_name}'."
        ]
    )
