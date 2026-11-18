"""Agent 5: Python Code Generation Agent."""

import json
import logging
import re
from typing import Any, Dict, List, Optional
from schemas.analysis import AnalysisPlan
from schemas.dataset import DatasetProfile
from schemas.execution import ErrorDiagnosis
from services.llm_service import LLMService, get_llm_service

logger = logging.getLogger(__name__)

CODE_GENERATOR_SYSTEM_PROMPT = """You are the Senior Python Code Generation Agent of an Autonomous Data Analyst AI.
Your mission is to generate clean, robust, executable Python code to perform data analysis and render Plotly charts.

CRITICAL EXECUTION INTERFACE RULES:
1. `df` is ALREADY loaded in your execution scope as a pandas DataFrame.
2. DO NOT import or call `pd.read_csv`, `os`, `sys`, `subprocess`, `requests`, `open`, or network libraries.
3. You have access to: `pandas as pd`, `numpy as np`, `scipy`, `sklearn`, `plotly.express as px`, `plotly.graph_objects as go`.
4. Store your computed results into the pre-initialized `OUTPUT` dictionary:
   - `OUTPUT['tables']['table_name'] = result_dataframe` (or list of dicts)
   - `OUTPUT['metrics']['metric_name'] = float_or_int_or_str_value`
   - `OUTPUT['figures'].append(fig.to_dict())` (or simply define `fig = ...` which the harness captures automatically)
5. ALWAYS check if columns exist and handle NaNs safely (`.dropna()` or `.fillna()`).
6. Format numbers appropriately (round floats to 2 or 4 decimal places).
7. Ensure all column names match the Dataset Profile EXACTLY (case-sensitive).
8. Return ONLY executable Python code enclosed inside ```python ... ``` fences.
"""


