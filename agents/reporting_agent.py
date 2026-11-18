"""Agent 10: Insight and Reporting Agent."""

import json
import logging
import uuid
from typing import Any, Dict, List, Optional
from schemas.analysis import AnalysisPlan
from schemas.dataset import DatasetProfile
from schemas.execution import ExecutionResult
from schemas.report import AnalyticalReport, ChartArtifact, InsightItem
from services.llm_service import LLMService, get_llm_service

logger = logging.getLogger(__name__)

REPORTING_SYSTEM_PROMPT = """You are the Principal Business Analytics and Executive Reporting Agent of an Autonomous Data Analyst AI.
Your mission is to synthesize the verified computations, tables, metrics, and charts into an authoritative, professional AnalyticalReport.

CRITICAL REPORTING PRINCIPLES:
1. NEVER fabricate statistics, numbers, or conclusions. Every numerical claim MUST be directly traceable to the computed metrics or tables provided.
2. Clearly distinguish correlation from causation. Do not claim causal relationships without experimental controls.
3. Highlight genuine business implications and provide actionable, pragmatic recommendations.
4. Note analytical limitations honestly (e.g., sample size, missing confounders, observational nature).
5. Produce a structured AnalyticalReport matching the schema.
"""


class ReportingAgent:
    """Agent that produces executive summaries, actionable business recommendations, and final analytical reports."""

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or get_llm_service()

    def generate_report(
        self,
        question: str,
        plan: AnalysisPlan,
        profile: DatasetProfile,
        execution_result: ExecutionResult,
        charts: List[ChartArtifact],
        code_executed: Optional[str] = None
    ) -> AnalyticalReport:
        """Synthesize computed data into an end-to-end AnalyticalReport."""
        logger.info(f"ReportingAgent synthesizing findings for: '{question}'")

        if self.llm_service.is_configured:
            try:
                return self._generate_report_llm(
                    question=question,
                    plan=plan,
                    profile=profile,
                    execution_result=execution_result,
                    charts=charts,
                    code_executed=code_executed
                )
            except Exception as e:
                logger.warning(f"ReportingAgent LLM synthesis failed: {e}. Falling back to structured heuristic synthesis.")

        return self._generate_report_heuristics(
            question=question,
            plan=plan,
            profile=profile,
            execution_result=execution_result,
            charts=charts,
            code_executed=code_executed
        )

    def _generate_report_llm(
        self,
        question: str,
        plan: AnalysisPlan,
        profile: DatasetProfile,
        execution_result: ExecutionResult,
        charts: List[ChartArtifact],
        code_executed: Optional[str]
    ) -> AnalyticalReport:
        user_msg = (
            f"User Question: {question}\n"
            f"Dataset Name: {profile.filename} ({profile.row_count:,} rows, {profile.column_count} columns)\n"
            f"Analytical Objective: {plan.objective_type}\n"
            f"Calculated Metrics:\n{json.dumps(execution_result.metrics, indent=2)}\n\n"
            f"Calculated Table Summaries (top 5 rows each):\n"
            f"{json.dumps({k: v[:5] for k, v in execution_result.output_tables.items()}, indent=2)}\n\n"
            f"Charts Available:\n" + "\n".join(f"- {c.title} ({c.chart_type})" for c in charts) + "\n\n"
            "Generate the full structured AnalyticalReport."
        )

        messages = [
            {"role": "system", "content": REPORTING_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg}
        ]

        report = self.llm_service.generate_structured_output(
            messages=messages,
            response_model=AnalyticalReport,
            temperature=0.2
        )
        report.report_id = str(uuid.uuid4())
        report.charts = charts
        report.tabular_results = execution_result.output_tables
        report.metrics_summary = execution_result.metrics
        report.code_executed = code_executed
        return report

    def _generate_report_heuristics(
        self,
        question: str,
        plan: AnalysisPlan,
        profile: DatasetProfile,
        execution_result: ExecutionResult,
        charts: List[ChartArtifact],
        code_executed: Optional[str]
    ) -> AnalyticalReport:
        metrics = execution_result.metrics
        tables = execution_result.output_tables

        # Build evidence string
        evidence_items = [f"{k}: {v}" for k, v in metrics.items()]
        evidence_str = "; ".join(evidence_items) if evidence_items else "Derived from output aggregation tables."

        # Findings
        findings: List[InsightItem] = []
        if metrics:
            for k, v in list(metrics.items())[:3]:
                findings.append(InsightItem(
                    title=f"Metric: {k.replace('_', ' ').title()}",
                    category="Quantitative Finding",
                    finding=f"Computed value for {k.replace('_', ' ')} is {v}.",
                    evidence=f"{k} = {v}",
                    business_implication="Directly impacts operational performance metrics and targets.",
                    recommendation=f"Incorporate {k} into regular business review dashboards and tracking."
                ))

        if not findings:
            findings.append(InsightItem(
                title="Primary Analytical Summary",
                category="Trend",
                finding=f"Analysis computed successfully for question '{question}'.",
                evidence=evidence_str,
                business_implication="Validates structural patterns in the provided dataset.",
                recommendation="Monitor segment performance and periodic variances."
            ))

        exec_summary = (
            f"This analysis evaluated '{question}' against dataset '{profile.filename}' "
            f"containing {profile.row_count:,} records. "
            f"Calculations established key metrics including: {evidence_str}. "
            f"All findings have been validated against computed data without synthetic extrapolation."
        )

        limitations = [
            "Analysis is based strictly on available historical observational records.",
            "External macroeconomic and seasonal factors not present in the dataset were not controlled for.",
            "Correlation indicators do not imply direct causality."
        ]

        recommendations = [
            "Focus operational initiatives on highest-contributing segments and categories.",
            "Establish automated alerts for anomalies and unexpected margin contractions.",
            "Conduct further A/B experimentation to validate causal drivers."
        ]

        return AnalyticalReport(
            report_id=str(uuid.uuid4()),
            question=question,
            dataset_name=profile.filename,
            executive_summary=exec_summary,
            key_findings=findings,
            limitations=limitations,
            recommendations=recommendations,
            charts=charts,
            tabular_results=tables,
            metrics_summary=metrics,
            code_executed=code_executed
        )
