"""AUTONOMOUS DATA ANALYST AI - STREAMLIT APPLICATION

A modular, enterprise-grade Autonomous Data Analyst AI application.
Features:
- Dataset upload (CSV, Excel, JSON, Parquet) & Sample Superstore loader
- Multi-agent LangGraph autonomous execution workflow
- Isolated secure code sandbox
- Interactive Plotly visualizations
- Mathematical result validation & self-correction
- Multi-format report export (PDF, Excel, CSV)
"""

import io
import json
import logging
import os
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics.cleaning import apply_cleaning_actions, generate_cleaning_proposals
from analytics.descriptive import compute_descriptive_stats
from analytics.profiling import load_dataset
from config.settings import get_settings
from dashboard import (
    DashboardExporter,
    DashboardFilterState,
    DashboardGenerator,
    DashboardPlanningAgent,
    apply_dashboard_filters,
    render_dashboard_layout,
    render_presentation_mode,
)
from graph.workflow import AnalysisWorkflowManager
from reporting.excel_report import ExcelReportGenerator
from reporting.pdf_report import PDFReportGenerator
from services.dataset_service import DatasetService
from services.session_service import SessionService

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("app")

# Page Configuration
st.set_page_config(
    page_title="Autonomous Data Analyst AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for polished enterprise look
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #475569;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_services():
    settings = get_settings()
    dataset_svc = DatasetService()
    session_svc = SessionService()
    workflow_mgr = AnalysisWorkflowManager()
    pdf_gen = PDFReportGenerator(settings.reports_path)
    excel_gen = ExcelReportGenerator(settings.reports_path)
    return dataset_svc, session_svc, workflow_mgr, pdf_gen, excel_gen


dataset_svc, session_svc, workflow_mgr, pdf_gen, excel_gen = get_services()

# Initialize session state
if "dataset_id" not in st.session_state:
    st.session_state.dataset_id = None
if "dataset_path" not in st.session_state:
    st.session_state.dataset_path = None
if "dataset_profile" not in st.session_state:
    st.session_state.dataset_profile = None
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "latest_workflow_state" not in st.session_state:
    st.session_state.latest_workflow_state = None
if "df" not in st.session_state:
    st.session_state.df = None
if "dashboard_spec" not in st.session_state:
    st.session_state.dashboard_spec = None
if "dashboard_filter_state" not in st.session_state:
    st.session_state.dashboard_filter_state = DashboardFilterState()
if "dashboard_theme" not in st.session_state:
    st.session_state.dashboard_theme = "corporate"


# --- SIDEBAR: DATASET SELECTION & UPLOAD ---
with st.sidebar:
    st.title("⚙️ Control Center")
    st.markdown("### 📁 Dataset Management")

    data_source_mode = st.radio(
        "Choose Data Source:",
        ["Sample Dataset (Superstore)", "Upload File"],
        index=0
    )

    if data_source_mode == "Sample Dataset (Superstore)":
        if st.button("🚀 Load Sample Superstore Dataset", use_container_width=True):
            with st.spinner("Generating sample retail dataset..."):
                d_id, d_path, d_prof = dataset_svc.ensure_sample_dataset()
                st.session_state.dataset_id = d_id
                st.session_state.dataset_path = str(d_path)
                st.session_state.dataset_profile = d_prof
                st.session_state.df = load_dataset(d_path)
                st.session_state.session_id = session_svc.create_session(d_id, title="Sample Superstore Analysis")
                st.success(f"Loaded: {d_prof.filename} ({d_prof.row_count:,} rows)")

    else:
        uploaded = st.file_uploader(
            "Upload CSV, Excel, Parquet, or JSON",
            type=["csv", "xlsx", "xls", "parquet", "json"]
        )
        if uploaded is not None:
            if st.button("📤 Process & Profile Uploaded File", use_container_width=True):
                with st.spinner("Profiling uploaded dataset..."):
                    d_id, d_path, d_prof = dataset_svc.save_uploaded_file(uploaded, uploaded.name)
                    st.session_state.dataset_id = d_id
                    st.session_state.dataset_path = str(d_path)
                    st.session_state.dataset_profile = d_prof
                    st.session_state.df = load_dataset(d_path)
                    st.session_state.session_id = session_svc.create_session(d_id, title=f"Analysis of {uploaded.name}")
                    st.success(f"Successfully profiled: {uploaded.name}")

    st.markdown("---")
    st.markdown("### 🛡️ Execution Sandbox")
    st.info("Environment: Out-of-Process Sandbox\nStatus: Active (No Network, Restricted FS)")

    st.markdown("---")
    st.markdown("### 💡 Quick Analytical Queries")
    quick_queries = [
        "What is the total revenue?",
        "Which region performs best by total sales?",
        "Show monthly sales trends.",
        "Which products generate the highest revenue?",
        "Identify correlations between variables.",
        "Find missing and duplicate records.",
        "Generate an executive summary."
    ]
    for q_idx, q_prompt in enumerate(quick_queries):
        if st.button(q_prompt, use_container_width=True, key=f"quick_btn_{q_idx}"):
            st.session_state["submitted_query"] = q_prompt


# Default initialization if nothing loaded yet
if st.session_state.dataset_id is None:
    d_id, d_path, d_prof = dataset_svc.ensure_sample_dataset()
    st.session_state.dataset_id = d_id
    st.session_state.dataset_path = str(d_path)
    st.session_state.dataset_profile = d_prof
    st.session_state.df = load_dataset(d_path)
    st.session_state.session_id = session_svc.create_session(d_id, title="Sample Superstore Analysis")

profile = st.session_state.dataset_profile
df = st.session_state.df

# --- HEADER ---
st.markdown('<div class="main-header">AUTONOMOUS DATA ANALYST AI</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="sub-header">Active Dataset: <b>{profile.filename}</b> &nbsp;|&nbsp; '
    f'Rows: <b>{profile.row_count:,}</b> &nbsp;|&nbsp; Columns: <b>{profile.column_count}</b> &nbsp;|&nbsp; '
    f'Health Rating: <b>{profile.health_score}/100</b></div>',
    unsafe_allow_html=True
)


# --- MAIN TABS ---
tab_health, tab_builder, tab_explorer, tab_chat, tab_code, tab_vis, tab_insights, tab_reports = st.tabs([
    "📊 Dataset Health",
    "🎛️ AI Dashboard Builder",
    "🔍 Dataset Explorer",
    "💬 AI Analyst Chat",
    "💻 Code Workspace",
    "📈 Visualizations",
    "💡 Business Insights",
    "📄 Export Reports"
])


# ==============================================================================
# TAB 1: DATASET HEALTH
# ==============================================================================
with tab_health:
    st.subheader("Dataset Health & Structural Overview")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Rows", f"{profile.row_count:,}")
    col2.metric("Total Columns", f"{profile.column_count}")
    col3.metric("Missing Values", f"{profile.total_missing_cells:,} ({profile.total_missing_percentage}%)")
    col4.metric("Duplicate Rows", f"{profile.duplicate_rows_count:,} ({profile.duplicate_rows_percentage}%)")

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Numeric Columns", len(profile.numeric_columns))
    col6.metric("Categorical Columns", len(profile.categorical_columns))
    col7.metric("Datetime Columns", len(profile.datetime_columns))
    col8.metric("Dataset Health Score", f"{profile.health_score}/100")

    st.markdown("---")
    st.markdown(f"**Structural Summary:** {profile.summary}")

    # Column inventory breakdown
    st.subheader("Column Roster & Inferred Data Types")
    col_data = []
    for c_name, c_prof in profile.columns.items():
        col_data.append({
            "Column Name": c_name,
            "Pandas Dtype": c_prof.dtype,
            "Inferred Category": c_prof.inferred_type.upper(),
            "Missing Count": c_prof.missing_count,
            "Missing %": f"{c_prof.missing_percentage}%",
            "Unique Count": c_prof.unique_count,
            "Candidate PK": "✓ Yes" if c_prof.is_primary_key_candidate else "No"
        })
    st.dataframe(pd.DataFrame(col_data), use_container_width=True)


# ==============================================================================
# TAB 2: AUTONOMOUS AI DASHBOARD BUILDER
# ==============================================================================
with tab_builder:
    st.subheader("Autonomous AI Dashboard Builder")
    st.markdown(
        "Generate a complete, presentation-ready analytics dashboard. The agent inspects dataset dimensions, "
        "identifies KPIs, plans executive sections, selects optimal chart types, and generates actionable strategic insights."
    )

    # Dashboard Control Ribbon
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([2, 1, 1])
    with col_ctrl1:
        generate_clicked = st.button(
            "⚡ Generate Autonomous Dashboard",
            type="primary",
            use_container_width=True,
            key="btn_gen_dash"
        )
    with col_ctrl2:
        selected_theme = st.selectbox(
            "Visual Theme",
            ["corporate", "light", "dark"],
            index=["corporate", "light", "dark"].index(st.session_state.dashboard_theme),
            key="select_dash_theme"
        )
    with col_ctrl3:
        pres_mode = st.toggle("📺 Presentation Mode", value=False, key="toggle_pres_mode")

    planner = DashboardPlanningAgent()
    generator = DashboardGenerator()
    exporter = DashboardExporter(Path(get_settings().reports_path))

    # Trigger Generation
    if generate_clicked:
        with st.spinner("🤖 Autonomous Dashboard Planning & Visualization Rendering in progress..."):
            try:
                spec = planner.plan_dashboard(df=df, profile=profile)
                spec.theme = selected_theme
                spec = generator.generate_dashboard(df=df, spec=spec, profile=profile)
                st.session_state.dashboard_spec = spec
                st.session_state.dashboard_theme = selected_theme
                st.session_state.dashboard_filter_state = DashboardFilterState()
                st.success("✨ Autonomous dashboard successfully generated!")
            except Exception as e:
                st.error(f"Failed to generate dashboard: {e}")

    # Handle Theme Change on Existing Spec
    if st.session_state.dashboard_spec is not None and selected_theme != st.session_state.dashboard_theme:
        st.session_state.dashboard_theme = selected_theme
        st.session_state.dashboard_spec.theme = selected_theme
        filtered_df = apply_dashboard_filters(df, st.session_state.dashboard_filter_state)
        st.session_state.dashboard_spec = generator.generate_dashboard(
            df=filtered_df, spec=st.session_state.dashboard_spec, profile=profile
        )

    # If Spec Exists, Render Dashboard, Filters, Controls, and Exports
    if st.session_state.dashboard_spec is not None:
        spec = st.session_state.dashboard_spec

        # --- Interactive Filter Bar ---
        with st.expander("🔍 Interactive Dashboard Filters & Slicers", expanded=False):
            f_col1, f_col2, f_col3 = st.columns(3)
            filter_updated = False
            new_filter_state = st.session_state.dashboard_filter_state

            # Date Filter
            if profile.datetime_columns:
                date_c = profile.datetime_columns[0]
                with f_col1:
                    st.markdown(f"**Date Slicer (`{date_c}`)**")
                    valid_dates = pd.to_datetime(df[date_c], errors="coerce").dropna()
                    if not valid_dates.empty:
                        min_d = valid_dates.min().date()
                        max_d = valid_dates.max().date()
                        cur_range = new_filter_state.date_range or (min_d, max_d)
                        selected_dates = st.date_input(
                            "Select Date Range",
                            value=cur_range,
                            min_value=min_d,
                            max_value=max_d,
                            key="dash_date_filter_input"
                        )
                        if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
                            s_str, e_str = str(selected_dates[0]), str(selected_dates[1])
                            if new_filter_state.date_range != (s_str, e_str):
                                new_filter_state.date_column = date_c
                                new_filter_state.date_range = (s_str, e_str)
                                filter_updated = True

            # Categorical Filters (up to 2 candidates)
            cat_filters = list(spec.available_filters.keys())[:2]
            for idx, c_col in enumerate(cat_filters):
                target_col = f_col2 if idx == 0 else f_col3
                with target_col:
                    options = spec.available_filters[c_col]
                    curr_selected = new_filter_state.selected_categories.get(c_col, [])
                    new_selected = st.multiselect(
                        f"Filter by {c_col}",
                        options=options,
                        default=curr_selected,
                        key=f"dash_filter_cat_{c_col}"
                    )
                    if set(new_selected) != set(curr_selected):
                        new_filter_state.selected_categories[c_col] = new_selected
                        filter_updated = True

            # Reset filters button
            if st.button("🔄 Reset All Filters", key="btn_reset_filters"):
                st.session_state.dashboard_filter_state = DashboardFilterState()
                filtered_df = df
                st.session_state.dashboard_spec = generator.generate_dashboard(
                    df=filtered_df, spec=spec, profile=profile
                )
                st.rerun()

            if filter_updated:
                st.session_state.dashboard_filter_state = new_filter_state
                filtered_df = apply_dashboard_filters(df, new_filter_state)
                st.session_state.dashboard_spec = generator.generate_dashboard(
                    df=filtered_df, spec=spec, profile=profile
                )
                st.rerun()

        # Callbacks for chart customizations
        def on_chart_type_change(chart_id: str, new_type: str):
            for sec in st.session_state.dashboard_spec.sections:
                for c in sec.charts:
                    if c.id == chart_id and c.chart_type != new_type:
                        c.chart_type = new_type
                        filtered_df = apply_dashboard_filters(df, st.session_state.dashboard_filter_state)
                        fig, recs = generator._build_chart_content(filtered_df, c, st.session_state.dashboard_spec.theme)
                        c.figure_dict = fig.to_dict() if fig else {}
                        c.table_records = recs
                        exp, ins = generator.explanation_engine.explain_chart(
                            title=c.title, chart_type=c.chart_type, x_col=c.x_col, y_col=c.y_col, data_records=recs
                        )
                        c.explanation = exp
                        c.insights = ins
                        st.rerun()

        def on_chart_remove(chart_id: str):
            for sec in st.session_state.dashboard_spec.sections:
                sec.charts = [c for c in sec.charts if c.id != chart_id]
            st.rerun()

        st.markdown("---")

        # Render Presentation Mode or Standard Dashboard
        if pres_mode:
            render_presentation_mode(spec)
        else:
            render_dashboard_layout(
                spec=spec,
                on_chart_type_change=on_chart_type_change,
                on_chart_remove=on_chart_remove
            )

        st.markdown("---")

        # --- Natural Language Customization Assistant ---
        st.subheader("💬 AI Dashboard Customization Assistant")
        nl_col1, nl_col2 = st.columns([4, 1])
        with nl_col1:
            custom_prompt = st.text_input(
                "Instruct the AI to customize the dashboard (e.g., 'Switch to dark theme', 'Remove pareto chart', 'Focus on East region'):",
                placeholder="Type modification instructions...",
                key="dash_custom_prompt"
            )
        with nl_col2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            apply_custom = st.button("Apply Modification", key="btn_apply_custom", use_container_width=True)

        if apply_custom and custom_prompt.strip():
            prompt_lower = custom_prompt.lower()
            filtered_df = apply_dashboard_filters(df, st.session_state.dashboard_filter_state)
            if "dark" in prompt_lower:
                st.session_state.dashboard_spec.theme = "dark"
                st.session_state.dashboard_theme = "dark"
                st.session_state.dashboard_spec = generator.generate_dashboard(filtered_df, st.session_state.dashboard_spec, profile)
                st.success("Applied dark theme.")
                st.rerun()
            elif "light" in prompt_lower:
                st.session_state.dashboard_spec.theme = "light"
                st.session_state.dashboard_theme = "light"
                st.session_state.dashboard_spec = generator.generate_dashboard(filtered_df, st.session_state.dashboard_spec, profile)
                st.success("Applied light theme.")
                st.rerun()
            elif "remove" in prompt_lower or "delete" in prompt_lower:
                # Find matching chart
                removed = False
                for sec in st.session_state.dashboard_spec.sections:
                    for c in list(sec.charts):
                        if any(term in c.title.lower() or term in c.chart_type.lower() for term in prompt_lower.split()):
                            sec.charts.remove(c)
                            removed = True
                            st.success(f"Removed chart: {c.title}")
                            break
                    if removed:
                        break
                if not removed:
                    st.info("Could not find a chart matching the removal criteria.")
                else:
                    st.rerun()
            else:
                # General re-plan with user preferences
                with st.spinner("AI re-planning dashboard based on custom instruction..."):
                    new_spec = planner.plan_dashboard(filtered_df, profile, user_preferences=custom_prompt)
                    new_spec.theme = st.session_state.dashboard_spec.theme
                    new_spec = generator.generate_dashboard(filtered_df, new_spec, profile)
                    st.session_state.dashboard_spec = new_spec
                    st.success("Dashboard updated based on your instructions!")
                    st.rerun()

        # --- Multi-Format Export Section ---
        st.markdown("---")
        st.subheader("📥 Export Complete Dashboard")
        st.caption("Export this presentation-ready dashboard across executive, presentation, and data engineering formats.")
        exp_col1, exp_col2, exp_col3, exp_col4 = st.columns(4)

        # 1. HTML Export
        with exp_col1:
            try:
                html_path = exporter.export_to_html(spec)
                with open(html_path, "r", encoding="utf-8") as f:
                    st.download_button(
                        label="🌐 Interactive HTML",
                        data=f.read(),
                        file_name=html_path.name,
                        mime="text/html",
                        use_container_width=True,
                        key="btn_export_dash_html"
                    )
            except Exception as e:
                st.error(f"HTML Export Error: {e}")

        # 2. PowerPoint (.pptx) Export
        with exp_col2:
            try:
                pptx_path = exporter.export_to_pptx(spec)
                with open(pptx_path, "rb") as f:
                    st.download_button(
                        label="📊 PowerPoint Deck (.pptx)",
                        data=f.read(),
                        file_name=pptx_path.name,
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        use_container_width=True,
                        key="btn_export_dash_pptx"
                    )
            except Exception as e:
                st.error(f"PPTX Export Error: {e}")

        # 3. PDF Summary Export
        with exp_col3:
            try:
                pdf_path = exporter.export_to_pdf(spec)
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="📄 Executive PDF Summary",
                        data=f.read(),
                        file_name=pdf_path.name,
                        mime="application/pdf",
                        use_container_width=True,
                        key="btn_export_dash_pdf"
                    )
            except Exception as e:
                st.error(f"PDF Export Error: {e}")

        # 4. Excel Multi-Sheet Export
        with exp_col4:
            try:
                excel_path = exporter.export_to_excel(spec)
                with open(excel_path, "rb") as f:
                    st.download_button(
                        label="📗 All Charts Excel (.xlsx)",
                        data=f.read(),
                        file_name=excel_path.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        key="btn_export_dash_excel"
                    )
            except Exception as e:
                st.error(f"Excel Export Error: {e}")

    else:
        st.info("👆 Click **'⚡ Generate Autonomous Dashboard'** above to automatically blueprint, compute, and render your AI analytics dashboard.")