class CodeAgent:
    """Agent responsible for writing dataset-aware, secure Python analytics scripts."""

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service or get_llm_service()

    def generate_code(
        self,
        plan: AnalysisPlan,
        profile: DatasetProfile,
        specification: Optional[Dict[str, Any]] = None,
        previous_errors: Optional[List[ErrorDiagnosis]] = None
    ) -> str:
        """Generate executable Python script fulfilling the analytical plan."""
        logger.info(f"CodeAgent generating script for plan: '{plan.primary_goal}'")

        if self.llm_service.is_configured:
            try:
                return self._generate_with_llm(plan, profile, specification, previous_errors)
            except Exception as e:
                logger.warning(f"LLM code generation failed: {e}. Falling back to dynamic heuristic generator.")

        return self._generate_heuristic_code(plan, profile, previous_errors)

    def _generate_with_llm(
        self,
        plan: AnalysisPlan,
        profile: DatasetProfile,
        specification: Optional[Dict[str, Any]],
        previous_errors: Optional[List[ErrorDiagnosis]]
    ) -> str:
        prompt_content = (
            f"Dataset Columns and Types:\n"
            f"{json.dumps({c: prof.dtype for c, prof in profile.columns.items()}, indent=2)}\n\n"
            f"Analysis Plan:\n{plan.model_dump_json(indent=2)}\n\n"
        )

        if specification:
            prompt_content += f"Analytical Specification:\n{json.dumps(specification, indent=2)}\n\n"

        if previous_errors:
            prompt_content += "PREVIOUS EXECUTION ATTEMPTS FAILED WITH THESE ERRORS:\n"
            for err in previous_errors:
                prompt_content += (
                    f"- Error Type: {err.error_type}\n"
                    f"  Message: {err.error_message}\n"
                    f"  Root Cause: {err.root_cause}\n"
                    f"  Suggested Fix: {err.suggested_correction}\n"
                    f"  Failed Code Snippet:\n{err.failed_code}\n\n"
                )
            prompt_content += "Make sure you completely fix the above errors in this new version.\n\n"

        messages = [
            {"role": "system", "content": CODE_GENERATOR_SYSTEM_PROMPT},
            {"role": "user", "content": prompt_content}
        ]

        raw_response = self.llm_service.generate_chat_completion(messages, temperature=0.0)
        return self._extract_code_blocks(raw_response)

    def _extract_code_blocks(self, text: str) -> str:
        """Extract python code from Markdown fences."""
        match = re.search(r"```python\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()

    def _generate_heuristic_code(
        self,
        plan: AnalysisPlan,
        profile: DatasetProfile,
        previous_errors: Optional[List[ErrorDiagnosis]] = None
    ) -> str:
        """Deterministic, dataset-aware code generator handling all standard analytical scenarios."""
        q_lower = plan.question.lower()
        num_cols = profile.numeric_columns
        cat_cols = profile.categorical_columns
        date_cols = profile.datetime_columns

        # Pick primary metric column
        metric_col = None
        for cand in ["Sales", "Revenue", "Profit", "Amount", "Price", "Total"]:
            for nc in num_cols:
                if cand.lower() in nc.lower():
                    metric_col = nc
                    break
            if metric_col:
                break
        if not metric_col and num_cols:
            metric_col = num_cols[0]

        # Pick primary grouping column: check if a specific category column is mentioned in the query
        group_col = None
        for cc in cat_cols:
            if cc.lower() in q_lower:
                group_col = cc
                break

        if not group_col:
            for cand in ["Region", "Product_Name", "Product", "Category", "Sub_Category", "Customer_ID", "Segment"]:
                for cc in cat_cols:
                    if cand.lower() in cc.lower():
                        group_col = cc
                        break
                if group_col:
                    break
        if not group_col and cat_cols:
            group_col = cat_cols[0]

        # Date column
        date_col = date_cols[0] if date_cols else None
        for dc in date_cols:
            if "order" in dc.lower() or "date" in dc.lower():
                date_col = dc
                break

        # Check for specific intents:
        # Scenario 1: Trend / Monthly / Over time
        if any(k in q_lower for k in ["trend", "monthly", "over time", "month-over-month", "growth"]) and date_col and metric_col:
            return f"""# Trend analysis over time
df_work = df.copy()
df_work['{date_col}'] = pd.to_datetime(df_work['{date_col}'], errors='coerce')
df_work = df_work.dropna(subset=['{date_col}', '{metric_col}'])

# Resample monthly
ts = df_work.set_index('{date_col}').resample('ME')['{metric_col}'].sum().reset_index()
ts['Period'] = ts['{date_col}'].dt.strftime('%Y-%m')
ts['Mom_Growth_Pct'] = (ts['{metric_col}'].pct_change() * 100).round(2)

OUTPUT['tables']['monthly_trend'] = ts[['Period', '{metric_col}', 'Mom_Growth_Pct']]
OUTPUT['metrics']['total_{metric_col.lower()}'] = float(round(ts['{metric_col}'].sum(), 2))
OUTPUT['metrics']['average_monthly_{metric_col.lower()}'] = float(round(ts['{metric_col}'].mean(), 2))

fig = px.line(
    ts, 
    x='Period', 
    y='{metric_col}', 
    title='Monthly Trend of {metric_col}',
    markers=True,
    labels={{'{metric_col}': '{metric_col}', 'Period': 'Month'}}
)
fig.update_layout(template='plotly_white')
OUTPUT['figures'].append(fig.to_dict())
"""

        # Scenario 2: Region / Category Segment comparison
        if any(k in q_lower for k in ["region", "category", "highest", "best", "compare", "performance"]) and group_col and metric_col:
            return f"""# Segment performance comparison
df_work = df.dropna(subset=['{group_col}', '{metric_col}']).copy()
grouped = df_work.groupby('{group_col}')['{metric_col}'].agg(['sum', 'mean', 'count']).reset_index()
grouped.columns = ['{group_col}', 'Total_{metric_col}', 'Average_{metric_col}', 'Record_Count']
grouped = grouped.sort_values(by='Total_{metric_col}', ascending=False)
grouped['Share_of_Total_Pct'] = ((grouped['Total_{metric_col}'] / grouped['Total_{metric_col}'].sum()) * 100).round(2)

top_segment = grouped.iloc[0]['{group_col}'] if not grouped.empty else 'None'
top_value = float(grouped.iloc[0]['Total_{metric_col}']) if not grouped.empty else 0.0

OUTPUT['tables']['segment_comparison'] = grouped
OUTPUT['metrics']['top_segment'] = str(top_segment)
OUTPUT['metrics']['top_segment_{metric_col.lower()}'] = round(top_value, 2)
OUTPUT['metrics']['total_{metric_col.lower()}'] = float(round(grouped['Total_{metric_col}'].sum(), 2))

fig = px.bar(
    grouped.head(10), 
    x='{group_col}', 
    y='Total_{metric_col}', 
    color='{group_col}',
    title='Total {metric_col} by {group_col}',
    text_auto='.2s'
)
fig.update_layout(template='plotly_white', showlegend=False)
OUTPUT['figures'].append(fig.to_dict())
"""

        # Scenario 3: Top N items (customers, products)
        if any(k in q_lower for k in ["top", "highest", "leading"]) and group_col and metric_col:
            return f"""# Top items ranking
df_work = df.dropna(subset=['{group_col}', '{metric_col}']).copy()
top_df = df_work.groupby('{group_col}')['{metric_col}'].sum().reset_index()
top_df = top_df.sort_values(by='{metric_col}', ascending=False).head(10)

OUTPUT['tables']['top_items'] = top_df
OUTPUT['metrics']['leader'] = str(top_df.iloc[0]['{group_col}'])
OUTPUT['metrics']['leader_value'] = float(round(top_df.iloc[0]['{metric_col}'], 2))

fig = px.bar(
    top_df, 
    x='{metric_col}', 
    y='{group_col}', 
    orientation='h',
    title='Top 10 {group_col} by {metric_col}',
    color='{metric_col}',
    color_continuous_scale='Blues'
)
fig.update_layout(template='plotly_white', yaxis=dict(autorange='reversed'))
OUTPUT['figures'].append(fig.to_dict())
"""

        # Scenario 4: Correlation analysis
        if any(k in q_lower for k in ["correlation", "relationship", "correlated"]) and len(num_cols) >= 2:
            c1, c2 = num_cols[0], num_cols[1]
            return f"""# Correlation analysis
sub_df = df[['{c1}', '{c2}']].dropna()
corr_val = float(round(sub_df['{c1}'].corr(sub_df['{c2}']), 4))

OUTPUT['tables']['correlation_data'] = sub_df.describe().reset_index()
OUTPUT['metrics']['correlation_{c1}_{c2}'] = corr_val

fig = px.scatter(
    sub_df.sample(min(len(sub_df), 500)), 
    x='{c1}', 
    y='{c2}', 
    trendline='ols',
    title=f'Relationship between {c1} and {c2} (r = {{corr_val}})'
)
fig.update_layout(template='plotly_white')
OUTPUT['figures'].append(fig.to_dict())
"""

        # Default fallback: General aggregation & distribution
        if metric_col:
            return f"""# General metric aggregation and distribution
clean_series = df['{metric_col}'].dropna()
stats_df = clean_series.describe().reset_index()

OUTPUT['tables']['descriptive_stats'] = stats_df
OUTPUT['metrics']['mean'] = float(round(clean_series.mean(), 2))
OUTPUT['metrics']['median'] = float(round(clean_series.median(), 2))
OUTPUT['metrics']['sum'] = float(round(clean_series.sum(), 2))

fig = px.histogram(
    df, 
    x='{metric_col}', 
    nbins=30, 
    title='Distribution of {metric_col}',
    marginal='box'
)
fig.update_layout(template='plotly_white')
OUTPUT['figures'].append(fig.to_dict())
"""
        else:
            first_col = profile.categorical_columns[0] if profile.categorical_columns else list(profile.columns.keys())[0]
            return f"""# Frequency counts
counts = df['{first_col}'].value_counts().head(10).reset_index()
counts.columns = ['{first_col}', 'Count']

OUTPUT['tables']['frequencies'] = counts
OUTPUT['metrics']['total_records'] = int(len(df))

fig = px.bar(
    counts, 
    x='{first_col}', 
    y='Count', 
    title='Top categories in {first_col}'
)
fig.update_layout(template='plotly_white')
OUTPUT['figures'].append(fig.to_dict())
"""
