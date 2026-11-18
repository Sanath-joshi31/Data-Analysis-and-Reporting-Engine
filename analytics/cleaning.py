"""Data quality assessment and non-destructive transformation module."""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from schemas.analysis import CleaningAction, CleaningReport
from schemas.dataset import DatasetProfile


def generate_cleaning_proposals(df: pd.DataFrame, profile: DatasetProfile) -> List[CleaningAction]:
    """Inspect dataframe and profile to generate intelligent cleaning recommendations."""
    actions: List[CleaningAction] = []
    action_idx = 1
    
    # 1. Duplicate rows
    if profile.duplicate_rows_count > 0:
        actions.append(CleaningAction(
            action_id=f"clean_{action_idx}",
            column=None,
            issue=f"Found {profile.duplicate_rows_count:,} duplicate rows ({profile.duplicate_rows_percentage}%)",
            action_type="drop_duplicates",
            parameters={"keep": "first"},
            is_destructive=True,
            approved=False,
            explanation="Removing identical duplicate rows prevents artificial inflation of metrics and skewing of distributions."
        ))
        action_idx += 1

    # 2. Missing values in numeric columns
    for col_name in profile.numeric_columns:
        col_prof = profile.columns.get(col_name)
        if col_prof and col_prof.missing_count > 0:
            pct = col_prof.missing_percentage
            # If missing percentage is small (< 10%), suggest median imputation (robust to outliers)
            if pct <= 15.0:
                actions.append(CleaningAction(
                    action_id=f"clean_{action_idx}",
                    column=col_name,
                    issue=f"Column '{col_name}' has {col_prof.missing_count} missing values ({pct}%)",
                    action_type="impute_median",
                    parameters={"column": col_name},
                    is_destructive=False,
                    approved=False,
                    explanation=f"Impute missing numeric values using median ({col_prof.median}) to preserve sample size without outlier bias."
                ))
                action_idx += 1
            elif pct > 70.0:
                actions.append(CleaningAction(
                    action_id=f"clean_{action_idx}",
                    column=col_name,
                    issue=f"Column '{col_name}' has excessively high missingness ({pct}%)",
                    action_type="impute_constant",
                    parameters={"column": col_name, "value": 0},
                    is_destructive=False,
                    approved=False,
                    explanation=f"Missingness is over 70%; filling with 0 or flagging prevents loss of other data."
                ))
                action_idx += 1

    # 3. Missing values in categorical columns
    for col_name in profile.categorical_columns:
        col_prof = profile.columns.get(col_name)
        if col_prof and col_prof.missing_count > 0:
            actions.append(CleaningAction(
                action_id=f"clean_{action_idx}",
                column=col_name,
                issue=f"Categorical column '{col_name}' has {col_prof.missing_count} missing values ({col_prof.missing_percentage}%)",
                action_type="impute_constant",
                parameters={"column": col_name, "value": "Unknown"},
                is_destructive=False,
                approved=False,
                explanation="Fill missing categories with 'Unknown' to retain rows while keeping group distinctions clear."
            ))
            action_idx += 1

    # 4. Whitespace trimming in text / categorical columns
    for col_name in profile.categorical_columns + profile.text_columns:
        if col_name in df.columns and df[col_name].dtype == "object":
            has_leading_trailing_space = df[col_name].dropna().astype(str).apply(
                lambda s: s != s.strip()
            ).any()
            if has_leading_trailing_space:
                actions.append(CleaningAction(
                    action_id=f"clean_{action_idx}",
                    column=col_name,
                    issue=f"Inconsistent whitespace detected in column '{col_name}'",
                    action_type="strip_whitespace",
                    parameters={"column": col_name},
                    is_destructive=False,
                    approved=True,  # Non-destructive whitespace strip
                    explanation="Trimming whitespace prevents duplicate group categories (e.g. 'South' vs 'South ')."
                ))
                action_idx += 1

    # 5. Datetime columns stored as strings
    for col_name in profile.datetime_columns:
        if col_name in df.columns and not pd.api.types.is_datetime64_any_dtype(df[col_name]):
            actions.append(CleaningAction(
                action_id=f"clean_{action_idx}",
                column=col_name,
                issue=f"Column '{col_name}' appears to be date/time but is stored as string/object",
                action_type="cast_type",
                parameters={"column": col_name, "target_type": "datetime"},
                is_destructive=False,
                approved=True,
                explanation="Casting to standard Datetime format enables monthly trend analysis and time-series aggregations."
            ))
            action_idx += 1

    return actions


