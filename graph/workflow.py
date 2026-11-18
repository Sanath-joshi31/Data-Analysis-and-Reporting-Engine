"""LangGraph workflow definition for the Autonomous Data Analyst AI."""

import logging
from typing import Any, Dict, Optional
from langgraph.graph import END, START, StateGraph

from agents.analyst_agent import AnalystAgent
from agents.cleaning_agent import CleaningAgent
from agents.code_agent import CodeAgent
from agents.error_agent import ErrorAgent
from agents.execution_agent import ExecutionAgent
from agents.planner_agent import PlanningAgent
from agents.profiler_agent import DatasetProfilerAgent
from agents.reporting_agent import ReportingAgent
from agents.validation_agent import ValidationAgent
from agents.visualization_agent import VisualizationAgent
from config.settings import get_settings
from graph.routing import route_after_execution, route_after_validation
from graph.state import AnalystWorkflowState
from schemas.dataset import DatasetProfile

logger = logging.getLogger(__name__)


class AnalysisWorkflowManager:
    """Manages the instantiation, compilation, and execution of the multi-agent LangGraph workflow."""

    def __init__(self):
        self.settings = get_settings()

        # Instantiate all 10 specialized agents
        self.profiler_agent = DatasetProfilerAgent()
        self.cleaning_agent = CleaningAgent()
        self.planner_agent = PlanningAgent()
        self.analyst_agent = AnalystAgent()
        self.code_agent = CodeAgent()
        self.execution_agent = ExecutionAgent()
        self.error_agent = ErrorAgent()
        self.validation_agent = ValidationAgent()
        self.visualization_agent = VisualizationAgent()
        self.reporting_agent = ReportingAgent()

        self.workflow = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(AnalystWorkflowState)

        # Register nodes
        graph.add_node("profile_dataset", self._node_profile_dataset)
        graph.add_node("quality_check", self._node_quality_check)
        graph.add_node("plan_analysis", self._node_plan_analysis)
        graph.add_node("analyst_spec", self._node_analyst_spec)
        graph.add_node("generate_code", self._node_generate_code)
        graph.add_node("execute_code", self._node_execute_code)
        graph.add_node("diagnose_error", self._node_diagnose_error)
        graph.add_node("validate_results", self._node_validate_results)
        graph.add_node("generate_visualizations", self._node_generate_visualizations)
        graph.add_node("generate_report", self._node_generate_report)

        # Base linear edges
        graph.add_edge(START, "profile_dataset")
        graph.add_edge("profile_dataset", "quality_check")
        graph.add_edge("quality_check", "plan_analysis")
        graph.add_edge("plan_analysis", "analyst_spec")
        graph.add_edge("analyst_spec", "generate_code")
        graph.add_edge("generate_code", "execute_code")

        # Conditional branching after code execution
        graph.add_conditional_edges(
            "execute_code",
            route_after_execution,
            {
                "validate_results": "validate_results",
                "diagnose_error": "diagnose_error",
                "generate_report": "generate_report"
            }
        )

        # Loop from diagnosis back to code generation
        graph.add_edge("diagnose_error", "generate_code")

        # Conditional branching after validation
        graph.add_conditional_edges(
            "validate_results",
            route_after_validation,
            {
                "generate_visualizations": "generate_visualizations",
                "regenerate_code": "generate_code",
                "generate_report": "generate_report"
            }
        )

        graph.add_edge("generate_visualizations", "generate_report")
        graph.add_edge("generate_report", END)

        return graph.compile()

    # --- Node Callbacks ---

    def _node_profile_dataset(self, state: AnalystWorkflowState) -> Dict[str, Any]:
        logger.info("--- [Node: Profile Dataset] ---")
        profile = state.get("dataset_profile")
        dataset_path = state["dataset_path"]

        if not profile:
            profile = self.profiler_agent.run(file_path_or_df=dataset_path)

        return {
            "dataset_profile": profile,
            "current_step": "profile_dataset",
            "status_message": f"Dataset profile ready: {profile.row_count:,} rows, {profile.column_count} columns."
        }

    def _node_quality_check(self, state: AnalystWorkflowState) -> Dict[str, Any]:
        logger.info("--- [Node: Quality Check] ---")
        profile = state["dataset_profile"]
        # Generate proposed actions
        return {
            "current_step": "quality_check",
            "status_message": f"Data quality assessed. Health score: {profile.health_score}/100."
        }

    def _node_plan_analysis(self, state: AnalystWorkflowState) -> Dict[str, Any]:
        logger.info("--- [Node: Plan Analysis] ---")
        question = state["question"]
        profile = state["dataset_profile"]
        history = state.get("conversation_history", [])

        plan = self.planner_agent.run(
            question=question,
            profile=profile,
            conversation_history=history
        )

        return {
            "analysis_plan": plan,
            "current_step": "plan_analysis",
            "status_message": f"Formulated {plan.objective_type} analysis plan: '{plan.primary_goal}'."
        }

    def _node_analyst_spec(self, state: AnalystWorkflowState) -> Dict[str, Any]:
        logger.info("--- [Node: Analyst Specification] ---")
        plan = state["analysis_plan"]
        profile = state["dataset_profile"]

        spec = self.analyst_agent.formulate_specification(plan=plan, profile=profile)
        return {
            "analyst_specification": spec,
            "current_step": "analyst_spec",
            "status_message": "Mathematical specifications prepared."
        }

    def _node_generate_code(self, state: AnalystWorkflowState) -> Dict[str, Any]:
        logger.info("--- [Node: Generate Code] ---")
        plan = state["analysis_plan"]
        profile = state["dataset_profile"]
        spec = state.get("analyst_specification")
        errors = state.get("error_diagnoses", [])

        # Check if the last diagnosis already produced corrected code
        if errors and errors[-1].corrected_code:
            code = errors[-1].corrected_code
        else:
            code = self.code_agent.generate_code(
                plan=plan,
                profile=profile,
                specification=spec,
                previous_errors=errors
            )

        return {
            "generated_code": code,
            "current_step": "generate_code",
            "status_message": f"Generated Python analysis code (Attempt {len(errors) + 1})."
        }

    def _node_execute_code(self, state: AnalystWorkflowState) -> Dict[str, Any]:
        logger.info("--- [Node: Execute Code] ---")
        code = state["generated_code"]
        dataset_path = state["dataset_path"]
        retry_count = state.get("retry_count", 0)

        result = self.execution_agent.run(code=code, dataset_path=dataset_path)

        return {
            "execution_result": result,
            "retry_count": retry_count + 1,
            "current_step": "execute_code",
            "status_message": "Executed code inside isolated execution environment."
        }

    def _node_diagnose_error(self, state: AnalystWorkflowState) -> Dict[str, Any]:
        logger.info("--- [Node: Diagnose Error] ---")
        code = state["generated_code"]
        result = state["execution_result"]
        profile = state["dataset_profile"]
        errors = list(state.get("error_diagnoses", []))
        attempt = state.get("retry_count", 1)

        diagnosis = self.error_agent.diagnose_and_correct(
            attempt_number=attempt,
            failed_code=code,
            execution_result=result,
            profile=profile
        )
        errors.append(diagnosis)

        return {
            "error_diagnoses": errors,
            "current_step": "diagnose_error",
            "status_message": f"Diagnosed {diagnosis.error_type}. Formulating correction."
        }

    def _node_validate_results(self, state: AnalystWorkflowState) -> Dict[str, Any]:
        logger.info("--- [Node: Validate Results] ---")
        exec_res = state["execution_result"]
        plan = state["analysis_plan"]
        profile = state["dataset_profile"]

        validation = self.validation_agent.validate(
            execution_result=exec_res,
            plan=plan,
            profile=profile
        )

        return {
            "validation_result": validation,
            "current_step": "validate_results",
            "status_message": f"Results validated: {validation.feedback}"
        }

    def _node_generate_visualizations(self, state: AnalystWorkflowState) -> Dict[str, Any]:
        logger.info("--- [Node: Generate Visualizations] ---")
        exec_res = state["execution_result"]
        plan = state["analysis_plan"]

        charts = self.visualization_agent.generate_visualizations(
            execution_result=exec_res,
            plan=plan
        )

        return {
            "charts": charts,
            "current_step": "generate_visualizations",
            "status_message": f"Rendered {len(charts)} interactive Plotly charts."
        }

    def _node_generate_report(self, state: AnalystWorkflowState) -> Dict[str, Any]:
        logger.info("--- [Node: Generate Report] ---")
        question = state["question"]
        plan = state.get("analysis_plan")
        profile = state["dataset_profile"]
        exec_res = state.get("execution_result")
        charts = state.get("charts", [])
        code = state.get("generated_code")

        report = self.reporting_agent.generate_report(
            question=question,
            plan=plan,
            profile=profile,
            execution_result=exec_res,
            charts=charts,
            code_executed=code
        )

        return {
            "final_report": report,
            "is_complete": True,
            "current_step": "generate_report",
            "status_message": "Autonomous analysis and executive report completed."
        }

    def run_analysis(
        self,
        question: str,
        dataset_path: str,
        dataset_id: str,
        dataset_profile: Optional[DatasetProfile] = None,
        conversation_history: Optional[list] = None
    ) -> AnalystWorkflowState:
        """Run the full autonomous multi-agent pipeline."""
        initial_state: AnalystWorkflowState = {
            "question": question,
            "dataset_id": dataset_id,
            "dataset_path": dataset_path,
            "conversation_history": conversation_history or [],
            "dataset_profile": dataset_profile,
            "error_diagnoses": [],
            "retry_count": 0,
            "max_retries": self.settings.max_correction_retries,
            "charts": [],
            "is_complete": False,
            "status_message": "Starting autonomous analysis workflow..."
        }

        final_state = self.workflow.invoke(initial_state)
        return final_state
