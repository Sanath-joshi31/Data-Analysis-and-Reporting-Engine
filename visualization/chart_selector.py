"""Chart type recommendation and selector based on analytical queries and column dtypes."""

from typing import List, Optional


class ChartSelector:
    """Selects best visualization type for a given question and column configuration."""

    @staticmethod
    def recommend(
        question: str,
        numeric_columns: List[str],
        categorical_columns: List[str],
        datetime_columns: List[str]
    ) -> str:
        q = question.lower()
        if any(w in q for w in ["trend", "forecast", "monthly", "over time", "history"]):
            return "line"
        if any(w in q for w in ["correlation", "relationship", "vs", "versus"]):
            return "scatter" if len(numeric_columns) >= 2 else "bar"
        if any(w in q for w in ["distribution", "histogram", "spread", "frequency"]):
            return "histogram"
        if any(w in q for w in ["outlier", "spread", "box"]):
            return "box"
        if any(w in q for w in ["share", "composition", "breakdown"]) and len(categorical_columns) > 0:
            return "bar"
        return "bar"
