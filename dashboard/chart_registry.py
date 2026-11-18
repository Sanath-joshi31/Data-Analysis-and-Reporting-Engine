"""Comprehensive Plotly visualization engine supporting all dashboard chart types and themes."""

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


THEME_CONFIGS = {
    "light": {
        "template": "plotly_white",
        "bg_color": "#FFFFFF",
        "paper_bg": "#FFFFFF",
        "text_color": "#0F172A",
        "grid_color": "#E2E8F0",
        "color_sequence": px.colors.qualitative.Plotly,
        "primary": "#2563EB",
        "secondary": "#10B981"
    },
    "dark": {
        "template": "plotly_dark",
        "bg_color": "#0F172A",
        "paper_bg": "#0F172A",
        "text_color": "#F8FAFC",
        "grid_color": "#334155",
        "color_sequence": px.colors.qualitative.Dark24,
        "primary": "#38BDF8",
        "secondary": "#34D399"
    },
    "corporate": {
        "template": "plotly_white",
        "bg_color": "#FAFAFA",
        "paper_bg": "#FFFFFF",
        "text_color": "#1E293B",
        "grid_color": "#E2E8F0",
        "color_sequence": ["#1E3A8A", "#0284C7", "#0D9488", "#F59E0B", "#EF4444", "#8B5CF6"],
        "primary": "#1E3A8A",
        "secondary": "#0284C7"
    }
}


def apply_theme_layout(fig: go.Figure, theme: str = "corporate", title: str = "") -> go.Figure:
    """Apply consistent corporate typography, margins, and palette to a Plotly figure."""
    cfg = THEME_CONFIGS.get(theme, THEME_CONFIGS["corporate"])
    fig.update_layout(
        template=cfg["template"],
        paper_bgcolor=cfg["paper_bg"],
        plot_bgcolor=cfg["bg_color"],
        font=dict(family="Inter, -apple-system, sans-serif", color=cfg["text_color"], size=12),
        title=dict(
            text=f"<b>{title}</b>" if title else "",
            font=dict(size=14, color=cfg["text_color"]),
            x=0.02,
            y=0.96
        ),
        margin=dict(l=40, r=30, t=50, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11)
        ),
        hoverlabel=dict(font_size=12, font_family="Inter, sans-serif")
    )
    fig.update_xaxes(showgrid=True, gridcolor=cfg["grid_color"], zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor=cfg["grid_color"], zeroline=False)
    return fig


# ------------------------------------------------------------------------------
# TREND VISUALIZATIONS
# ------------------------------------------------------------------------------

def build_line_chart(
    df: pd.DataFrame, 
    x_col: str, 
    y_col: str, 
    color_col: Optional[str] = None,
    title: str = "",
    theme: str = "corporate",
    show_moving_avg: bool = False
) -> go.Figure:
    """Generate time-series line chart with optional moving average."""
    sub = df.dropna(subset=[x_col, y_col]).sort_values(by=x_col)
    cfg = THEME_CONFIGS.get(theme, THEME_CONFIGS["corporate"])

    if color_col and color_col in sub.columns:
        fig = px.line(
            sub, x=x_col, y=y_col, color=color_col,
            title=title, markers=True, color_discrete_sequence=cfg["color_sequence"]
        )
    else:
        fig = px.line(
            sub, x=x_col, y=y_col, title=title, markers=True,
            color_discrete_sequence=[cfg["primary"]]
        )
        if show_moving_avg and len(sub) >= 6:
            sub["MA_3"] = sub[y_col].rolling(window=3, min_periods=1).mean()
            fig.add_trace(go.Scatter(
                x=sub[x_col], y=sub["MA_3"],
                mode="lines", name="3-Period Moving Avg",
                line=dict(dash="dash", color=cfg["secondary"], width=2)
            ))

    return apply_theme_layout(fig, theme, title)


def build_area_chart(
    df: pd.DataFrame, 
    x_col: str, 
    y_col: str, 
    color_col: Optional[str] = None,
    title: str = "",
    theme: str = "corporate"
) -> go.Figure:
    """Generate stacked or single area chart for trend volumes."""
    sub = df.dropna(subset=[x_col, y_col]).sort_values(by=x_col)
    cfg = THEME_CONFIGS.get(theme, THEME_CONFIGS["corporate"])
    fig = px.area(
        sub, x=x_col, y=y_col, color=color_col,
        title=title, color_discrete_sequence=cfg["color_sequence"]
    )
    return apply_theme_layout(fig, theme, title)


# ------------------------------------------------------------------------------
# COMPARATIVE VISUALIZATIONS
# ------------------------------------------------------------------------------