# ==============================================================================
# TAB 2: DATASET EXPLORER
# ==============================================================================
with tab_explorer:
    st.subheader("Interactive Dataset Explorer")

    # Preview
    st.write(f"Showing first 100 rows of `{profile.filename}`:")
    st.dataframe(df.head(100), use_container_width=True)

    # Descriptive statistics
    st.subheader("Descriptive Statistics")
    if profile.numeric_columns:
        desc_stats = compute_descriptive_stats(df, profile.numeric_columns)
        st.dataframe(pd.DataFrame(desc_stats).T, use_container_width=True)

    # Data Quality & Cleaning Proposals
    st.subheader("Data Quality Inspection & Transformation Recommendations")
    cleaning_actions = generate_cleaning_proposals(df, profile)
    if cleaning_actions:
        st.info(f"Detected {len(cleaning_actions)} data quality optimization opportunities:")
        for act in cleaning_actions:
            st.markdown(f"- **{act.issue}**: {act.explanation} *(Action: `{act.action_type}`) — Destructive: {act.is_destructive}*")
    else:
        st.success("No critical quality defects detected in this dataset.")


# ==============================================================================
# TAB 3: AI ANALYST CHAT
# ==============================================================================
with tab_chat:
    st.subheader("Conversational Analytical Workspace")
    st.markdown("Ask natural language business questions. The agent autonomously plans, codes, executes, and validates.")

    # Render previous messages
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "metrics" in msg and msg["metrics"]:
                st.caption(f"Calculated Metrics: {msg['metrics']}")

    # Check if a query came from quick buttons
    prefilled_query = st.session_state.pop("submitted_query", None)
    user_input = st.chat_input("Ask a question about your data (e.g., 'Which region generated the highest revenue?')...")
    active_query = prefilled_query or user_input

    if active_query:
        # Add user prompt to chat
        st.session_state.chat_messages.append({"role": "user", "content": active_query})
        with st.chat_message("user"):
            st.markdown(active_query)

        # Autonomous Agent Execution
        with st.chat_message("assistant"):
            progress_placeholder = st.empty()
            with progress_placeholder.container():
                st.info("🤖 **Autonomous Agents Mobilized**: Profiling -> Planning -> Coding -> Sandbox Executing -> Validating...")

            try:
                state = workflow_mgr.run_analysis(
                    question=active_query,
                    dataset_path=st.session_state.dataset_path,
                    dataset_id=st.session_state.dataset_id,
                    dataset_profile=st.session_state.dataset_profile,
                    conversation_history=st.session_state.chat_messages
                )

                st.session_state.latest_workflow_state = state
                report = state.get("final_report")
                exec_res = state.get("execution_result")

                progress_placeholder.empty()

                if report:
                    st.markdown(f"### 📋 Analytical Answer\n{report.executive_summary}")
                    
                    if report.metrics_summary:
                        st.markdown("**Computed Numerical Proof:**")
                        cols = st.columns(min(len(report.metrics_summary), 4))
                        for idx, (k, v) in enumerate(report.metrics_summary.items()):
                            cols[idx % 4].metric(k.replace("_", " ").title(), str(v))

                    # Render figures if present
                    if state.get("charts"):
                        for c_idx, chart in enumerate(state["charts"]):
                            fig = go.Figure(chart.figure_dict)
                            st.plotly_chart(fig, use_container_width=True, key=f"chat_fig_{chart.chart_id}_{c_idx}")
                            st.caption(f"💡 *{chart.explanation}*")

                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": report.executive_summary,
                        "metrics": report.metrics_summary
                    })

                else:
                    st.error("Analysis completed without final report.")

            except Exception as e:
                progress_placeholder.empty()
                st.error(f"Error during agentic execution: {str(e)}")


