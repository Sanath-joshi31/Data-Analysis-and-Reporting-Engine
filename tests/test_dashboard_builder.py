"""Comprehensive unit and integration tests for the Autonomous Dashboard Builder."""

import tempfile
from pathlib import Path
import pandas as pd
import pytest

from analytics.profiling import profile_dataframe
from dashboard.export import DashboardExporter
from dashboard.filters import apply_dashboard_filters, extract_filter_candidates
from dashboard.generator import DashboardGenerator
from dashboard.planner import DashboardPlanningAgent
from dashboard.specification import DashboardFilterState, DashboardSpecification
from dashboard.validator import DashboardValidator


@pytest.fixture
def sample_dashboard_df():
    """Synthetic retail dataset for dashboard testing."""
    return pd.DataFrame({
        "Order_ID": [f"ORD-{i:03d}" for i in range(1, 13)],
        "Region": ["North", "South", "East", "West"] * 3,
        "Category": ["Technology", "Furniture", "Office Supplies"] * 4,
        "Sales": [1200.0, 450.0, 150.0, 2100.0, 950.0, 300.0, 1400.0, 600.0, 250.0, 3200.0, 1100.0, 400.0],
        "Profit": [240.0, 50.0, 30.0, 420.0, 190.0, -20.0, 280.0, 90.0, 40.0, 640.0, 220.0, 60.0],
        "Order_Date": [
            "2024-01-15", "2024-02-10", "2024-03-05", "2024-04-20",
            "2024-05-12", "2024-06-18", "2024-07-22", "2024-08-14",
            "2024-09-30", "2024-10-15", "2024-11-20", "2024-12-05"
        ]
    })


def test_dashboard_planning_agent(sample_dashboard_df):
    """Verify DashboardPlanningAgent designs multi-section specifications."""
    profile = profile_dataframe(sample_dashboard_df)
    planner = DashboardPlanningAgent()
    spec = planner.plan_dashboard(sample_dashboard_df, profile)

    assert isinstance(spec, DashboardSpecification)
    assert len(spec.global_kpis) >= 2
    assert len(spec.sections) >= 3
    assert any(s.section_id == "sec_exec" for s in spec.sections)
    assert any(s.section_id == "sec_trend" for s in spec.sections)


def test_dashboard_generator(sample_dashboard_df):
    """Verify DashboardGenerator renders Plotly figures and AI explanations."""
    profile = profile_dataframe(sample_dashboard_df)
    planner = DashboardPlanningAgent()
    spec = planner.plan_dashboard(sample_dashboard_df, profile)

    generator = DashboardGenerator()
    generated_spec = generator.generate_dashboard(sample_dashboard_df, spec, profile)

    assert generated_spec is not None
    # Verify charts have rendered figures and explanations
    first_chart = generated_spec.sections[0].charts[0]
    assert len(first_chart.figure_dict) > 0
    assert len(first_chart.table_records) > 0
    assert len(first_chart.explanation) > 0


def test_dashboard_validator(sample_dashboard_df):
    """Verify DashboardValidator passes clean dashboard and flags empty charts."""
    profile = profile_dataframe(sample_dashboard_df)
    planner = DashboardPlanningAgent()
    spec = planner.plan_dashboard(sample_dashboard_df, profile)
    generator = DashboardGenerator()
    generated_spec = generator.generate_dashboard(sample_dashboard_df, spec, profile)

    is_valid, issues = DashboardValidator.validate_dashboard(generated_spec)
    assert is_valid is True
    assert len(issues) == 0


def test_dashboard_filters(sample_dashboard_df):
    """Verify interactive cross-filtering by date and category."""
    profile = profile_dataframe(sample_dashboard_df)
    filters = extract_filter_candidates(sample_dashboard_df, profile)
    assert "Region" in filters
    assert "Category" in filters

    # Apply Region filter
    f_state = DashboardFilterState(selected_categories={"Region": ["North"]})
    filtered = apply_dashboard_filters(sample_dashboard_df, f_state)
    assert len(filtered) == 3
    assert set(filtered["Region"]) == {"North"}


def test_dashboard_exporter_all_formats(sample_dashboard_df, tmp_path):
    """Verify export to HTML, PowerPoint PPTX, Excel, and PDF."""
    profile = profile_dataframe(sample_dashboard_df)
    planner = DashboardPlanningAgent()
    spec = planner.plan_dashboard(sample_dashboard_df, profile)
    generator = DashboardGenerator()
    generated_spec = generator.generate_dashboard(sample_dashboard_df, spec, profile)

    exporter = DashboardExporter(export_dir=tmp_path)

    # 1. HTML Export
    html_path = exporter.export_to_html(generated_spec)
    assert html_path.exists()
    assert html_path.stat().st_size > 500
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "Plotly.newPlot" in content

    # 2. PowerPoint PPTX Export
    pptx_path = exporter.export_to_pptx(generated_spec)
    assert pptx_path.exists()
    assert pptx_path.stat().st_size > 1000

    # 3. Excel Export
    excel_path = exporter.export_to_excel(generated_spec)
    assert excel_path.exists()
    assert excel_path.stat().st_size > 1000

    # 4. PDF Export
    pdf_path = exporter.export_to_pdf(generated_spec)
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 1000
