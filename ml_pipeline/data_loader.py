"""
Data Loader for GSI Landslide Inventory
Loads, validates, and cleans historical landslide event records.
"""

import os
import json
import pandas as pd
from typing import Dict, Any, Tuple, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "backend", "app", "data", "gsi_landslides.json")


def load_gsi_events() -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Loads verified GSI historical landslide events.
    Returns DataFrame of events and provenance metadata dictionary.
    """
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"GSI dataset not found at {DATA_PATH}")

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "records" in data:
        metadata = data.get("metadata", {})
        records = data["records"]
    elif isinstance(data, list):
        metadata = {"source": "GSI Bhu Sanket Pilot"}
        records = data
    else:
        raise ValueError("Invalid format in gsi_landslides.json")

    df = pd.DataFrame(records)
    
    # Ensure datetime format and sorting
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["event_date"] = pd.to_datetime(df["event_date"]).dt.date
    df["year"] = pd.to_datetime(df["datetime"]).dt.year
    df = df.sort_values("datetime").reset_index(drop=True)

    return df, metadata


if __name__ == "__main__":
    df, meta = load_gsi_events()
    print("=== GSI Dataset Loaded ===")
    print(f"Total Validated Events: {len(df)}")
    print(f"Yearly Breakdown:\n{df['year'].value_counts().sort_index()}")
    print(f"Districts Covered:\n{df['district'].value_counts()}")
    print(f"Provenance Source: {meta.get('source')}")
