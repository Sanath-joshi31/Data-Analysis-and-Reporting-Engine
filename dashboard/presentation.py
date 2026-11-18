"""Full-screen Presentation Mode renderer for executive dashboards."""

import plotly.graph_objects as go
import streamlit as st
from dashboard.specification import DashboardSpecification


def render_presentation_mode(spec: DashboardSpecification):
    """Render a clean, distraction-free executive presentation deck."""
    st.markdown("""
    <style>
        .presentation-banner {
            background: linear-gradient(135deg, #1E3A8A, #0284C7);
            color: white;
            padding: 24px;
            border-radius: 12px;
            margin-bottom: 24px;
            text-align: center;
        }
        .pres-kpi-card {
            background: #F8FAFC;
            border: 2px solid #E2E8F0;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        }
        .pres-kpi-val {
            font-size: 32px;
            font-weight: 800;
            color: #1E3A8A;
        }
        .pres-kpi-lbl {
            font-size: 14px;
            font-weight: 600;
            color: #64748B;
            text-transform: uppercase;
        }
    </style>
    """, unsafe_allow_html=True)

    # Presentation Header Banner
    st.markdown(f"""
    <div class="presentation-banner">
        <h1 style="margin: 0; font-size: 32px;">{spec.title}</h1>
        <p style="margin: 8px 0 0 0; opacity: 0.9;">Dataset: <b>{spec.dataset_name}</b> | Executive Presentation Mode</p>
    </div>
    """, unsafe_allow_html=True)

    # Global KPI Row
    st.markdown("### 🏆 Executive Performance Indicators")
    kpi_cols = st.columns(min(len(spec.global_kpis), 4))
    for idx, kpi in enumerate(spec.global_kpis[:4]):
        with kpi_cols[idx]:
            st.markdown(f"""
            <div class="pres-kpi-card">
                <div class="pres-kpi-lbl">{kpi.icon} {kpi.label}</div>
                <div class="pres-kpi-val">{kpi.formatted_value}</div>
                <div style="font-size: 12px; color: #16A34A; font-weight: 600;">{kpi.delta_formatted or ""}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # Section Navigation Tabs for Slide-by-Slide Viewing
    section_titles = [f"📌 {sec.title}" for sec in spec.sections if sec.visible]
    section_titles.append("💡 AI Executive Insights")

    pres_tabs = st.tabs(section_titles)

    for s_idx, sec in enumerate([s for s in spec.sections if s.visible]):
        with pres_tabs[s_idx]:
            st.markdown(f"## {sec.title}")
            st.markdown(f"*{sec.description}*")
            st.markdown("")

            # Render charts side by side or stacked depending on count
            if len(sec.charts) == 1:
                chart = sec.charts[0]
                st.markdown(f"### {chart.title}")
                fig = go.Figure(chart.figure_dict)
                fig.update_layout(height=520)
                st.plotly_chart(fig, use_container_width=True, key=f"pres_fig_{chart.id}_{s_idx}")
                st.info(f"**Insight:** {chart.explanation}")
            else:
                for c_idx, chart in enumerate(sec.charts):
                    st.markdown(f"### {chart.title}")
                    fig = go.Figure(chart.figure_dict)
                    fig.update_layout(height=450)
                    st.plotly_chart(fig, use_container_width=True, key=f"pres_fig_{chart.id}_{s_idx}_{c_idx}")
                    st.info(f"**Takeaway:** {chart.explanation}")
                    if chart.insights:
                        for ins in chart.insights:
                            st.markdown(f"- {ins}")
                    st.markdown("---")

    # Final Tab: Executive Narrative & Actionable Recommendations
    with pres_tabs[-1]:
        st.markdown("## 📋 Executive Strategic Narrative")
        st.markdown(f"> **Summary**: {spec.executive_summary}")

        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown("### 🔍 Key Empirical Findings")
            for f in spec.key_findings:
                st.markdown(f"- **{f}**")

            st.markdown("### ⚠️ Operational Risks")
            for r in spec.risks:
                st.markdown(f"- 🔴 {r}")

        with col_right:
            st.markdown("### 🚀 Strategic Growth Recommendations")
            for rec in spec.recommendations:
                st.markdown(f"✅ **{rec}**")

            st.markdown("### 🌟 Growth Opportunities")
            for opp in spec.opportunities:
                st.markdown(f"- 🟢 {opp}")
