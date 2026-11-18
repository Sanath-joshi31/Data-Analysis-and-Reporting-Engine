"""Agent 2: Planning Agent."""

import json
import logging
from typing import Any, Dict, List, Optional
from schemas.dataset import DatasetProfile
from schemas.analysis import AnalysisPlan, AnalysisTask
from services.llm_service import LLMService, get_llm_service

logger = logging.getLogger(__name__)


PLANNER_SYSTEM_PROMPT = """You are the Senior Planning Agent of an Autonomous Data Analyst AI.
Your mission is to understand user analytical inquiries, identify the objective, determine necessary columns, and construct a precise, actionable AnalysisPlan.

Analytical Objectives:
- 'descriptive': Summarizing totals, distributions, counts, means, percentiles, or rankings.
- 'diagnostic': Comparing segments, finding reasons for variance, investigating correlations or drivers.
- 'predictive': Forecasting trends into future periods, linear regression, customer clustering.
- 'prescriptive': Scenario evaluation, optimization proposals, actionable business recommendations.

Guidelines:
1. ONLY reference columns that actually exist in the Dataset Profile.
2. Break complex questions into clear sequential subtasks.
3. Suggest appropriate chart types ('line', 'bar', 'scatter', 'heatmap', 'box', 'histogram').
4. If the question is a conversational follow-up (e.g., 'Show its trend' or 'Compare it with North'), incorporate context from previous turns.
5. Explicitly state analytical assumptions.
"""


class PlanningAgent:
    """Agent that creates structured analytical execution plans from natural language queries."""

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or get_llm_service()

    def run(
        self,
        question: str,
        profile: DatasetProfile,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> AnalysisPlan:
        """Formulate a comprehensive AnalysisPlan."""
        logger.info(f"PlanningAgent formulating plan for: '{question}'")

        if self.llm_service.is_configured:
            try:
                return self._plan_with_llm(question, profile, conversation_history)
            except Exception as e:
                logger.warning(f"LLM planning encountered error: {e}. Falling back to rule-based planner.")

        return self._plan_with_heuristics(question, profile, conversation_history)

    def _plan_with_llm(
        self,
        question: str,
        profile: DatasetProfile,
        conversation_history: Optional[List[Dict[str, str]]]
    ) -> AnalysisPlan:
        columns_summary = {
            col_name: {
                "dtype": col.dtype,
                "inferred_type": col.inferred_type,
                "sample_values": col.sample_values,
                "null_count": col.missing_count
            }
            for col_name, col in profile.columns.items()
        }

        user_content = (
            f"Dataset Name: {profile.filename}\n"
            f"Total Rows: {profile.row_count}, Columns: {profile.column_count}\n"
            f"Available Columns & Metadata:\n{json.dumps(columns_summary, indent=2)}\n\n"
            f"User Question: {question}\n"
        )

        if conversation_history:
            history_text = "\n".join(f"{m['role']}: {m['content']}" for m in conversation_history[-4:])
            user_content += f"\nRecent Conversation Context:\n{history_text}\n"

        messages = [
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]

        return self.llm_service.generate_structured_output(
            messages=messages,
            response_model=AnalysisPlan,
            temperature=0.1
        )

    def _plan_with_heuristics(
        self,
        question: str,
        profile: DatasetProfile,
        conversation_history: Optional[List[Dict[str, str]]]
    ) -> AnalysisPlan:
        q_lower = question.lower()
        
        # Match relevant columns by substring or token
        relevant_cols = []
        for col in profile.columns.keys():
            if col.lower() in q_lower or any(word in col.lower() for word in q_lower.split()):
                relevant_cols.append(col)

        # If none matched, provide best guess based on keywords
        if not relevant_cols:
            if any(k in q_lower for k in ["sales", "revenue", "amount", "price"]):
                relevant_cols += [c for c in profile.numeric_columns if any(k in c.lower() for k in ["sale", "rev", "amount", "price"])]
            if any(k in q_lower for k in ["region", "area", "geo", "state"]):
                relevant_cols += [c for c in profile.categorical_columns if any(k in c.lower() for k in ["region", "state", "area"])]
            if any(k in q_lower for k in ["product", "item", "category"]):
                relevant_cols += [c for c in profile.categorical_columns if any(k in c.lower() for k in ["product", "cat", "item"])]
            if any(k in q_lower for k in ["month", "date", "trend", "year", "time"]):
                relevant_cols += profile.datetime_columns

        # Ensure at least one numeric and one categorical/date if available
        if not relevant_cols:
            if profile.numeric_columns:
                relevant_cols.append(profile.numeric_columns[0])
            if profile.categorical_columns:
                relevant_cols.append(profile.categorical_columns[0])

        relevant_cols = list(dict.fromkeys(relevant_cols))

        # Detect objective
        objective = "descriptive"
        suggested_charts = ["bar"]
        if any(k in q_lower for k in ["trend", "forecast", "future", "predict", "over time"]):
            objective = "predictive" if any(k in q_lower for k in ["forecast", "future", "predict"]) else "descriptive"
            suggested_charts = ["line"]
        elif any(k in q_lower for k in ["why", "compare", "correlation", "relationship", "difference", "versus", "vs"]):
            objective = "diagnostic"
            suggested_charts = ["bar", "scatter"]
        elif any(k in q_lower for k in ["recommend", "improve", "optimize", "action", "strategy"]):
            objective = "prescriptive"
            suggested_charts = ["bar"]

        tasks = [
            AnalysisTask(
                task_id=1,
                title="Data Extraction and Preprocessing",
                description=f"Filter and prepare relevant columns: {', '.join(relevant_cols)}",
                target_columns=relevant_cols,
                method="filtering and validation",
                expected_output="Clean working subset DataFrame"
            ),
            AnalysisTask(
                task_id=2,
                title="Analytical Computation",
                description=f"Compute aggregations and analytical metrics to address: '{question}'",
                target_columns=relevant_cols,
                method="groupby aggregation / statistical calculation",
                expected_output="Computed summary metrics and analytical table"
            ),
            AnalysisTask(
                task_id=3,
                title="Visualization Generation",
                description=f"Generate interactive {suggested_charts[0]} visualization for computed metrics",
                target_columns=relevant_cols,
                method="plotly figure rendering",
                expected_output="Plotly figure dictionary"
            )
        ]

        return AnalysisPlan(
            question=question,
            objective_type=objective,
            primary_goal=f"Answer '{question}' using columns {relevant_cols}",
            relevant_columns=relevant_cols,
            tasks=tasks,
            assumptions=["Data records represent valid transactions", "Null values are handled gracefully"],
            suggested_chart_types=suggested_charts,
            explanation=f"Heuristic plan identifying {objective} analytics across target columns {relevant_cols}."
        )
