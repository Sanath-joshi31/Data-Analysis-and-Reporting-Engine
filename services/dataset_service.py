"""Dataset management service for uploading, caching, and loading analytical datasets."""

import os
import shutil
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from config.settings import get_settings
from database.repository import Repository
from schemas.dataset import DatasetProfile
from analytics.profiling import load_dataset, profile_dataset


class DatasetService:
    """Manages file storage, dataset profiling, and retrieval."""

    def __init__(self, repository: Optional[Repository] = None):
        self.settings = get_settings()
        self.repo = repository or Repository()
        self._profiles_cache: Dict[str, DatasetProfile] = {}

    def save_uploaded_file(self, uploaded_file, original_filename: str) -> Tuple[str, Path, DatasetProfile]:
        """Save an uploaded file, profile it, and persist metadata."""
        dataset_id = str(uuid.uuid4())
        suffix = Path(original_filename).suffix.lower()
        if suffix not in [".csv", ".xlsx", ".xls", ".parquet", ".json"]:
            raise ValueError(f"Unsupported file format: {suffix}. Allowed: CSV, Excel, Parquet, JSON.")

        dest_filename = f"{dataset_id}_{original_filename}"
        dest_path = self.settings.uploads_path / dest_filename

        # Write uploaded file buffer to destination
        with open(dest_path, "wb") as f:
            if hasattr(uploaded_file, "getbuffer"):
                f.write(uploaded_file.getbuffer())
            elif hasattr(uploaded_file, "read"):
                f.write(uploaded_file.read())
            else:
                f.write(uploaded_file)

        # Profile the dataset
        profile = profile_dataset(dest_path, filename=original_filename, dataset_id=dataset_id)
        self._profiles_cache[dataset_id] = profile

        # Persist in repository
        self.repo.save_dataset(
            dataset_id=dataset_id,
            filename=original_filename,
            file_path=str(dest_path),
            profile=profile
        )

        return dataset_id, dest_path, profile

    def get_dataset_profile(self, dataset_id: str) -> Optional[DatasetProfile]:
        """Retrieve dataset profile from cache or database."""
        if dataset_id in self._profiles_cache:
            return self._profiles_cache[dataset_id]

        record = self.repo.get_dataset(dataset_id)
        if record and record.profile_json:
            profile = DatasetProfile.model_validate_json(record.profile_json)
            self._profiles_cache[dataset_id] = profile
            return profile
        return None

    def get_dataset_dataframe(self, dataset_id: str) -> pd.DataFrame:
        """Load dataset DataFrame by dataset_id."""
        record = self.repo.get_dataset(dataset_id)
        if not record or not os.path.exists(record.file_path):
            raise FileNotFoundError(f"Dataset {dataset_id} file not found on disk.")
        return load_dataset(record.file_path)

    def ensure_sample_dataset(self) -> Tuple[str, Path, DatasetProfile]:
        """Generate a rich sample superstore dataset for testing and immediate exploration."""
        sample_path = self.settings.samples_path / "sample_superstore.csv"
        dataset_id = "sample_superstore_retail"

        if not sample_path.exists():
            np.random.seed(42)
            n_rows = 1500

            regions = ["North", "South", "East", "West"]
            categories = {
                "Technology": ["Phones", "Laptops", "Accessories", "Copiers"],
                "Furniture": ["Chairs", "Tables", "Bookcases", "Furnishings"],
                "Office Supplies": ["Binders", "Paper", "Storage", "Appliances", "Art"]
            }
            segments = ["Consumer", "Corporate", "Home Office"]

            dates = pd.date_range(start="2024-01-01", end="2025-12-31", periods=n_rows)
            order_dates = np.random.choice(dates, n_rows)

            rows = []
            for i in range(n_rows):
                cat = np.random.choice(list(categories.keys()))
                sub_cat = np.random.choice(categories[cat])
                reg = np.random.choice(regions, p=[0.25, 0.35, 0.20, 0.20])
                seg = np.random.choice(segments, p=[0.50, 0.30, 0.20])

                base_price = (
                    np.random.uniform(200, 1200) if cat == "Technology"
                    else np.random.uniform(80, 500) if cat == "Furniture"
                    else np.random.uniform(10, 150)
                )
                qty = int(np.random.choice([1, 2, 3, 4, 5, 8], p=[0.3, 0.3, 0.2, 0.1, 0.07, 0.03]))
                discount = float(np.random.choice([0.0, 0.1, 0.2, 0.3, 0.5], p=[0.5, 0.25, 0.15, 0.07, 0.03]))
                sales = round(base_price * qty * (1.0 - discount), 2)

                # Profit formula with negative margin if excessive discount
                margin_factor = 0.25 - (discount * 0.7)
                profit = round(sales * margin_factor + np.random.normal(0, 5), 2)

                rows.append({
                    "Order_ID": f"ORD-{2024 + (i % 2)}-{10000 + i}",
                    "Order_Date": pd.to_datetime(order_dates[i]).strftime("%Y-%m-%d"),
                    "Customer_ID": f"CUST-{100 + (i % 250)}",
                    "Customer_Segment": seg,
                    "Region": reg,
                    "Category": cat,
                    "Sub_Category": sub_cat,
                    "Product_Name": f"{sub_cat} Model {chr(65 + (i % 10))}",
                    "Sales": sales,
                    "Quantity": qty,
                    "Discount": discount,
                    "Profit": profit,
                    "Postal_Code": int(np.random.choice([90001, 75001, 10001, 30301, 60601]))
                })

            sample_df = pd.DataFrame(rows)
            # Add a few realistic duplicate rows
            sample_df = pd.concat([sample_df, sample_df.iloc[:8]], ignore_index=True)
            # Add a few realistic missing values
            sample_df.loc[np.random.choice(sample_df.index, 12), "Postal_Code"] = np.nan
            sample_df.to_csv(sample_path, index=False)

        profile = profile_dataset(sample_path, filename="sample_superstore.csv", dataset_id=dataset_id)
        self._profiles_cache[dataset_id] = profile
        self.repo.save_dataset(
            dataset_id=dataset_id,
            filename="sample_superstore.csv",
            file_path=str(sample_path),
            profile=profile
        )

        return dataset_id, sample_path, profile
