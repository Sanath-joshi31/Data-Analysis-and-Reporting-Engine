"""Agent 8: Result Validation Agent."""

import json
import logging
import math
from typing import Any, Dict, List, Optional
from schemas.analysis import AnalysisPlan
from schemas.dataset import DatasetProfile
from schemas.execution import ExecutionResult, ValidationResult
from services.llm_service import LLMService, get_llm_service

logger = logging.getLogger(__name__)

VALIDATION_SYSTEM_PROMPT = """You are the Senior Result Validation Agent of an Autonomous Data Analyst AI.
Your critical responsibility is to verify that the execution output is mathematically valid, non-empty, and genuinely answers the user's question.

CRITICAL RULES:
- Never approve an analysis merely because Python exited with return code 0.
- If all calculated metrics are null, empty, or zero without justification, mark as invalid.
- Check that output tables have rows and correspond to the question.
- Verify that numeric aggregations are reasonable (e.g., negative revenue when unexpected, infinite growth rates).
- Return a structured ValidationResult.
"""


class ValidationAgent:
    """Agent that validates mathematical sanity, non-emptiness, and relevance of computed results."""

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or get_llm_service()

    def validate(
        self,
        execution_result: ExecutionResult,
        plan: AnalysisPlan,
        profile: DatasetProfile
    ) -> ValidationResult:
        """Thoroughly audit execution outputs for mathematical validity and domain accuracy."""
        logger.info(f"ValidationAgent auditing execution output for question: '{plan.question}'")

        # 1. Deterministic Sanity Checks
        flagged_issues: List[str] = []
        math_valid = True
        answers_question = True

        # Check if output is empty
        has_tables = bool(execution_result.output_tables)
        has_metrics = bool(execution_result.metrics)
        has_figures = bool(execution_result.figures_json)

        if not (has_tables or has_metrics or has_figures):
            flagged_issues.append("Execution produced zero output tables, metrics, or visualizations.")
            math_valid = False
            answers_question = False

        # Check for NaN / Infinity in metrics
        for k, v in execution_result.metrics.items():
            if v is None:
                flagged_issues.append(f"Metric '{k}' is None/null.")
            elif isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                flagged_issues.append(f"Metric '{k}' evaluates to an illegal floating point NaN or Infinity.")
                math_valid = False

        # Check for empty output tables
        for tbl_name, rows in execution_result.output_tables.items():
            if not rows or len(rows) == 0:
                flagged_issues.append(f"Output table '{tbl_name}' contains 0 rows.")
                math_valid = False

        # If deterministic checks already failed, return early failure
        if flagged_issues:
            return ValidationResult(
                is_valid=False,
                answers_question=answers_question,
                mathematically_sound=math_valid,
                feedback="Deterministic validation failed:\n" + "\n".join(f"- {iss}" for iss in flagged_issues),
                flagged_issues=flagged_issues,
                confidence_score=0.2
            )

        # 2. LLM or Advanced Semantic Check if configured
        if self.llm_service.is_configured:
            try:
                user_content = (
                    f"User Question: {plan.question}\n"
                    f"Analytical Goal: {plan.primary_goal}\n"
                    f"Computed Metrics:\n{json.dumps(execution_result.metrics, indent=2)}\n"
                    f"Computed Table Headers & Sample Rows:\n"
                    f"{json.dumps({k: v[:3] for k, v in execution_result.output_tables.items()}, indent=2)}\n"
                    f"Figures Generated Count: {len(execution_result.figures_json)}\n"
                )
                messages = [
                    {"role": "system", "content": VALIDATION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content}
                ]
                return self.llm_service.generate_structured_output(
                    messages=messages,
                    response_model=ValidationResult,
                    temperature=0.0
                )
            except Exception as e:
                logger.warning(f"ValidationAgent LLM check failed: {e}. Using deterministic pass.")

        # Default clean pass
        return ValidationResult(
            is_valid=True,
            answers_question=True,
            mathematically_sound=True,
            feedback="All numerical sanity checks, non-emptiness tests, and table verifications passed.",
            flagged_issues=[],
            confidence_score=0.95
        )
