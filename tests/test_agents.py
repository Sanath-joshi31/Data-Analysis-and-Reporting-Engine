"""Unit tests for individual specialized agents."""

import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from agents.analyst_agent import AnalystAgent
from agents.cleaning_agent import CleaningAgent
from agents.code_agent import CodeAgent
from agents.error_agent import ErrorAgent
from agents.planner_agent import PlanningAgent
from agents.profiler_agent import DatasetProfilerAgent
from agents.reporting_agent import ReportingAgent
from agents.validation_agent import ValidationAgent
from agents.visualization_agent import VisualizationAgent
from schemas.analysis import AnalysisPlan, AnalysisTask
from schemas.dataset import DatasetProfile
from schemas.execution import ExecutionResult


@pytest.fixture
def mock_dataset_profile():
    return DatasetProfile(
        dataset_id="test_profile_id",
        filename="sales_test.csv",
        row_count=100,
        column_count=3,
        numeric_columns=["Sales", "Profit"],
        categorical_columns=["Region"],
        datetime_columns=[],
        text_columns=[],
        total_missing_cells=0,
        total_missing_percentage=0.0,
        duplicate_rows_count=0,
        duplicate_rows_percentage=0.0,
        health_score=100.0,
        summary="Clean test dataset."
    )


def test_planning_agent_objective_detection(mock_dataset_profile):
    """Verify PlanningAgent generates structured AnalysisPlan with subtasks."""
    planner = PlanningAgent()
    plan = planner.run(
        question="Which region generated the highest revenue?",
        profile=mock_dataset_profile
    )

    assert isinstance(plan, AnalysisPlan)
    assert len(plan.tasks) >= 2
    assert "Region" in plan.relevant_columns or "Sales" in plan.relevant_columns
    assert len(plan.suggested_chart_types) > 0


def test_code_agent_generation(mock_dataset_profile):
    """Verify CodeAgent writes valid Python script referencing known columns."""
    planner = PlanningAgent()
    plan = planner.run("Which region generated the highest sales?", mock_dataset_profile)

    code_agent = CodeAgent()
    code = code_agent.generate_code(plan=plan, profile=mock_dataset_profile)

    assert "df" in code
    assert "OUTPUT" in code
    assert "Region" in code or "Sales" in code


def test_error_agent_diagnosis_and_repair(mock_dataset_profile):
    """Verify ErrorAgent diagnoses KeyError and repairs column names."""
    error_agent = ErrorAgent()
    failed_code = "total = df['revenue'].sum()"
    exec_result = ExecutionResult(
        success=False,
        stderr="KeyError: 'revenue'",
        return_code=1
    )

    diagnosis = error_agent.diagnose_and_correct(
        attempt_number=1,
        failed_code=failed_code,
        execution_result=exec_result,
        profile=mock_dataset_profile
    )

    assert diagnosis.error_type == "KeyError"
    assert diagnosis.corrected_code is not None
    assert diagnosis.attempt_number == 1


def test_validation_agent_empty_output_rejection(mock_dataset_profile):
    """Verify ValidationAgent rejects empty outputs."""
    val_agent = ValidationAgent()
    plan = AnalysisPlan(
        question="What is total sales?",
        primary_goal="Calculate total sales",
        tasks=[]
    )
    empty_result = ExecutionResult(
        success=True,
        output_tables={},
        metrics={},
        figures_json=[]
    )

    validation = val_agent.validate(empty_result, plan, mock_dataset_profile)
    assert validation.is_valid is False
    assert len(validation.flagged_issues) > 0


def test_reporting_agent_generation(mock_dataset_profile):
    """Verify ReportingAgent produces AnalyticalReport with evidence and recommendations."""
    reporter = ReportingAgent()
    plan = AnalysisPlan(question="What is total sales?", primary_goal="Total sales", tasks=[])
    exec_result = ExecutionResult(
        success=True,
        metrics={"total_sales": 250000.0},
        output_tables={"summary": [{"Region": "North", "Sales": 250000.0}]}
    )

    report = reporter.generate_report(
        question="What is total sales?",
        plan=plan,
        profile=mock_dataset_profile,
        execution_result=exec_result,
        charts=[]
    )

    assert report.question == "What is total sales?"
    assert len(report.key_findings) > 0
    assert len(report.recommendations) > 0
    assert report.metrics_summary["total_sales"] == 250000.0
