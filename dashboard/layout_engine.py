"""Dynamic Streamlit Layout Engine for the Autonomous Dashboard Builder."""

import io
from typing import Any, Callable, Dict, Optional
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.specification import ChartSpecification, DashboardSpecification


def render_dashboard_layout(
    spec: DashboardSpecification,
    on_chart_type_change: Optional[Callable[[str, str], None]] = None,
    on_chart_remove: Optional[Callable[[str], None]] = None
):
    """Render the complete interactive dashboard in Streamlit with customization controls."""
    # 1. Executive Summary & KPIs Row
    st.markdown("### 🏆 Executive KPI Metrics")
    kpi_cols = st.columns(min(len(spec.global_kpis), 4))
    for idx, kpi in enumerate(spec.global_kpis[:4]):
        with kpi_cols[idx]:
            st.metric(
                label=f"{kpi.icon} {kpi.label}",
                value=kpi.formatted_value,
                delta=kpi.delta_formatted,
                delta_color="normal" if kpi.delta_positive else "inverse"
            )

    st.markdown("---")

    # 2. Render Each Dashboard Section
    for s_idx, section in enumerate(spec.sections):
        if not section.visible or not section.charts:
            continue

        with st.expander(f"📁 {section.title.upper()}", expanded=True):
            st.caption(section.description)

            # Render charts 2-per-row for clean dashboard density
            num_charts = len(section.charts)
            for i in range(0, num_charts, 2):
                col_left, col_right = st.columns(2)

                # Left Chart
                chart_left = section.charts[i]
                with col_left:
                    _render_interactive_chart_card(
                        chart=chart_left,
                        chart_key=f"chart_left_{s_idx}_{i}",
                        on_chart_type_change=on_chart_type_change,
                        on_chart_remove=on_chart_remove
                    )

                # Right Chart (if exists)
                if i + 1 < num_charts:
                    chart_right = section.charts[i + 1]
                    with col_right:
                        _render_interactive_chart_card(
                            chart=chart_right,
                            chart_key=f"chart_right_{s_idx}_{i+1}",
                            on_chart_type_change=on_chart_type_change,
                            on_chart_remove=on_chart_remove
                        )

            st.markdown("")


def _render_interactive_chart_card(
    chart: ChartSpecification,
    chart_key: str,
    on_chart_type_change: Optional[Callable[[str, str], None]],
    on_chart_remove: Optional[Callable[[str], None]]
):
    """Render a single chart container with header, plot, AI explanation, and interactive tools."""
    st.markdown(f"#### {chart.title}")

    # Plotly Figure
    if chart.figure_dict:
        fig = go.Figure(chart.figure_dict)
        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True, key=f"plot_{chart_key}")

    # AI Generated Explanation
    if chart.explanation:
        st.info(f"💡 **AI Insight**: {chart.explanation}")

    # Action Toolbar & Drill-Down
    with st.expander("🛠️ Chart Controls & Drill-Down Data"):
        col_c1, col_c2 = st.columns([2, 1])

        # Chart Type Switcher
        with col_c1:
            allowed_types = ["bar", "horizontal_bar", "line", "area", "donut", "scatter", "histogram", "box"]
            curr_idx = allowed_types.index(chart.chart_type) if chart.chart_type in allowed_types else 0
            new_type = st.selectbox(
                "Change Visualization Type",
                allowed_types,
                index=curr_idx,
                key=f"type_select_{chart_key}"
            )
            if new_type != chart.chart_type and on_chart_type_change:
                on_chart_type_change(chart.id, new_type)

        # Remove / Hide Button
        with col_c2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("🗑️ Remove", key=f"del_{chart_key}", use_container_width=True):
                if on_chart_remove:
                    on_chart_remove(chart.id)

        # Tabular Drill-Down Preview & CSV Download
        if chart.table_records:
            st.markdown("**Underlying Computed Table:**")
            df_rec = pd.DataFrame(chart.table_records)
            st.dataframe(df_rec.head(10), use_container_width=True)

            csv_buffer = io.StringIO()
            df_rec.to_csv(csv_buffer, index=False)
            st.download_button(
                label="📥 Export Chart CSV",
                data=csv_buffer.getvalue(),
                file_name=f"{chart.id}_data.csv",
                mime="text/csv",
                key=f"dl_csv_{chart_key}"
            )