def build_bar_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    color_col: Optional[str] = None,
    orientation: str = "v",
    title: str = "",
    theme: str = "corporate",
    barmode: str = "group"
) -> go.Figure:
    """Generate vertical or horizontal bar chart with group/stack modes."""
    sub = df.dropna(subset=[x_col, y_col])
    cfg = THEME_CONFIGS.get(theme, THEME_CONFIGS["corporate"])

    if orientation == "h":
        fig = px.bar(
            sub, x=y_col, y=x_col, color=color_col or x_col,
            orientation="h", title=title, text_auto=".2s",
            color_discrete_sequence=cfg["color_sequence"]
        )
        fig.update_layout(yaxis=dict(autorange="reversed"), showlegend=bool(color_col))
    else:
        fig = px.bar(
            sub, x=x_col, y=y_col, color=color_col or x_col,
            barmode=barmode, title=title, text_auto=".2s",
            color_discrete_sequence=cfg["color_sequence"]
        )
        if not color_col:
            fig.update_layout(showlegend=False)

    return apply_theme_layout(fig, theme, title)


def build_pareto_chart(
    df: pd.DataFrame,
    cat_col: str,
    val_col: str,
    title: str = "",
    theme: str = "corporate"
) -> go.Figure:
    """Generate Pareto 80/20 chart combining bars and cumulative percentage line."""
    sub = df.groupby(cat_col)[val_col].sum().reset_index()
    sub = sub.sort_values(by=val_col, ascending=False).head(15)
    total = sub[val_col].sum()
    sub["cum_pct"] = (sub[val_col].cumsum() / total * 100.0).round(2)

    cfg = THEME_CONFIGS.get(theme, THEME_CONFIGS["corporate"])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=sub[cat_col], y=sub[val_col], name=val_col,
        marker_color=cfg["primary"], text=sub[val_col].apply(lambda v: f"{v:,.0f}"),
        textposition="auto"
    ))
    fig.add_trace(go.Scatter(
        x=sub[cat_col], y=sub["cum_pct"], name="Cumulative %",
        yaxis="y2", mode="lines+markers",
        line=dict(color="#EF4444", width=2.5),
        marker=dict(size=6)
    ))

    fig.update_layout(
        yaxis2=dict(
            title="Cumulative %",
            overlaying="y",
            side="right",
            range=[0, 105],
            showgrid=False
        )
    )
    return apply_theme_layout(fig, theme, title)


# ------------------------------------------------------------------------------
# COMPOSITION VISUALIZATIONS
# ------------------------------------------------------------------------------

def build_donut_chart(
    df: pd.DataFrame,
    names_col: str,
    values_col: str,
    title: str = "",
    theme: str = "corporate"
) -> go.Figure:
    """Generate modern donut chart with central hole."""
    sub = df.groupby(names_col)[values_col].sum().reset_index()
    sub = sub.sort_values(by=values_col, ascending=False).head(8)
    cfg = THEME_CONFIGS.get(theme, THEME_CONFIGS["corporate"])

    fig = px.pie(
        sub, names=names_col, values=values_col,
        hole=0.45, title=title,
        color_discrete_sequence=cfg["color_sequence"]
    )
    fig.update_traces(textinfo="percent+label", textposition="outside")
    return apply_theme_layout(fig, theme, title)


def build_treemap(
    df: pd.DataFrame,
    path_cols: List[str],
    values_col: str,
    title: str = "",
    theme: str = "corporate"
) -> go.Figure:
    """Generate hierarchical Treemap visualization."""
    sub = df.dropna(subset=path_cols + [values_col])
    cfg = THEME_CONFIGS.get(theme, THEME_CONFIGS["corporate"])

    fig = px.treemap(
        sub, path=path_cols, values=values_col,
        title=title, color_discrete_sequence=cfg["color_sequence"]
    )
    fig.update_traces(root_color="lightgrey")
    return apply_theme_layout(fig, theme, title)


# ------------------------------------------------------------------------------
# DISTRIBUTION & RELATIONSHIP VISUALIZATIONS
# ------------------------------------------------------------------------------

def build_histogram(
    df: pd.DataFrame,
    x_col: str,
    nbins: int = 30,
    title: str = "",
    theme: str = "corporate"
) -> go.Figure:
    """Generate distribution histogram with marginal box plot."""
    sub = df.dropna(subset=[x_col])
    cfg = THEME_CONFIGS.get(theme, THEME_CONFIGS["corporate"])

    fig = px.histogram(
        sub, x=x_col, nbins=nbins, marginal="box",
        title=title, color_discrete_sequence=[cfg["primary"]]
    )
    return apply_theme_layout(fig, theme, title)


