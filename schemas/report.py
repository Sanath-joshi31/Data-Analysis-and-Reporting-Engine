"""Pydantic schemas for visualizations, business insights, and reports."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChartArtifact(BaseModel):
    """Metadata and serialized content for a generated visualization."""
    chart_id: str = Field(description="Unique identifier for the chart")
    title: str = Field(description="Visual chart title")
    chart_type: str = Field(description="Chart type: 'line', 'bar', 'scatter', 'heatmap', 'box', 'histogram', 'pie'")
    figure_dict: Dict[str, Any] = Field(description="Serialized Plotly figure dictionary")
    explanation: str = Field(description="Natural language explanation of what the chart demonstrates")
    insights: List[str] = Field(default_factory=list, description="Bullet points of key visual takeaways")


class InsightItem(BaseModel):
    """An individual actionable business finding backed by computed evidence."""
    title: str = Field(description="Short headline for the finding")
    category: str = Field(description="Category: 'Trend', 'Anomaly', 'Segment Comparison', 'Risk', 'Opportunity'")
    finding: str = Field(description="Objective observation of what the data shows")
    evidence: str = Field(description="Exact computed numerical figures and metrics proving this finding")
    business_implication: str = Field(description="Why this matters for the business or organization")
    recommendation: str = Field(description="Specific actionable, evidence-based recommendation")


class AnalyticalReport(BaseModel):
    """Complete analytical report compiling findings, charts, tables, and recommendations."""
    report_id: str = Field(description="Unique report identifier")
    question: str = Field(description="Original user question answered by this report")
    dataset_name: str = Field(description="Source dataset name")
    executive_summary: str = Field(description="High-level narrative summary of findings")
    key_findings: List[InsightItem] = Field(default_factory=list, description="List of structured insight items")
    limitations: List[str] = Field(default_factory=list, description="Analytical boundaries, cautions, and limitations")
    recommendations: List[str] = Field(default_factory=list, description="Prioritized strategic business recommendations")
    charts: List[ChartArtifact] = Field(default_factory=list, description="Generated charts and their interpretations")
    tabular_results: Dict[str, List[Dict[str, Any]]] = Field(
        default_factory=dict, 
        description="Key output tables generated during analysis"
    )
    metrics_summary: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Core calculated scalar metrics"
    )
    code_executed: Optional[str] = Field(default=None, description="Final Python code used to derive results")
