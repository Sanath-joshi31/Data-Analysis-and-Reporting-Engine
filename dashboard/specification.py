"""Pydantic data models defining the Autonomous Dashboard specification."""

from typing import Any, Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, Field


class KPISpecification(BaseModel):
    """Specification for an executive summary Key Performance Indicator (KPI)."""
    id: str = Field(description="Unique KPI identifier")
    label: str = Field(description="Display label (e.g. 'Total Sales', 'Average Profit Margin')")
    metric_column: Optional[str] = Field(default=None, description="Underlying column name")
    aggregation: Literal["sum", "mean", "median", "count", "distinct_count", "growth", "ratio"] = Field(
        default="sum",
        description="Aggregation method applied"
    )
    value: float = Field(default=0.0, description="Raw computed numerical value")
    formatted_value: str = Field(default="", description="Human-friendly formatted value (e.g. '$1.2M', '24.5%')")
    delta: Optional[float] = Field(default=None, description="Period growth or comparative delta")
    delta_formatted: Optional[str] = Field(default=None, description="Formatted delta percentage or difference")
    delta_positive: bool = Field(default=True, description="True if growth is favorable")
    icon: str = Field(default="📊", description="Emoji or icon descriptor")
    explanation: Optional[str] = Field(default=None, description="Brief narrative context for this metric")


class ChartSpecification(BaseModel):
    """Detailed specification for an individual interactive dashboard chart."""
    id: str = Field(description="Unique chart identifier")
    title: str = Field(description="User-facing chart title")
    chart_type: Literal[
        "line", "area", "bar", "horizontal_bar", "grouped_bar", "stacked_bar", "pareto",
        "donut", "pie", "treemap", "sunburst",
        "histogram", "box", "violin",
        "scatter", "bubble", "heatmap", "regression",
        "forecast", "anomaly", "funnel"
    ] = Field(description="Visualization chart type")
    description: str = Field(default="", description="Purpose and business context of this chart")
    section_id: str = Field(default="executive_summary", description="Parent section ID")

    # Column bindings
    x_col: Optional[str] = Field(default=None, description="Column mapped to X-axis")
    y_col: Optional[str] = Field(default=None, description="Column mapped to Y-axis")
    color_col: Optional[str] = Field(default=None, description="Column mapped to color/grouping")
    size_col: Optional[str] = Field(default=None, description="Column mapped to marker size")
    facet_col: Optional[str] = Field(default=None, description="Column mapped to subplots/facets")
    orientation: Literal["v", "h"] = Field(default="v", description="Vertical or horizontal orientation")

    # Aggregation & Filtering parameters
    aggregation: Literal["sum", "mean", "median", "count", "none"] = Field(default="sum")
    sort_by: Optional[str] = Field(default="y_desc", description="Sort order: 'x_asc', 'y_desc', 'none'")
    top_n: Optional[int] = Field(default=15, description="Limit to top N categories for clarity")

    # Computed figures & metadata
    figure_dict: Dict[str, Any] = Field(default_factory=dict, description="Serialized Plotly figure dictionary")
    table_records: List[Dict[str, Any]] = Field(default_factory=list, description="Computed data records powering this chart")
    explanation: str = Field(default="", description="AI-generated explanation of the chart")
    insights: List[str] = Field(default_factory=list, description="Key empirical takeaways extracted from this chart")

    # Interactive state
    visible: bool = Field(default=True, description="Whether this chart is visible in layout")
    order: int = Field(default=0, description="Display order within section")


class DashboardSection(BaseModel):
    """Logical grouping of KPIs and visualizations within the dashboard."""
    section_id: str = Field(description="Unique section identifier")
    title: str = Field(description="Section heading")
    description: str = Field(default="", description="Section scope and narrative")
    order: int = Field(default=0, description="Display sequence order")
    visible: bool = Field(default=True, description="Whether section is rendered")
    charts: List[ChartSpecification] = Field(default_factory=list, description="Charts belonging to this section")
    kpis: List[KPISpecification] = Field(default_factory=list, description="KPIs belonging to this section")


class DashboardFilterState(BaseModel):
    """Active filter selection criteria applied across the entire dashboard."""
    date_column: Optional[str] = Field(default=None)
    date_range: Optional[Tuple[str, str]] = Field(default=None, description="Start date and end date strings")
    selected_categories: Dict[str, List[str]] = Field(default_factory=dict, description="Selected values per category")
    metric_column: Optional[str] = Field(default=None, description="Currently selected primary metric")


class DashboardSpecification(BaseModel):
    """Complete, end-to-end specification for an autonomously built analytics dashboard."""
    dashboard_id: str = Field(description="Unique dashboard UUID")
    title: str = Field(description="Dashboard title")
    dataset_name: str = Field(description="Underlying dataset filename")
    dataset_id: str = Field(description="Underlying dataset ID")
    theme: Literal["light", "dark", "corporate"] = Field(default="corporate", description="Visual theme")
    created_at: str = Field(default="", description="Creation timestamp")

    # Dashboard contents
    sections: List[DashboardSection] = Field(default_factory=list, description="Structured dashboard sections")
    global_kpis: List[KPISpecification] = Field(default_factory=list, description="Top-level executive KPI cards")

    # Filters and interaction
    filter_state: DashboardFilterState = Field(default_factory=DashboardFilterState)
    available_filters: Dict[str, List[str]] = Field(default_factory=dict, description="Available categorical filter options")

    # AI Business Insights & Narrative
    executive_summary: str = Field(default="", description="High-level narrative executive summary")
    key_findings: List[str] = Field(default_factory=list, description="Primary empirical discoveries")
    risks: List[str] = Field(default_factory=list, description="Operational risks and performance vulnerabilities")
    opportunities: List[str] = Field(default_factory=list, description="Identified growth opportunities")
    recommendations: List[str] = Field(default_factory=list, description="Evidence-backed strategic recommendations")