def build_box_plot(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str = "",
    theme: str = "corporate"
) -> go.Figure:
    """Generate outlier box plot across categories."""
    sub = df.dropna(subset=[x_col, y_col])
    cfg = THEME_CONFIGS.get(theme, THEME_CONFIGS["corporate"])

    fig = px.box(
        sub, x=x_col, y=y_col, color=x_col,
        title=title, color_discrete_sequence=cfg["color_sequence"]
    )
    fig.update_layout(showlegend=False)
    return apply_theme_layout(fig, theme, title)


def build_scatter_plot(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    color_col: Optional[str] = None,
    size_col: Optional[str] = None,
    title: str = "",
    theme: str = "corporate"
) -> go.Figure:
    """Generate scatter plot with optional regression trendline and bubble size."""
    needed = [x_col, y_col]
    if color_col:
        needed.append(color_col)
    if size_col:
        needed.append(size_col)

    sub = df.dropna(subset=needed)
    if len(sub) > 600:
        sub = sub.sample(600, random_state=42)

    cfg = THEME_CONFIGS.get(theme, THEME_CONFIGS["corporate"])

    fig = px.scatter(
        sub, x=x_col, y=y_col, color=color_col, size=size_col,
        trendline="ols" if not color_col else None,
        title=title, color_discrete_sequence=cfg["color_sequence"]
    )
    return apply_theme_layout(fig, theme, title)


def build_correlation_heatmap(
    df: pd.DataFrame,
    numeric_cols: List[str],
    title: str = "Correlation Matrix",
    theme: str = "corporate"
) -> go.Figure:
    """Generate interactive correlation heatmap."""
    cols = [c for c in numeric_cols if c in df.columns][:8]
    if len(cols) < 2:
        cols = df.select_dtypes(include=[np.number]).columns.tolist()[:8]

    corr = df[cols].corr().round(2)
    fig = px.imshow(
        corr, text_auto=True, aspect="auto",
        title=title, color_continuous_scale="RdBu_r"
    )
    return apply_theme_layout(fig, theme, title)


# ------------------------------------------------------------------------------
# ADVANCED VISUALIZATIONS (FORECAST & ANOMALY)
# ------------------------------------------------------------------------------

def build_forecast_chart(
    historical_data: List[Dict[str, Any]],
    forecast_data: List[Dict[str, Any]],
    title: str = "Trend Forecast",
    theme: str = "corporate"
) -> go.Figure:
    """Generate forecast chart with historical trend and forward projection."""
    cfg = THEME_CONFIGS.get(theme, THEME_CONFIGS["corporate"])
    fig = go.Figure()

    if historical_data:
        h_dates = [d["date"] for d in historical_data]
        h_actual = [d.get("actual") for d in historical_data]
        h_fitted = [d.get("fitted_trend") for d in historical_data]

        fig.add_trace(go.Scatter(
            x=h_dates, y=h_actual, mode="lines+markers", name="Actual",
            line=dict(color=cfg["primary"], width=2.5)
        ))
        if any(h_fitted):
            fig.add_trace(go.Scatter(
                x=h_dates, y=h_fitted, mode="lines", name="Historical Trend",
                line=dict(dash="dot", color="#94A3B8")
            ))

    if forecast_data:
        f_dates = [d["date"] for d in forecast_data]
        f_preds = [d.get("forecast") for d in forecast_data]

        fig.add_trace(go.Scatter(
            x=f_dates, y=f_preds, mode="lines+markers", name="Forecast Projection",
            line=dict(dash="dash", color="#F59E0B", width=2.5),
            marker=dict(symbol="star", size=8)
        ))

    return apply_theme_layout(fig, theme, title)


def build_anomaly_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    outlier_indices: List[Any],
    title: str = "Anomaly Detection",
    theme: str = "corporate"
) -> go.Figure:
    """Generate anomaly detection chart highlighting detected outliers in bright red."""
    cfg = THEME_CONFIGS.get(theme, THEME_CONFIGS["corporate"])
    normal_df = df.drop(index=outlier_indices, errors="ignore")
    anomaly_df = df.loc[df.index.intersection(outlier_indices)]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=normal_df[x_col], y=normal_df[y_col],
        mode="markers", name="Normal Records",
        marker=dict(color=cfg["primary"], opacity=0.7, size=7)
    ))
    if not anomaly_df.empty:
        fig.add_trace(go.Scatter(
            x=anomaly_df[x_col], y=anomaly_df[y_col],
            mode="markers", name="Detected Outliers",
            marker=dict(color="#EF4444", symbol="x", size=10, line=dict(width=2, color="#7F1D1D"))
        ))

    return apply_theme_layout(fig, theme, title)
