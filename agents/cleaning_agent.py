"""Agent 3: Data Cleaning Agent."""

import logging
from typing import List, Optional, Tuple
import pandas as pd

from analytics.cleaning import apply_cleaning_actions, generate_cleaning_proposals
from schemas.analysis import CleaningAction, CleaningReport
from schemas.dataset import DatasetProfile

logger = logging.getLogger(__name__)


class CleaningAgent:
    """Specialized agent responsible for detecting data quality flaws and executing approved transformations."""

    def __init__(self):
        pass

    def evaluate(self, df: pd.DataFrame, profile: DatasetProfile) -> List[CleaningAction]:
        """Assess dataset quality and return proposed non-destructive and destructive actions."""
        logger.info(f"CleaningAgent evaluating quality for dataset {profile.filename}...")
        proposals = generate_cleaning_proposals(df, profile)
        logger.info(f"CleaningAgent generated {len(proposals)} proposed cleaning actions.")
        return proposals

    def apply(
        self,
        df: pd.DataFrame,
        actions: List[CleaningAction]
    ) -> Tuple[pd.DataFrame, CleaningReport]:
        """Apply approved cleaning transformations on an isolated copy of the dataset."""
        logger.info(f"CleaningAgent executing approved transformations...")
        cleaned_df, report = apply_cleaning_actions(df, actions)
        logger.info(f"CleaningAgent completed. Result summary: {report.summary}")
        return cleaned_df, report
