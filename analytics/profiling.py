"""Dataset profiling engine for Autonomous Data Analyst AI."""

import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from schemas.dataset import ColumnProfile, DatasetProfile


def load_dataset(file_path: Union[str, Path]) -> pd.DataFrame:
    """Load a dataset from CSV, Excel, JSON, or Parquet with robust type inference."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = path.suffix.lower()
    if suffix in [".csv", ".txt"]:
        # Try reading with utf-8 first, fallback to latin-1
        try:
            return pd.read_csv(path, low_memory=False)
        except UnicodeDecodeError:
            return pd.read_csv(path, encoding="latin-1", low_memory=False)
    elif suffix in [".xlsx", ".xls"]:
        return pd.read_excel(path)
    elif suffix == ".parquet":
        return pd.read_parquet(path)
    elif suffix == ".json":
        try:
            return pd.read_json(path)
        except ValueError:
            return pd.read_json(path, lines=True)
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Supported formats: CSV, Excel, Parquet, JSON.")


def infer_column_type(series: pd.Series) -> str:
    """Infer high-level column category: numeric, datetime, categorical, text, or boolean."""
    # Check if boolean
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    
    # Check if numeric
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    
    # Check if already datetime
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    
    # Try converting sample of non-null string values to datetime
    non_null_samples = series.dropna().astype(str).head(50)
    if not non_null_samples.empty:
        try:
            converted = pd.to_datetime(non_null_samples, errors="coerce", format="mixed")
            if converted.notna().mean() > 0.8:
                return "datetime"
        except Exception:
            pass

    # Check text vs categorical based on uniqueness ratio and average string length
    if pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series):
        non_null = series.dropna()
        if len(non_null) == 0:
            return "categorical"
        unique_ratio = non_null.nunique() / len(non_null)
        avg_str_len = non_null.astype(str).str.len().mean()
        if avg_str_len > 40 and unique_ratio > 0.5:
            return "text"
        return "categorical"

    return "categorical"


def calculate_outliers_iqr(series: pd.Series) -> int:
    """Calculate the number of IQR outliers for a numeric series."""
    clean = series.dropna()
    if len(clean) < 4:
        return 0
    q25 = clean.quantile(0.25)
    q75 = clean.quantile(0.75)
    iqr = q75 - q25
    if iqr == 0:
        return 0
    lower_bound = q25 - 1.5 * iqr
    upper_bound = q75 + 1.5 * iqr
    return int(((clean < lower_bound) | (clean > upper_bound)).sum())


def profile_column(series: pd.Series, col_name: str) -> ColumnProfile:
    """Generate detailed statistics and metadata for a single column."""
    total_count = len(series)
    missing_count = int(series.isna().sum())
    missing_percentage = round((missing_count / total_count * 100.0) if total_count > 0 else 0.0, 2)
    
    non_null = series.dropna()
    unique_count = int(non_null.nunique())
    unique_percentage = round((unique_count / total_count * 100.0) if total_count > 0 else 0.0, 2)
    
    is_pk_candidate = (missing_count == 0) and (unique_count == total_count) and (total_count > 0)
    
    # Representative sample values
    sample_values = [
        val if not isinstance(val, (np.generic, pd.Timestamp)) else str(val)
        for val in non_null.head(5).tolist()
    ]
    
    inferred_type = infer_column_type(series)
    
    # Numeric metrics
    min_val, max_val, mean_val, median_val, std_val = None, None, None, None, None
    q25, q75, outliers = None, None, None
    
    if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
        if len(non_null) > 0:
            min_val = float(non_null.min())
            max_val = float(non_null.max())
            mean_val = float(round(non_null.mean(), 4))
            median_val = float(round(non_null.median(), 4))
            std_val = float(round(non_null.std(), 4)) if len(non_null) > 1 else 0.0
            q25 = float(round(non_null.quantile(0.25), 4))
            q75 = float(round(non_null.quantile(0.75), 4))
            outliers = calculate_outliers_iqr(non_null)
            
    # Categorical top values
    top_values = None
    if inferred_type in ["categorical", "boolean", "text"] and len(non_null) > 0:
        val_counts = non_null.astype(str).value_counts().head(5).to_dict()
        top_values = {str(k): int(v) for k, v in val_counts.items()}
        
    return ColumnProfile(
        name=col_name,
        dtype=str(series.dtype),
        inferred_type=inferred_type,
        total_count=total_count,
        missing_count=missing_count,
        missing_percentage=missing_percentage,
        unique_count=unique_count,
        unique_percentage=unique_percentage,
        is_primary_key_candidate=is_pk_candidate,
        sample_values=sample_values,
        min_value=min_val,
        max_value=max_val,
        mean=mean_val,
        median=median_val,
        std_dev=std_val,
        quartile_25=q25,
        quartile_75=q75,
        outliers_count=outliers,
        most_frequent_values=top_values
    )


def profile_dataset(
    file_path: Union[str, Path], 
    filename: Optional[str] = None, 
    dataset_id: Optional[str] = None
) -> DatasetProfile:
    """Generate a complete DatasetProfile from a file."""
    df = load_dataset(file_path)
    return profile_dataframe(
        df=df,
        filename=filename or Path(file_path).name,
        dataset_id=dataset_id or str(uuid.uuid4())
    )


def profile_dataframe(
    df: pd.DataFrame, 
    filename: str = "dataset.csv", 
    dataset_id: Optional[str] = None
) -> DatasetProfile:
    """Profile an in-memory pandas DataFrame."""
    if dataset_id is None:
        dataset_id = str(uuid.uuid4())
        
    row_count = int(df.shape[0])
    col_count = int(df.shape[1])
    memory_mb = round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2)
    
    columns_profile: Dict[str, ColumnProfile] = {}
    numeric_cols: List[str] = []
    categorical_cols: List[str] = []
    datetime_cols: List[str] = []
    text_cols: List[str] = []
    potential_pks: List[str] = []
    
    total_missing_cells = int(df.isna().sum().sum())
    total_cells = row_count * col_count if row_count * col_count > 0 else 1
    total_missing_percentage = round((total_missing_cells / total_cells) * 100.0, 2)
    
    duplicate_rows = int(df.duplicated().sum()) if row_count > 0 else 0
    duplicate_percentage = round((duplicate_rows / row_count * 100.0) if row_count > 0 else 0.0, 2)
    
    for col in df.columns:
        col_str = str(col)
        prof = profile_column(df[col], col_str)
        columns_profile[col_str] = prof
        
        if prof.inferred_type == "numeric":
            numeric_cols.append(col_str)
        elif prof.inferred_type == "datetime":
            datetime_cols.append(col_str)
        elif prof.inferred_type == "text":
            text_cols.append(col_str)
        else:
            categorical_cols.append(col_str)
            
        if prof.is_primary_key_candidate:
            potential_pks.append(col_str)
            
    # Calculate health score (100 minus penalties for missingness and duplicates)
    missing_penalty = min(total_missing_percentage * 1.5, 50.0)
    dup_penalty = min(duplicate_percentage * 2.0, 30.0)
    health_score = max(0.0, round(100.0 - missing_penalty - dup_penalty, 1))
    
    summary = (
        f"Dataset contains {row_count:,} rows and {col_count} columns ({len(numeric_cols)} numeric, "
        f"{len(categorical_cols)} categorical, {len(datetime_cols)} datetime). "
        f"Overall missingness is {total_missing_percentage}% ({total_missing_cells:,} empty cells), "
        f"and duplicate rows represent {duplicate_percentage}% ({duplicate_rows:,} rows). "
        f"Dataset health rating: {health_score}/100."
    )
    
    return DatasetProfile(
        dataset_id=dataset_id,
        filename=filename,
        row_count=row_count,
        column_count=col_count,
        memory_usage_mb=memory_mb,
        columns=columns_profile,
        numeric_columns=numeric_cols,
        categorical_columns=categorical_cols,
        datetime_columns=datetime_cols,
        text_columns=text_cols,
        total_missing_cells=total_missing_cells,
        total_missing_percentage=total_missing_percentage,
        duplicate_rows_count=duplicate_rows,
        duplicate_rows_percentage=duplicate_percentage,
        potential_primary_keys=potential_pks,
        health_score=health_score,
        summary=summary
    )