# ==============================================================================
# TAB 4: CODE WORKSPACE
# ==============================================================================
with tab_code:
    st.subheader("Autonomous Code Workspace & Execution Trace")

    state = st.session_state.latest_workflow_state
    if state and state.get("generated_code"):
        st.markdown(f"**Execution Status**: {'✅ Successful' if state.get('execution_result') and state['execution_result'].success else '❌ Failed'}")
        st.markdown(f"**Retry Attempts**: {state.get('retry_count', 1)} / {state.get('max_retries', 3)}")

        st.markdown("### Generated Python Analysis Script")
        st.code(state["generated_code"], language="python")

        exec_res = state.get("execution_result")
        if exec_res:
            col_e1, col_e2, col_e3 = st.columns(3)
            col_e1.metric("Execution Time", f"{exec_res.execution_time_seconds:.2f}s")
            col_e2.metric("Return Code", exec_res.return_code)
            col_e3.metric("Peak Memory", f"{exec_res.memory_used_mb:.1f} MB")

            if exec_res.stdout:
                with st.expander("Standard Output (stdout)"):
                    st.text(exec_res.stdout)
            if exec_res.stderr:
                with st.expander("Standard Error / Traceback (stderr)"):
                    st.text(exec_res.stderr)

        # Show Error Diagnoses if any
        if state.get("error_diagnoses"):
            st.markdown("### Self-Correction Audit History")
            for diag in state["error_diagnoses"]:
                with st.expander(f"Attempt #{diag.attempt_number}: {diag.error_type} - {diag.error_message}"):
                    st.markdown(f"**Root Cause**: {diag.root_cause}")
                    st.markdown(f"**Suggested Correction**: {diag.suggested_correction}")
                    st.code(diag.failed_code, language="python")

    else:
        st.info("Submit an analytical question in the Chat tab or click a Quick Analytical Query to inspect generated Python code.")


