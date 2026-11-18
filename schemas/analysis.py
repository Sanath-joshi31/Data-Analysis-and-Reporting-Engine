"""Pydantic schemas for analytical planning, tasks, and data cleaning."""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class AnalysisTask(BaseModel):
    """A granular step or calculation in an analytical plan."""
    task_id: int = Field(description="Sequential task identifier (1, 2, ...)")
    title: str = Field(description="Short human-readable title of the task")
    description: str = Field(description="Specific analytical step, formula, or aggregation to perform")
    target_columns: List[str] = Field(default_factory=list, description="Columns utilized by this task")
    method: str = Field(description="Analytical technique: e.g., groupby, correlation, timeseries, t-test, percentile")
    expected_output: str = Field(description="Expected table, metric, or structure produced by this task")


class AnalysisPlan(BaseModel):
    """Structured analytical plan formulated by the Planning Agent."""
    question: str = Field(description="User's original or refined analytical question")
    objective_type: Literal["descriptive", "diagnostic", "predictive", "prescriptive"] = Field(
        default="descriptive",
        description="Category of analytics requested"
    )
    primary_goal: str = Field(description="Concise description of the analytical objective")
    relevant_columns: List[str] = Field(default_factory=list, description="Dataset columns strictly needed for this analysis")
    tasks: List[AnalysisTask] = Field(default_factory=list, description="Step-by-step analytical tasks")
    assumptions: List[str] = Field(default_factory=list, description="Explicit domain or analytical assumptions made")
    suggested_chart_types: List[str] = Field(
        default_factory=list, 
        description="Recommended chart types (e.g. line, bar, scatter, heatmap, box, histogram)"
    )
    explanation: str = Field(
        default="", 
        description="Reasoning explaining why this analytical plan satisfies the user question"
    )


class CleaningAction(BaseModel):
    """A specific data cleaning or transformation proposal."""
    action_id: str = Field(description="Unique identifier for the action")
    column: Optional[str] = Field(default=None, description="Column affected, or None if row-level operation")
    issue: str = Field(description="Detected data quality problem")
    action_type: Literal[
        "drop_duplicates", 
        "impute_median", 
        "impute_mean", 
        "impute_mode", 
        "impute_constant", 
        "drop_na_rows", 
        "cast_type", 
        "normalize_text", 
        "strip_whitespace", 
        "remove_outliers"
    ] = Field(description="Cleaning transformation type")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the transformation")
    is_destructive: bool = Field(default=False, description="True if operation removes rows or irreversibly modifies values")
    approved: bool = Field(default=False, description="Whether human approval has been granted")
    explanation: str = Field(description="Why this transformation is recommended")


class CleaningReport(BaseModel):
    """Complete report on data quality and cleaning transformations."""
    detected_issues: List[str] = Field(default_factory=list, description="Summary of data quality defects found")
    actions: List[CleaningAction] = Field(default_factory=list, description="List of proposed cleaning actions")
    original_row_count: int = Field(default=0, description="Row count before cleaning")
    original_column_count: int = Field(default=0, description="Column count before cleaning")
    cleaned_row_count: Optional[int] = Field(default=None, description="Row count after cleaning")
    cleaned_column_count: Optional[int] = Field(default=None, description="Column count after cleaning")
    summary: str = Field(default="", description="Executive summary of data cleaning")
