"""
Negative Sampling Engine for Landslide Early-Warning Modeling
Generates non-landslide control points across Sikkim using spatial exclusion buffers (>= 2.0 km),
DEM geomorphology, and real ECMWF ERA5-Land environmental observations.
"""

import sys
import os
import math
import random
import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.services.terrain_service import terrain_service
from ml_pipeline.era5_weather_fetcher import extract_pre_event_telemetry


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance in kilometers between two coordinates."""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2.0) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def generate_negative_samples(
    positive_df: pd.DataFrame,
    neg_to_pos_ratio: float = 2.0,
    min_exclusion_km: float = 2.0,
    seed: int = 42
) -> pd.DataFrame:
    """
    Generates non-landslide controls in Sikkim by pairing spatial buffer exclusion
    with real DEM topography and genuine Open-Meteo ERA5-Land reanalysis observations.
    """
    random.seed(seed)
    np.random.seed(seed)

    num_negatives = int(len(positive_df) * neg_to_pos_ratio)
    known_points = positive_df[["lat", "lon"]].values

    # Sikkim Pilot Spatial Bounding Box
    lat_min, lat_max = 27.10, 28.00
    lon_min, lon_max = 88.10, 88.85

    negative_records = []
    attempts = 0
    max_attempts = num_negatives * 30

    years = positive_df["year"].tolist()
    candidate_specs = []

    while len(candidate_specs) < num_negatives and attempts < max_attempts:
        attempts += 1
        cand_lat = round(random.uniform(lat_min, lat_max), 4)
        cand_lon = round(random.uniform(lon_min, lon_max), 4)

        # Check spatial exclusion buffer against all known landslide occurrences
        too_close = False
        for k_lat, k_lon in known_points:
            if haversine_km(cand_lat, cand_lon, k_lat, k_lon) < min_exclusion_km:
                too_close = True
                break

        if too_close:
            continue

        year = random.choice(years)
        month = random.choice([5, 6, 7, 8, 9, 10])
        day = random.randint(1, 28)
        hour = random.choice([2, 6, 10, 14, 18, 22])
        event_date_str = f"{year:04d}-{month:02d}-{day:02d}"
        cand_dt = datetime.strptime(f"{event_date_str} {hour:02d}:00", "%Y-%m-%d %H:%M")

        candidate_specs.append({
            "lat": cand_lat,
            "lon": cand_lon,
            "year": year,
            "cand_dt": cand_dt,
            "datetime_str": cand_dt.strftime("%Y-%m-%dT%H:00:00Z")
        })

    # Parallel prefetch ERA5 telemetry for all negative candidates
    from ml_pipeline.era5_weather_fetcher import prefetch_batch_telemetry
    print(f"[DATA] Prefetching ERA5 telemetry for {len(candidate_specs)} negative controls...")
    prefetch_batch_telemetry([(s["lat"], s["lon"], s["cand_dt"]) for s in candidate_specs], max_workers=15)

    for i, s in enumerate(candidate_specs):
        cand_lat = s["lat"]
        cand_lon = s["lon"]
        year = s["year"]
        cand_dt = s["cand_dt"]
        datetime_str = s["datetime_str"]

        # Extract real physical terrain from Copernicus 30m DEM
        terrain = terrain_service.compute_terrain_metrics(cand_lat, cand_lon)
        slope = terrain["slope_deg"]
        elevation = terrain["elevation_m"]
        suscep = terrain["susceptibility"]
        suscep_factor = terrain["suscep_factor"]

        # Extract genuine ERA5-Land weather & multi-depth soil moisture observations
        weather = extract_pre_event_telemetry(cand_lat, cand_lon, cand_dt)

        negative_records.append({
            "id": f"NEG-SK-{year}-{len(negative_records)+1:03d}",
            "event_date": cand_dt.date(),
            "datetime": pd.to_datetime(datetime_str),
            "year": year,
            "district": terrain.get("district", "Sikkim Terrain Matrix"),
            "location_name": f"Stable Slope Sector ({cand_lat}, {cand_lon})",
            "lat": cand_lat,
            "lon": cand_lon,
            "elevation_m": elevation,
            "slope_deg": slope,
            "type": "No Landslide (Stable Control)",
            "severity": "None",
            "trigger_rain_6h_mm": weather["rain_6h"],
            "trigger_rain_24h_mm": weather["rain_24h"],
            "trigger_rain_48h_mm": weather["rain_48h"],
            "trigger_rain_7d_mm": weather["rain_7d"],
            "soil_moisture_0_10cm": weather["soil_0_10cm"],
            "soil_moisture_10_40cm": weather["soil_10_40cm"],
            "soil_moisture_27_81cm": weather.get("soil_27_81cm", 0.30),
            "susceptibility": suscep,
            "suscep_factor": suscep_factor,
            "damage_summary": "No slope failure recorded at this coordinate/timestamp.",
            "gsi_inventory_code": "NON-EVENT-CONTROL",
            "label": 0
        })

    neg_df = pd.DataFrame(negative_records)
    neg_df = neg_df.sort_values("datetime").reset_index(drop=True)
    return neg_df


if __name__ == "__main__":
    from ml_pipeline.data_loader import load_gsi_events
    pos_df, _ = load_gsi_events()
    pos_df["label"] = 1
    neg_df = generate_negative_samples(pos_df, neg_to_pos_ratio=2.0)
    print(f"Generated {len(neg_df)} real-observation negative samples with >2km spatial separation.")
    print("Negative rain_24h stats:\n", neg_df["trigger_rain_24h_mm"].describe())
    print("Negative soil_0_10cm stats:\n", neg_df["soil_moisture_0_10cm"].describe())
