"""Agent 9: Visualization Agent."""

import json
import logging
import uuid
from typing import Any, Dict, List, Optional
import plotly.graph_objects as go

from schemas.analysis import AnalysisPlan
from schemas.execution import ExecutionResult
from schemas.report import ChartArtifact
from services.llm_service import LLMService, get_llm_service
from visualization.charts import build_chart_from_table

logger = logging.getLogger(__name__)

VIS_EXPLANATION_PROMPT = """You are the Senior Visualization Agent of an Autonomous Data Analyst AI.
Analyze the provided chart metadata and computed numerical values, and produce:
1. A concise, clear explanation of what the chart illustrates.
2. 2-3 bullet-point insights directly derived from the visual data.

Never fabricate numbers not present in the data.
"""


class VisualizationAgent:
    """Agent that creates, validates, and explains interactive Plotly visualizations."""

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or get_llm_service()

    def generate_visualizations(
        self,
        execution_result: ExecutionResult,
        plan: AnalysisPlan
    ) -> List[ChartArtifact]:
        """Convert execution figures and output tables into explained ChartArtifacts."""
        logger.info(f"VisualizationAgent processing visual outputs for plan: '{plan.primary_goal}'")
        artifacts: List[ChartArtifact] = []

        # 1. Process figures generated directly by the Python script
        for idx, fig_dict in enumerate(execution_result.figures_json):
            chart_id = f"fig_exec_{idx+1}"
            layout = fig_dict.get("layout", {})
            title = layout.get("title", {}).get("text", f"Chart {idx+1}") if isinstance(layout.get("title"), dict) else str(layout.get("title", f"Chart {idx+1}"))
            
            # Detect chart type from data traces
            traces = fig_dict.get("data", [])
            chart_type = traces[0].get("type", "bar") if traces else "bar"

            explanation, insights = self._explain_chart(title, chart_type, execution_result.metrics)

            artifacts.append(ChartArtifact(
                chart_id=chart_id,
                title=title,
                chart_type=chart_type,
                figure_dict=fig_dict,
                explanation=explanation,
                insights=insights
            ))

        # 2. If no direct figures were generated, build charts from output tables
        if not artifacts and execution_result.output_tables:
            for tbl_name, records in execution_result.output_tables.items():
                pref_type = plan.suggested_chart_types[0] if plan.suggested_chart_types else None
                art = build_chart_from_table(
                    table_name=tbl_name,
                    records=records,
                    title=f"{plan.primary_goal}",
                    preferred_type=pref_type
                )
                if art:
                    artifacts.append(art)
                    break

        return artifacts

    def _explain_chart(
        self,
        title: str,
        chart_type: str,
        metrics: Dict[str, Any]
    ) -> tuple[str, List[str]]:
        """Generate interpretation and key takeaways for a chart."""
        if self.llm_service.is_configured:
            try:
                user_msg = (
                    f"Chart Title: {title}\n"
                    f"Chart Type: {chart_type}\n"
                    f"Related Metrics: {json.dumps(metrics, indent=2)}\n"
                    "Provide an explanation and 2 bullet points."
                )
                resp = self.llm_service.generate_chat_completion(
                    messages=[
                        {"role": "system", "content": VIS_EXPLANATION_PROMPT},
                        {"role": "user", "content": user_msg}
                    ],
                    temperature=0.1
                )
                lines = [l.strip().lstrip("-*• ") for l in resp.strip().split("\n") if l.strip()]
                explanation = lines[0] if lines else f"Visualization illustrating {title}."
                insights = lines[1:] if len(lines) > 1 else [f"Highlights distributions and trends in {title}."]
                return explanation, insights
            except Exception:
                pass

        # Heuristic explanation
        explanation = f"This interactive {chart_type} chart illustrates {title.lower()} computed across the dataset."
        insights = [
            f"Visualizes computed metrics: {', '.join(f'{k}={v}' for k, v in list(metrics.items())[:3])}" if metrics else "Displays the calculated distribution.",
            "Enables interactive inspection of outliers and relative category performance."
        ]
        return explanation, insights
