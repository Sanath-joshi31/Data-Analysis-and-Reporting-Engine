"""Automated chart intelligence and analytical explanation engine."""

import json
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from services.llm_service import LLMService, get_llm_service


class ChartExplanationEngine:
    """Generates empirical explanations and bulleted takeaways grounded in computed chart data."""

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm = llm_service or get_llm_service()

    def explain_chart(
        self,
        title: str,
        chart_type: str,
        x_col: Optional[str],
        y_col: Optional[str],
        data_records: List[Dict[str, Any]]
    ) -> Tuple[str, List[str]]:
        """Produce narrative interpretation and key bullet points from computed data records."""
        if not data_records:
            return f"Chart illustrates {title}.", ["No data available for this selection."]

        df_records = pd.DataFrame(data_records)

        # Check if LLM is configured
        if self.llm.is_configured:
            try:
                sample_summary = df_records.head(5).to_dict(orient="records")
                prompt = (
                    f"Chart Title: {title}\n"
                    f"Chart Type: {chart_type}\n"
                    f"X Axis: {x_col}, Y Axis: {y_col}\n"
                    f"Sample Computed Values: {json.dumps(sample_summary, indent=2)}\n\n"
                    "Generate:\n1. A clear 1-2 sentence explanation of what this chart shows.\n"
                    "2. Exactly 2 bullet points describing the top empirical finding and business takeaway."
                )
                resp = self.llm.generate_chat_completion(
                    messages=[
                        {"role": "system", "content": "You are a Senior BI Analyst. Never invent numbers."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1
                )
                lines = [l.strip().lstrip("-*• ") for l in resp.strip().split("\n") if l.strip()]
                explanation = lines[0] if lines else f"Analysis of {title}."
                insights = lines[1:4] if len(lines) > 1 else [f"Displays {len(df_records)} data points for {title}."]
                return explanation, insights
            except Exception:
                pass

        # Robust Heuristic Grounding
        return self._heuristic_explanation(title, chart_type, x_col, y_col, df_records)

    def _heuristic_explanation(
        self,
        title: str,
        chart_type: str,
        x_col: Optional[str],
        y_col: Optional[str],
        df: pd.DataFrame
    ) -> Tuple[str, List[str]]:
        insights = []

        if y_col and y_col in df.columns and pd.api.types.is_numeric_dtype(df[y_col]):
            max_idx = df[y_col].idxmax()
            min_idx = df[y_col].idxmin()
            max_val = df.loc[max_idx, y_col]
            min_val = df.loc[min_idx, y_col]
            total_val = df[y_col].sum()
            mean_val = df[y_col].mean()

            x_lead = df.loc[max_idx, x_col] if x_col and x_col in df.columns else "Peak"
            x_min = df.loc[min_idx, x_col] if x_col and x_col in df.columns else "Lowest"

            explanation = (
                f"This {chart_type} chart details {title.lower()}, highlighting an overall total of "
                f"{total_val:,.2f} with an average of {mean_val:,.2f} across {len(df)} observations."
            )

            insights.append(f"Leader: '{x_lead}' accounts for the highest volume at {max_val:,.2f}.")
            if x_lead != x_min:
                insights.append(f"Laggard: '{x_min}' recorded the lowest volume at {min_val:,.2f}.")
            else:
                insights.append(f"Observed standard deviation of {df[y_col].std():,.2f}.")
        else:
            explanation = f"This {chart_type} visualization provides structural comparisons across {len(df)} segments in {title}."
            insights = [
                f"Captures {len(df)} categories.",
                "Enables interactive inspection of relative distributions."
            ]

        return explanation, insights
