"""Quality, mathematical integrity, and visual sanity validation for generated dashboards."""

import logging
from typing import List, Tuple
from dashboard.specification import ChartSpecification, DashboardSpecification

logger = logging.getLogger(__name__)


class DashboardValidator:
    """Validates that a generated dashboard is mathematically sound, non-empty, and free of misleading charts."""

    @classmethod
    def validate_dashboard(cls, spec: DashboardSpecification) -> Tuple[bool, List[str]]:
        """Perform comprehensive visual and numerical audit of the dashboard specification."""
        issues: List[str] = []

        # 1. Check Global KPIs
        if not spec.global_kpis:
            issues.append("Dashboard contains no executive KPI metrics.")
        for kpi in spec.global_kpis:
            if kpi.value is None:
                issues.append(f"KPI '{kpi.label}' computed value is None.")

        # 2. Check Sections & Charts
        total_charts = 0
        seen_chart_ids = set()
        seen_titles = set()

        for section in spec.sections:
            if not section.visible:
                continue

            for chart in section.charts:
                total_charts += 1

                # Check unique ID
                if chart.id in seen_chart_ids:
                    issues.append(f"Duplicate chart ID detected: '{chart.id}'.")
                seen_chart_ids.add(chart.id)

                # Check duplicate chart titles
                if chart.title in seen_titles:
                    issues.append(f"Duplicate visualization title detected: '{chart.title}'.")
                seen_titles.add(chart.title)

                # Check that chart has computed data records
                if not chart.table_records and not chart.figure_dict:
                    issues.append(f"Chart '{chart.title}' contains empty data records and empty figure.")

                # Check misleading chart selections
                if chart.chart_type in ["pie", "donut"] and len(chart.table_records) > 8:
                    issues.append(
                        f"Misleading chart design: Donut/Pie chart '{chart.title}' contains {len(chart.table_records)} slices (exceeds recommended max of 8)."
                    )

                # Check figure dictionary
                if not chart.figure_dict:
                    issues.append(f"Chart '{chart.title}' is missing rendered Plotly figure dictionary.")

        if total_charts == 0:
            issues.append("Dashboard specification contains 0 total charts.")

        is_valid = len(issues) == 0
        if not is_valid:
            logger.warning(f"Dashboard quality validation flagged {len(issues)} issues:\n" + "\n".join(f"- {i}" for i in issues))
        else:
            logger.info("Dashboard quality validation passed successfully with 0 defects.")

        return is_valid, issues
