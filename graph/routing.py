"""Conditional routing functions for LangGraph workflow."""

import logging
from typing import Literal
from graph.state import AnalystWorkflowState

logger = logging.getLogger(__name__)


def route_after_execution(state: AnalystWorkflowState) -> Literal["validate_results", "diagnose_error", "generate_report"]:
    """Route depending on sandbox execution outcome and retry budget."""
    exec_res = state.get("execution_result")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)

    if exec_res and exec_res.success:
        logger.info("Execution succeeded. Routing to result validation.")
        return "validate_results"

    if retry_count < max_retries:
        logger.info(f"Execution failed. Attempt {retry_count}/{max_retries}. Routing to error diagnosis.")
        return "diagnose_error"

    logger.warning(f"Exhausted maximum retry budget ({max_retries}). Routing to final report with error limitations.")
    return "generate_report"


def route_after_validation(state: AnalystWorkflowState) -> Literal["generate_visualizations", "regenerate_code", "generate_report"]:
    """Route based on mathematical and semantic validation of computed results."""
    val_res = state.get("validation_result")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)

    if val_res and val_res.is_valid:
        logger.info("Validation passed. Routing to visualization generation.")
        return "generate_visualizations"

    if retry_count < max_retries:
        logger.info(f"Validation failed: {val_res.feedback if val_res else 'unknown'}. Routing to code regeneration.")
        return "regenerate_code"

    logger.warning(f"Validation failed and retry budget exhausted. Routing to reporting with caveats.")
    return "generate_report"
