"""Benchmark test suite measuring accuracy against 10 explicit analytical requirements."""

import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from analytics.anomaly import detect_anomalies_iqr
from analytics.descriptive import compute_correlation_matrix
from analytics.profiling import profile_dataframe
from graph.workflow import AnalysisWorkflowManager
from sandbox.secure_subprocess_executor import SecureSubprocessExecutor


@pytest.fixture(scope="module")
def benchmark_dataset():
    """Deterministic ground-truth dataset with known aggregations and defects."""
    data = {
        "Order_ID": [f"ORD-{i:03d}" for i in range(1, 11)] + ["ORD-001"],  # 1 duplicate row
        "Region": ["North", "North", "South", "South", "East", "East", "West", "West", "North", "South", "North"],
        "Category": ["Technology", "Furniture", "Technology", "Office", "Furniture", "Technology", "Office", "Technology", "Furniture", "Office", "Technology"],
        "Sales": [100.0, 200.0, 300.0, 400.0, 500.0, 150.0, 250.0, 350.0, 450.0, 550.0, 100.0],
        "Profit": [20.0, 40.0, 60.0, 80.0, 100.0, 30.0, 50.0, 70.0, 90.0, 110.0, 20.0],
        "Quantity": [1, 2, 3, 4, 5, 2, 3, 4, 5, 6, 1],
        "Order_Date": [
            "2024-01-10", "2024-01-20", "2024-02-05", "2024-02-15",
            "2024-03-01", "2024-03-25", "2024-04-10", "2024-04-20",
            "2024-05-05", "2024-05-15", "2024-01-10"
        ],
        "Discount": [0.0, 0.1, 0.2, 0.0, 0.1, 0.0, 0.2, 0.1, 0.0, 0.3, 0.0]
    }
    df = pd.DataFrame(data)
    # Add an outlier
    df.loc[11] = ["ORD-011", "South", "Technology", 9500.0, 1900.0, 10, "2024-06-01", 0.0]
    # Add a null entry
    df.loc[12] = ["ORD-012", "East", "Office", np.nan, 10.0, 1, "2024-06-15", 0.0]

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        df.to_csv(f.name, index=False)
        path = f.name

    yield path, df
    Path(path).unlink(missing_ok=True)


def test_benchmark_1_simple_aggregation(benchmark_dataset):
    """Benchmark 1: Simple aggregation (sum, mean)."""
    path, df = benchmark_dataset
    mgr = AnalysisWorkflowManager()
    state = mgr.run_analysis(question="What is the total sales revenue?", dataset_path=path, dataset_id="bm_1")

    assert state["is_complete"] is True
    res = state["execution_result"]
    assert res.success is True
    metrics = res.metrics
    expected_sum = float(round(df["Sales"].dropna().sum(), 2))
    # Check metric is computed
    metric_val = next((v for k, v in metrics.items() if "total" in k or "sum" in k or "sale" in k), None)
    assert metric_val is not None
    assert abs(metric_val - expected_sum) < 1.0


def test_benchmark_2_group_by_analysis(benchmark_dataset):
    """Benchmark 2: Group-by ranking (highest revenue region)."""
    path, df = benchmark_dataset
    mgr = AnalysisWorkflowManager()
    state = mgr.run_analysis(question="Which region performs best by total sales?", dataset_path=path, dataset_id="bm_2")

    res = state["execution_result"]
    assert res.success is True
    # South has the 9500 outlier and highest total
    assert "segment_comparison" in res.output_tables or len(res.output_tables) > 0
    top_region = res.metrics.get("top_segment", "")
    assert top_region == "South"


def test_benchmark_3_date_based_trends(benchmark_dataset):
    """Benchmark 3: Date-based monthly trend calculation."""
    path, df = benchmark_dataset
    mgr = AnalysisWorkflowManager()
    state = mgr.run_analysis(question="Show monthly sales trends.", dataset_path=path, dataset_id="bm_3")

    res = state["execution_result"]
    assert res.success is True
    assert "monthly_trend" in res.output_tables or len(res.output_tables) > 0


def test_benchmark_4_missing_value_detection(benchmark_dataset):
    """Benchmark 4: Missing value detection."""
    _, df = benchmark_dataset
    profile = profile_dataframe(df)
    assert profile.columns["Sales"].missing_count == 1
    assert profile.total_missing_cells == 1


def test_benchmark_5_duplicate_detection(benchmark_dataset):
    """Benchmark 5: Duplicate row detection."""
    _, df = benchmark_dataset
    profile = profile_dataframe(df)
    assert profile.duplicate_rows_count >= 1


def test_benchmark_6_correlation_analysis(benchmark_dataset):
    """Benchmark 6: Correlation between Sales and Profit."""
    _, df = benchmark_dataset
    corr_res = compute_correlation_matrix(df, ["Sales", "Profit"])
    assert "matrix" in corr_res
    r = corr_res["matrix"]["Sales"]["Profit"]
    assert r > 0.8  # Strong positive correlation


def test_benchmark_7_outlier_analysis(benchmark_dataset):
    """Benchmark 7: Outlier analysis via IQR."""
    _, df = benchmark_dataset
    outliers = detect_anomalies_iqr(df, "Sales")
    assert outliers["outliers_count"] >= 1
    assert any(o["Sales"] == 9500.0 for o in outliers["top_outliers"])


def test_benchmark_8_multi_step_analysis(benchmark_dataset):
    """Benchmark 8: Multi-step filtering and ranking."""
    path, _ = benchmark_dataset
    mgr = AnalysisWorkflowManager()
    state = mgr.run_analysis(question="Find the top 5 products by sales.", dataset_path=path, dataset_id="bm_8")

    res = state["execution_result"]
    assert res.success is True
    assert len(res.figures_json) > 0 or len(state["charts"]) > 0


def test_benchmark_9_invalid_code_correction(benchmark_dataset):
    """Benchmark 9: Self-correcting loop when code references invalid column."""
    path, df = benchmark_dataset
    mgr = AnalysisWorkflowManager()

    # Artificially test error agent on misspelled column
    error_agent = mgr.error_agent
    failed_code = "df_agg = df.groupby('region_typo')['Sales'].sum()"
    exec_res = SecureSubprocessExecutor().execute(failed_code, path)
    diagnosis = error_agent.diagnose_and_correct(1, failed_code, exec_res, profile_dataframe(df))

    assert diagnosis.error_type == "KeyError"
    assert "Region" in diagnosis.corrected_code


def test_benchmark_10_follow_up_conversational(benchmark_dataset):
    """Benchmark 10: Follow-up question maintaining session context."""
    path, _ = benchmark_dataset
    mgr = AnalysisWorkflowManager()

    history = [
        {"role": "user", "content": "Which region generated the highest revenue?"},
        {"role": "assistant", "content": "The South region generated the highest revenue with $10,750."}
    ]

    state = mgr.run_analysis(
        question="Show its monthly trend.",
        dataset_path=path,
        dataset_id="bm_10",
        conversation_history=history
    )

    assert state["is_complete"] is True
    assert state["execution_result"].success is True
    assert state["final_report"] is not None
