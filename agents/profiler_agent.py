"""Agent 1: Dataset Profiler Agent."""

import logging
from pathlib import Path
from typing import Optional, Union
import pandas as pd

from analytics.profiling import load_dataset, profile_dataframe, profile_dataset
from schemas.dataset import DatasetProfile

logger = logging.getLogger(__name__)


class DatasetProfilerAgent:
    """Specialized agent responsible for structural, type, and statistical dataset profiling."""

    def __init__(self):
        pass

    def run(
        self,
        file_path_or_df: Union[str, Path, pd.DataFrame],
        filename: Optional[str] = None,
        dataset_id: Optional[str] = None
    ) -> DatasetProfile:
        """Inspect dataset, extract column properties, detect missingness/duplicates/outliers, and return DatasetProfile."""
        logger.info(f"DatasetProfilerAgent starting profile for {filename or 'dataframe'}...")
        if isinstance(file_path_or_df, pd.DataFrame):
            profile = profile_dataframe(
                df=file_path_or_df,
                filename=filename or "dataset.csv",
                dataset_id=dataset_id
            )
        else:
            profile = profile_dataset(
                file_path=file_path_or_df,
                filename=filename,
                dataset_id=dataset_id
            )

        logger.info(
            f"Profiling complete. Shape: ({profile.row_count}, {profile.column_count}), "
            f"Health Score: {profile.health_score}/100"
        )
        return profile