# ==============================================================================
# TAB 5: VISUALIZATIONS
# ==============================================================================
with tab_vis:
    st.subheader("Interactive Computed Visualizations")

    state = st.session_state.latest_workflow_state
    if state and state.get("charts"):
        for c_idx, chart in enumerate(state["charts"]):
            st.markdown(f"### {chart.title}")
            fig = go.Figure(chart.figure_dict)
            st.plotly_chart(fig, use_container_width=True, key=f"vis_tab_fig_{chart.chart_id}_{c_idx}")
            st.info(f"**Interpretation**: {chart.explanation}")
            if chart.insights:
                for ins in chart.insights:
                    st.markdown(f"- {ins}")
            st.markdown("---")
    else:
        st.info("No visualizations generated yet. Ask a question such as 'Show monthly sales trends' or 'Compare sales by region'.")


# ==============================================================================
# TAB 6: BUSINESS INSIGHTS
# ==============================================================================
with tab_insights:
    st.subheader("Executive Insights & Strategic Recommendations")

    state = st.session_state.latest_workflow_state
    if state and state.get("final_report"):
        report = state["final_report"]

        st.markdown(f"### Question Answered\n> *\"{report.question}\"*")
        st.markdown(f"### Executive Summary\n{report.executive_summary}")

        if report.key_findings:
            st.markdown("### Empirical Business Findings")
            for item in report.key_findings:
                with st.container():
                    st.markdown(f"#### 📌 {item.title} ({item.category})")
                    st.markdown(f"- **Finding**: {item.finding}")
                    st.markdown(f"- **Evidence**: `{item.evidence}`")
                    st.markdown(f"- **Business Implication**: {item.business_implication}")
                    st.markdown(f"- **Recommendation**: {item.recommendation}")
                    st.markdown("")

        if report.recommendations:
            st.markdown("### Strategic Recommendations")
            for rec in report.recommendations:
                st.markdown(f"✅ **{rec}**")

        if report.limitations:
            st.markdown("### Analytical Boundaries & Limitations")
            for lim in report.limitations:
                st.markdown(f"⚠️ *{lim}*")
    else:
        st.info("Execute an analysis to view executive summaries, actionable business recommendations, and limitations.")


