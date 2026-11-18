"""Unit tests for isolated sandbox code execution."""

import sys
import tempfile
from pathlib import Path
import pandas as pd
import pytest

from sandbox.secure_subprocess_executor import SecureSubprocessExecutor
from schemas.execution import ExecutionResult


@pytest.fixture
def temp_csv_file():
    df = pd.DataFrame({
        "Product": ["Laptop", "Mouse", "Keyboard"],
        "Sales": [1200.0, 25.0, 75.0],
        "Quantity": [2, 10, 5]
    })
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        df.to_csv(f.name, index=False)
        p = f.name
    yield p
    Path(p).unlink(missing_ok=True)


def test_successful_sandbox_execution(temp_csv_file):
    """Verify clean Python code executes and exports structured tables, metrics, and figures."""
    executor = SecureSubprocessExecutor(timeout_seconds=15)
    code = """
summary = df.groupby('Product')['Sales'].sum().reset_index()
OUTPUT['tables']['sales_by_product'] = summary
OUTPUT['metrics']['total_sales'] = float(summary['Sales'].sum())
OUTPUT['metrics']['product_count'] = int(len(summary))
"""
    result = executor.execute(code, temp_csv_file)

    assert isinstance(result, ExecutionResult)
    assert result.success is True
    assert result.return_code == 0
    assert "sales_by_product" in result.output_tables
    assert len(result.output_tables["sales_by_product"]) == 3
    assert result.metrics["total_sales"] == 1300.0
    assert result.metrics["product_count"] == 3


def test_sandbox_timeout_enforcement(temp_csv_file):
    """Verify an infinite loop is killed cleanly within timeout limit."""
    executor = SecureSubprocessExecutor(timeout_seconds=2)
    infinite_loop_code = """
import time
while True:
    time.sleep(0.1)
"""
    result = executor.execute(infinite_loop_code, temp_csv_file)

    assert result.success is False
    assert result.error == "TimeoutExpired"
    assert "timed out" in result.stderr.lower()


def test_sandbox_exception_handling(temp_csv_file):
    """Verify runtime exception is captured with full traceback."""
    executor = SecureSubprocessExecutor(timeout_seconds=10)
    broken_code = """
# Referencing non-existent column
val = df['NonExistentColumn'].sum()
"""
    result = executor.execute(broken_code, temp_csv_file)

    assert result.success is False
    assert result.return_code != 0
    assert "KeyError" in result.stderr
