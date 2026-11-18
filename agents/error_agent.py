"""Agent 7: Error Diagnosis and Self-Correction Agent."""

import json
import logging
import re
from typing import List, Optional
from schemas.dataset import DatasetProfile
from schemas.execution import ErrorDiagnosis, ExecutionResult
from services.llm_service import LLMService, get_llm_service

logger = logging.getLogger(__name__)

ERROR_DIAGNOSIS_PROMPT = """You are the Senior Error Diagnosis and Debugging Agent of an Autonomous Data Analyst AI.
A Python data analysis script failed during isolated sandbox execution.

Your mission is to:
1. Parse the traceback and stderr.
2. Identify the root cause (e.g., misspelled column name, wrong datatype, division by zero, missing aggregation).
3. Check the valid columns available in the Dataset Profile.
4. Produce a corrected, self-contained Python script that fixes the bug and adheres to the execution harness rules.
"""


class ErrorAgent:
    """Diagnoses execution failures, analyzes tracebacks, and formulates targeted code repairs."""

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or get_llm_service()

    def diagnose_and_correct(
        self,
        attempt_number: int,
        failed_code: str,
        execution_result: ExecutionResult,
        profile: DatasetProfile
    ) -> ErrorDiagnosis:
        """Analyze exception and generate a repaired code candidate."""
        stderr = execution_result.stderr or ""
        error_type, error_msg = self._extract_error_details(stderr)

        logger.info(f"ErrorAgent diagnosing attempt #{attempt_number}: {error_type} - {error_msg}")

        if self.llm_service.is_configured:
            try:
                return self._diagnose_with_llm(attempt_number, failed_code, execution_result, profile, error_type, error_msg)
            except Exception as e:
                logger.warning(f"ErrorAgent LLM call failed: {e}. Falling back to rule-based diagnosis.")

        return self._diagnose_with_heuristics(attempt_number, failed_code, execution_result, profile, error_type, error_msg)

    def _extract_error_details(self, stderr: str) -> tuple[str, str]:
        lines = [line.strip() for line in stderr.strip().split("\n") if line.strip()]
        if not lines:
            return "ExecutionError", "Process failed with non-zero exit code"

        last_line = lines[-1]
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*Error|Exception):\s*(.*)$", last_line)
        if match:
            return match.group(1), match.group(2)
        return "RuntimeError", last_line

    def _diagnose_with_llm(
        self,
        attempt_number: int,
        failed_code: str,
        execution_result: ExecutionResult,
        profile: DatasetProfile,
        error_type: str,
        error_msg: str
    ) -> ErrorDiagnosis:
        prompt = (
            f"Attempt Number: {attempt_number}\n"
            f"Available Dataset Columns & Types:\n"
            f"{json.dumps({c: prof.dtype for c, prof in profile.columns.items()}, indent=2)}\n\n"
            f"Failed Code:\n```python\n{failed_code}\n```\n\n"
            f"Full Error Traceback:\n{execution_result.stderr}\n\n"
            "Provide diagnosis, root cause, suggested fix, and fully corrected code."
        )

        messages = [
            {"role": "system", "content": ERROR_DIAGNOSIS_PROMPT},
            {"role": "user", "content": prompt}
        ]

        response = self.llm_service.generate_structured_output(
            messages=messages,
            response_model=ErrorDiagnosis,
            temperature=0.0
        )
        response.attempt_number = attempt_number
        response.failed_code = failed_code
        return response

    def _diagnose_with_heuristics(
        self,
        attempt_number: int,
        failed_code: str,
        execution_result: ExecutionResult,
        profile: DatasetProfile,
        error_type: str,
        error_msg: str
    ) -> ErrorDiagnosis:
        corrected_code = failed_code
        root_cause = f"Python raised {error_type}: {error_msg}"
        suggested_fix = "Apply defensive null-checking and column validation."

        # Case 1: KeyError (misspelled column)
        if error_type == "KeyError":
            import difflib
            match = re.search(r"['\"](.*?)['\"]", error_msg)
            missing_col = match.group(1) if match else ""
            valid_cols = list(profile.columns.keys())
            closest = None
            if missing_col:
                # 1. Exact case-insensitive
                for col in valid_cols:
                    if col.lower() == missing_col.lower():
                        closest = col
                        break
                # 2. Substring match
                if not closest:
                    for col in valid_cols:
                        if col.lower() in missing_col.lower() or missing_col.lower() in col.lower():
                            closest = col
                            break
                # 3. Fuzzy match
                if not closest:
                    matches = difflib.get_close_matches(missing_col, valid_cols, n=1, cutoff=0.3)
                    if matches:
                        closest = matches[0]

            if not closest and valid_cols:
                closest = valid_cols[0]

            if missing_col and closest:
                root_cause = f"Column '{missing_col}' does not exist in dataset. Did you mean '{closest}'?"
                suggested_fix = f"Replace references to '{missing_col}' with '{closest}'."
                corrected_code = failed_code.replace(f"'{missing_col}'", f"'{closest}'").replace(f'"{missing_col}"', f'"{closest}"')

        # Case 2: TypeError / AttributeError on dates or strings
        elif "datetime" in error_msg.lower() or "dt" in error_msg.lower():
            root_cause = "Attempted datetime operation on non-datetime column or contains invalid string dates."
            suggested_fix = "Wrap with pd.to_datetime(col, errors='coerce') and drop NaNs."
            # Inject defensive conversion at start of code
            if profile.datetime_columns:
                date_c = profile.datetime_columns[0]
                prefix = f"df['{date_c}'] = pd.to_datetime(df['{date_c}'], errors='coerce')\ndf = df.dropna(subset=['{date_c}'])\n"
                corrected_code = prefix + failed_code

        # Case 3: Division by zero or NaN issues
        elif "zero" in error_msg.lower() or "inf" in error_msg.lower():
            root_cause = "Division by zero or unhandled infinite values in metric calculation."
            suggested_fix = "Replace 0 divisors with np.nan and use fillna(0)."
            corrected_code = "import numpy as np\n" + failed_code.replace("/ 0", "/ np.nan")

        return ErrorDiagnosis(
            attempt_number=attempt_number,
            error_type=error_type,
            error_message=error_msg,
            root_cause=root_cause,
            suggested_correction=suggested_fix,
            failed_code=failed_code,
            corrected_code=corrected_code
        )