# ==============================================================================
# TAB 7: EXPORT REPORTS
# ==============================================================================
with tab_reports:
    st.subheader("Export Analytical Reports & Tabular Results")

    state = st.session_state.latest_workflow_state
    if state and state.get("final_report"):
        report = state["final_report"]

        st.write(f"Ready to export report for inquiry: **\"{report.question}\"**")

        col_r1, col_r2, col_r3 = st.columns(3)

        # 1. Export PDF
        with col_r1:
            try:
                pdf_path = pdf_gen.generate(report)
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="📥 Download PDF Report",
                        data=f.read(),
                        file_name=f"Report_{report.report_id[:8]}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key="btn_download_pdf_report"
                    )
            except Exception as e:
                st.error(f"PDF generation error: {e}")

        # 2. Export Excel
        with col_r2:
            try:
                excel_path = excel_gen.generate(report)
                with open(excel_path, "rb") as f:
                    st.download_button(
                        label="📥 Download Excel Workbook",
                        data=f.read(),
                        file_name=f"Report_{report.report_id[:8]}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        key="btn_download_excel_report"
                    )
            except Exception as e:
                st.error(f"Excel generation error: {e}")

        # 3. Export CSV (Tabular results)
        with col_r3:
            if report.tabular_results:
                primary_table_name = list(report.tabular_results.keys())[0]
                records = report.tabular_results[primary_table_name]
                csv_buffer = io.StringIO()
                pd.DataFrame(records).to_csv(csv_buffer, index=False)
                st.download_button(
                    label=f"📥 Download CSV ({primary_table_name})",
                    data=csv_buffer.getvalue(),
                    file_name=f"{primary_table_name}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="btn_download_csv_table"
                )
            else:
                st.button("No tables available for CSV export", disabled=True, use_container_width=True, key="btn_no_csv")

        st.markdown("---")
        st.markdown("### Generated Output Tables Preview")
        if report.tabular_results:
            for tbl_name, rows in report.tabular_results.items():
                st.markdown(f"**Table: `{tbl_name}`** ({len(rows)} records)")
                st.dataframe(pd.DataFrame(rows), use_container_width=True)

    else:
        st.info("Run an analytical question first to enable report generation and multi-format exports.")