def apply_cleaning_actions(
    df: pd.DataFrame, 
    actions: List[CleaningAction]
) -> Tuple[pd.DataFrame, CleaningReport]:
    """Execute approved cleaning actions on a deep copy of the DataFrame."""
    cleaned_df = df.copy()
    applied_count = 0
    issues_detected: List[str] = []
    
    orig_rows, orig_cols = int(df.shape[0]), int(df.shape[1])
    
    for action in actions:
        issues_detected.append(action.issue)
        if not action.approved:
            continue
            
        try:
            if action.action_type == "drop_duplicates":
                keep = action.parameters.get("keep", "first")
                cleaned_df = cleaned_df.drop_duplicates(keep=keep)
                applied_count += 1
                
            elif action.action_type == "impute_median":
                col = action.parameters.get("column")
                if col in cleaned_df.columns:
                    med = cleaned_df[col].median()
                    cleaned_df[col] = cleaned_df[col].fillna(med)
                    applied_count += 1
                    
            elif action.action_type == "impute_mean":
                col = action.parameters.get("column")
                if col in cleaned_df.columns:
                    mean_val = cleaned_df[col].mean()
                    cleaned_df[col] = cleaned_df[col].fillna(mean_val)
                    applied_count += 1
                    
            elif action.action_type == "impute_constant":
                col = action.parameters.get("column")
                val = action.parameters.get("value", "Unknown")
                if col in cleaned_df.columns:
                    cleaned_df[col] = cleaned_df[col].fillna(val)
                    applied_count += 1
                    
            elif action.action_type == "strip_whitespace":
                col = action.parameters.get("column")
                if col in cleaned_df.columns and cleaned_df[col].dtype == "object":
                    cleaned_df[col] = cleaned_df[col].astype(str).str.strip()
                    applied_count += 1
                    
            elif action.action_type == "cast_type":
                col = action.parameters.get("column")
                target = action.parameters.get("target_type")
                if col in cleaned_df.columns:
                    if target == "datetime":
                        cleaned_df[col] = pd.to_datetime(cleaned_df[col], errors="coerce", format="mixed")
                    elif target == "numeric":
                        cleaned_df[col] = pd.to_numeric(cleaned_df[col], errors="coerce")
                    applied_count += 1
                    
            elif action.action_type == "drop_na_rows":
                col = action.parameters.get("column")
                if col and col in cleaned_df.columns:
                    cleaned_df = cleaned_df.dropna(subset=[col])
                else:
                    cleaned_df = cleaned_df.dropna()
                applied_count += 1
                
        except Exception as err:
            action.explanation += f" (Execution error: {str(err)})"
            
    new_rows, new_cols = int(cleaned_df.shape[0]), int(cleaned_df.shape[1])
    
    summary = (
        f"Applied {applied_count} of {len(actions)} proposed transformations. "
        f"Shape changed from ({orig_rows}, {orig_cols}) to ({new_rows}, {new_cols})."
    )
    
    report = CleaningReport(
        detected_issues=issues_detected,
        actions=actions,
        original_row_count=orig_rows,
        original_column_count=orig_cols,
        cleaned_row_count=new_rows,
        cleaned_column_count=new_cols,
        summary=summary
    )
    
    return cleaned_df, report
