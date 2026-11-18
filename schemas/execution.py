"""Pydantic schemas for code generation, sandbox execution, error diagnosis, and validation."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExecutionResult(BaseModel):
    """Raw and parsed result of running generated code inside the sandbox."""
    success: bool = Field(description="True if execution exited cleanly with code 0")
    stdout: str = Field(default="", description="Captured standard output")
    stderr: str = Field(default="", description="Captured standard error")
    return_code: int = Field(default=0, description="Process return code")
    execution_time_seconds: float = Field(default=0.0, description="Wall clock runtime in seconds")
    memory_used_mb: float = Field(default=0.0, description="Peak memory utilized in MB")
    
    # Structured outputs saved to the artifact interface
    output_tables: Dict[str, List[Dict[str, Any]]] = Field(
        default_factory=dict,
        description="Tabular outputs converted to records (list of dicts)"
    )
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key computed numerical metrics (totals, means, percentages, etc.)"
    )
    figures_json: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Plotly figure dictionaries serialized to JSON-compatible dicts"
    )
    
    error: Optional[str] = Field(default=None, description="Primary exception name or error message")
    traceback: Optional[str] = Field(default=None, description="Full Python traceback if execution failed")


class ErrorDiagnosis(BaseModel):
    """Diagnosis of execution failure produced by Error Diagnosis Agent."""
    attempt_number: int = Field(description="Which retry attempt failed")
    error_type: str = Field(description="Exception class (e.g. KeyError, TypeError, ValueError, SyntaxError)")
    error_message: str = Field(description="Direct error message")
    root_cause: str = Field(description="Clear explanation of why the code failed (e.g. column not in dataframe, dtype mismatch)")
    offending_code_snippet: Optional[str] = Field(default=None, description="Lines of code causing the error")
    suggested_correction: str = Field(description="Specific actionable fix to apply")
    failed_code: str = Field(description="The complete code that failed")
    corrected_code: Optional[str] = Field(default=None, description="Proposed corrected code ready for next execution")


class ValidationResult(BaseModel):
    """Evaluation of computed results by the Result Validation Agent."""
    is_valid: bool = Field(description="True if the results are mathematically sound and answer the question")
    answers_question: bool = Field(description="Whether the output directly answers the user's inquiry")
    mathematically_sound: bool = Field(description="Whether checks passed (e.g. no illegal NaNs, non-empty results, reasonable sums)")
    feedback: str = Field(description="Detailed critique or confirmation of validation")
    flagged_issues: List[str] = Field(default_factory=list, description="Specific problems found (e.g., all values are null)")
    unsupported_assumptions: List[str] = Field(default_factory=list, description="Assumptions unsupported by data")
    confidence_score: float = Field(default=1.0, description="Confidence in the analytical result (0.0 to 1.0)")
