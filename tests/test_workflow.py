"""Integration tests for the LangGraph Autonomous Analyst pipeline."""

import tempfile
from pathlib import Path
import pandas as pd
import pytest

from graph.workflow import AnalysisWorkflowManager
from reporting.pdf_report import PDFReportGenerator
from reporting.excel_report import ExcelReportGenerator


@pytest.fixture
def retail_test_csv():
    df = pd.DataFrame({
        "Region": ["North", "South", "East", "West", "North", "South"],
        "Category": ["Technology", "Furniture", "Office Supplies", "Technology", "Furniture", "Technology"],
        "Sales": [1500.0, 3200.0, 450.0, 2100.0, 800.0, 4100.0],
        "Profit": [300.0, 650.0, 45.0, 420.0, -50.0, 920.0],
        "Order_Date": ["2024-01-15", "2024-02-20", "2024-03-10", "2024-04-05", "2024-05-12", "2024-06-18"]
    })
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        df.to_csv(f.name, index=False)
        p = f.name
    yield p
    Path(p).unlink(missing_ok=True)


def test_full_autonomous_workflow_execution(retail_test_csv):
    """Run full LangGraph multi-agent pipeline from user question to report."""
    workflow = AnalysisWorkflowManager()

    final_state = workflow.run_analysis(
        question="Which region generated the highest sales?",
        dataset_path=retail_test_csv,
        dataset_id="test_run_001"
    )

    assert final_state["is_complete"] is True
    assert final_state["dataset_profile"] is not None
    assert final_state["analysis_plan"] is not None
    assert final_state["execution_result"] is not None
    assert final_state["execution_result"].success is True
    assert final_state["final_report"] is not None

    report = final_state["final_report"]
    assert len(report.key_findings) > 0
    assert len(report.recommendations) > 0


def test_conversational_follow_up(retail_test_csv):
    """Verify workflow preserves context across follow-up queries."""
    workflow = AnalysisWorkflowManager()

    history = [
        {"role": "user", "content": "Which region generated the highest revenue?"},
        {"role": "assistant", "content": "The South region generated the highest revenue."}
    ]

    final_state = workflow.run_analysis(
        question="Show its monthly trend.",
        dataset_path=retail_test_csv,
        dataset_id="test_run_002",
        conversation_history=history
    )

    assert final_state["is_complete"] is True
    assert final_state["execution_result"].success is True


def test_report_exporters(retail_test_csv, tmp_path):
    """Verify PDF and Excel report generation exports files to disk."""
    workflow = AnalysisWorkflowManager()
    final_state = workflow.run_analysis(
        question="What is the total sales by category?",
        dataset_path=retail_test_csv,
        dataset_id="test_export"
    )

    report = final_state["final_report"]

    pdf_gen = PDFReportGenerator(output_dir=tmp_path)
    pdf_path = pdf_gen.generate(report)
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0

    excel_gen = ExcelReportGenerator(output_dir=tmp_path)
    excel_path = excel_gen.generate(report)
    assert excel_path.exists()
    assert excel_path.stat().st_size > 0
