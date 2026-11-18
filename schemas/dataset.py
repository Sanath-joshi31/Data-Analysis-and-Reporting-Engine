"""Pydantic schemas for dataset profiling and structural metadata."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ColumnProfile(BaseModel):
    """Detailed profile of a single dataset column."""
    name: str = Field(description="Name of the column")
    dtype: str = Field(description="Data type detected by Pandas (e.g. int64, float64, object, datetime64)")
    inferred_type: str = Field(description="High-level category: 'numeric', 'categorical', 'datetime', 'text', 'boolean'")
    total_count: int = Field(description="Total number of values including missing")
    missing_count: int = Field(default=0, description="Number of null / missing / NaN entries")
    missing_percentage: float = Field(default=0.0, description="Percentage of missing values (0-100)")
    unique_count: int = Field(default=0, description="Number of unique values")
    unique_percentage: float = Field(default=0.0, description="Percentage of unique values (0-100)")
    is_primary_key_candidate: bool = Field(default=False, description="True if unique and has zero nulls")
    sample_values: List[Any] = Field(default_factory=list, description="Small sample of representative non-null values")
    
    # Numeric column statistics
    min_value: Optional[float] = Field(default=None, description="Minimum numeric value")
    max_value: Optional[float] = Field(default=None, description="Maximum numeric value")
    mean: Optional[float] = Field(default=None, description="Arithmetic mean")
    median: Optional[float] = Field(default=None, description="Median value")
    std_dev: Optional[float] = Field(default=None, description="Standard deviation")
    quartile_25: Optional[float] = Field(default=None, description="25th percentile (Q1)")
    quartile_75: Optional[float] = Field(default=None, description="75th percentile (Q3)")
    outliers_count: Optional[int] = Field(default=None, description="Count of IQR-based outlier values")
    
    # Categorical / Text statistics
    most_frequent_values: Optional[Dict[str, int]] = Field(
        default=None, 
        description="Top 5 most frequent values and their frequencies"
    )


class DatasetProfile(BaseModel):
    """Complete structural and statistical profile of an analyzed dataset."""
    dataset_id: str = Field(description="Unique identifier for the dataset session")
    filename: str = Field(description="Original uploaded file name")
    row_count: int = Field(description="Total number of rows in the dataset")
    column_count: int = Field(description="Total number of columns in the dataset")
    memory_usage_mb: float = Field(default=0.0, description="Memory footprint in megabytes")
    
    columns: Dict[str, ColumnProfile] = Field(
        default_factory=dict, 
        description="Dictionary mapping column names to their ColumnProfile"
    )
    
    numeric_columns: List[str] = Field(default_factory=list, description="Names of all numeric columns")
    categorical_columns: List[str] = Field(default_factory=list, description="Names of categorical columns")
    datetime_columns: List[str] = Field(default_factory=list, description="Names of detected datetime columns")
    text_columns: List[str] = Field(default_factory=list, description="Names of free-form text columns")
    
    total_missing_cells: int = Field(default=0, description="Total missing cells across entire dataset")
    total_missing_percentage: float = Field(default=0.0, description="Overall missing cell percentage")
    duplicate_rows_count: int = Field(default=0, description="Total number of duplicate rows")
    duplicate_rows_percentage: float = Field(default=0.0, description="Duplicate rows percentage")
    potential_primary_keys: List[str] = Field(default_factory=list, description="Candidate primary key columns")
    
    health_score: float = Field(
        default=100.0, 
        description="Data health score from 0 (very poor) to 100 (clean, no missing/duplicates)"
    )
    summary: str = Field(
        default="", 
        description="Concise natural language summary of the dataset structure and cleanliness"
    )
