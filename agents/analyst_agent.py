"""Agent 4: Analysis Agent."""

import json
import logging
from typing import Any, Dict, List, Optional
from schemas.analysis import AnalysisPlan
from schemas.dataset import DatasetProfile
from services.llm_service import LLMService, get_llm_service

logger = logging.getLogger(__name__)

ANALYST_SYSTEM_PROMPT = """You are the Senior Data Scientist & Statistical Analyst Agent of an Autonomous Data Analyst AI.
Your job is to examine the AnalysisPlan and DatasetProfile, select the precise statistical methods, equations, aggregations, and data manipulations, and produce an explicit computational specification for the Python Code Generation Agent.

You must specify:
1. Exact groupby operations, aggregations, sort orders, and filters.
2. What statistical methods are required (mean, median, IQR, Pearson r, p-values, linear regression, etc.).
3. What dictionary keys in `OUTPUT['tables']` and `OUTPUT['metrics']` must be populated.
4. Edge cases to handle (division by zero, missing values, empty subsets).
"""


class AnalystAgent:
    """Selects mathematical and analytical methodologies and prepares code execution requirements."""

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or get_llm_service()

    def formulate_specification(
        self,
        plan: AnalysisPlan,
        profile: DatasetProfile
    ) -> Dict[str, Any]:
        """Produce concrete computational requirements for code generation."""
        logger.info(f"AnalystAgent formulating analytical specifications for plan: '{plan.primary_goal}'")

        if self.llm_service.is_configured:
            try:
                user_msg = (
                    f"Analysis Plan:\n{plan.model_dump_json(indent=2)}\n\n"
                    f"Dataset Profile:\n"
                    f"- Numeric Columns: {profile.numeric_columns}\n"
                    f"- Categorical Columns: {profile.categorical_columns}\n"
                    f"- Datetime Columns: {profile.datetime_columns}\n\n"
                    "Provide a clear JSON specification of calculations, output keys, and edge-case handlings."
                )
                response_text = self.llm_service.generate_chat_completion(
                    messages=[
                        {"role": "system", "content": ANALYST_SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg}
                    ],
                    temperature=0.1
                )
                # Attempt to parse json if structured
                try:
                    cleaned = response_text.strip()
                    if cleaned.startswith("```json"):
                        cleaned = cleaned[7:]
                    if cleaned.startswith("```"):
                        cleaned = cleaned[3:]
                    if cleaned.endswith("```"):
                        cleaned = cleaned[:-3]
                    return json.loads(cleaned)
                except Exception:
                    return {"methodology_notes": response_text}
            except Exception as e:
                logger.warning(f"AnalystAgent LLM call failed: {e}. Falling back to heuristic specification.")

        # Heuristic specification
        return {
            "objective": plan.objective_type,
            "relevant_columns": plan.relevant_columns,
            "operations": [task.description for task in plan.tasks],
            "required_tables": ["primary_analysis_table"],
            "required_metrics": ["summary_statistics"]
        }
