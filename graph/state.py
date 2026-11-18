"""State definition for LangGraph Autonomous Data Analyst workflow."""

from typing import Any, Dict, List, Optional, TypedDict
from schemas.analysis import AnalysisPlan, CleaningReport
from schemas.dataset import DatasetProfile
from schemas.execution import ErrorDiagnosis, ExecutionResult, ValidationResult
from schemas.report import AnalyticalReport, ChartArtifact


class AnalystWorkflowState(TypedDict, total=False):
    """Shared state dictionary tracked and updated across all LangGraph nodes."""

    # Input parameters
    question: str
    dataset_id: str
    dataset_path: str
    conversation_history: List[Dict[str, str]]

    # Profiling & Quality
    dataset_profile: Optional[DatasetProfile]
    cleaning_report: Optional[CleaningReport]

    # Planning & Specification
    analysis_plan: Optional[AnalysisPlan]
    analyst_specification: Optional[Dict[str, Any]]

    # Code Generation & Execution Loop
    generated_code: Optional[str]
    execution_result: Optional[ExecutionResult]
    error_diagnoses: List[ErrorDiagnosis]
    retry_count: int
    max_retries: int

    # Validation
    validation_result: Optional[ValidationResult]

    # Reporting & Artifacts
    charts: List[ChartArtifact]
    final_report: Optional[AnalyticalReport]

    # Workflow Control
    current_step: str
    is_complete: bool
    status_message: str
    execution_trace: List[Dict[str, Any]]
