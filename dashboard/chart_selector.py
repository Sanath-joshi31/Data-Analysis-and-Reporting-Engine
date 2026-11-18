"""Intelligent chart type selection heuristics for the Dashboard Builder."""

from typing import List, Optional
import pandas as pd


class DashboardChartSelector:
    """Evaluates dimension cardinalities, measure characteristics, and analytical goals to pick the optimal chart."""

    @staticmethod
    def select_time_series_chart(num_periods: int, has_categories: bool = False) -> str:
        if num_periods <= 4:
            return "bar"
        return "line"

    @staticmethod
    def select_categorical_chart(unique_categories: int, has_subgroups: bool = False) -> str:
        if has_subgroups:
            return "grouped_bar"
        if unique_categories <= 5:
            return "donut"
        if unique_categories <= 12:
            return "bar"
        return "horizontal_bar"

    @staticmethod
    def select_distribution_chart(sample_size: int, has_groups: bool = False) -> str:
        if has_groups:
            return "box"
        return "histogram"

    @staticmethod
    def select_relationship_chart(num_measures: int) -> str:
        if num_measures >= 3:
            return "bubble"
        return "scatter"
