"""
Configuration and spatial metadata for Landslide Early-Warning System (LEWS)
Piloting in Sikkim (Eastern Himalayas, India) - SIH PS 26001
"""

import os
from typing import Dict, Any, List

APP_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(APP_DIR)
DATA_DIR = os.path.join(APP_DIR, "data")
MODELS_DIR = os.path.join(DATA_DIR, "models")
METRICS_PATH = os.path.join(DATA_DIR, "metrics.json")
MODEL_PATH = os.path.join(MODELS_DIR, "rf_model.joblib")
MODEL_META_PATH = os.path.join(MODELS_DIR, "model_metadata.json")

# Environment & API Key Configuration
IMD_API_KEY = os.getenv("IMD_API_KEY", "")
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN", "")
NASA_EARTHDATA_TOKEN = os.getenv("NASA_EARTHDATA_TOKEN", "")
ALLOWED_ORIGINS = [
    origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000").split(",") if origin.strip()
]
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Bounding box for Sikkim pilot region
SIKKIM_BBOX = {
    "min_lat": 27.05,
    "max_lat": 28.15,
    "min_lon": 88.00,
    "max_lon": 88.95,
}

# Major observation stations and vulnerable corridors in Sikkim
PILOT_STATIONS: List[Dict[str, Any]] = [
    {
        "id": "STN-GTK",
        "name": "Gangtok (East Sikkim)",
        "district": "Gangtok",
        "lat": 27.3389,
        "lon": 88.6065,
        "elevation_m": 1650,
        "slope_deg": 34.5,
        "susceptibility": "High",
        "critical_infrastructure": "NH-10 Highway Corridor, Capital Urban Sector",
    },
    {
        "id": "STN-GYL",
        "name": "Gyalshing / Pelling (West Sikkim)",
        "district": "Gyalshing",
        "lat": 27.2917,
        "lon": 88.2394,
        "elevation_m": 1920,
        "slope_deg": 38.2,
        "susceptibility": "High",
        "critical_infrastructure": "Pelling-Gyalshing State Highway",
    },
    {
        "id": "STN-MGN",
        "name": "Mangan (North Sikkim)",
        "district": "Mangan",
        "lat": 27.5042,
        "lon": 88.5284,
        "elevation_m": 1310,
        "slope_deg": 41.0,
        "susceptibility": "High",
        "critical_infrastructure": "North Sikkim Highway (BRO Swastik Project)",
    },
    {
        "id": "STN-NMC",
        "name": "Namchi (South Sikkim)",
        "district": "Namchi",
        "lat": 27.1656,
        "lon": 88.3582,
        "elevation_m": 1315,
        "slope_deg": 29.8,
        "susceptibility": "Moderate",
        "critical_infrastructure": "Namchi-Jorethang Road",
    },
    {
        "id": "STN-PKY",
        "name": "Pakyong (Pakyong District)",
        "district": "Pakyong",
        "lat": 27.2372,
        "lon": 88.5916,
        "elevation_m": 1400,
        "slope_deg": 36.4,
        "susceptibility": "High",
        "critical_infrastructure": "Pakyong Greenfield Airport Link Road",
    },
    {
        "id": "STN-SRG",
        "name": "Soreng (Soreng District)",
        "district": "Soreng",
        "lat": 27.1627,
        "lon": 88.1969,
        "elevation_m": 1540,
        "slope_deg": 31.2,
        "susceptibility": "Moderate",
        "critical_infrastructure": "Soreng-Kaluk Valley Route",
    },
    {
        "id": "STN-CHT",
        "name": "Chungthang Valley",
        "district": "Mangan",
        "lat": 27.6048,
        "lon": 88.6473,
        "elevation_m": 1790,
        "slope_deg": 44.5,
        "susceptibility": "High",
        "critical_infrastructure": "Teesta Hydro Project & Lachen-Lachung Fork",
    },
    {
        "id": "STN-SGT",
        "name": "Singtam (Teesta Basin)",
        "district": "Gangtok",
        "lat": 27.2367,
        "lon": 88.4983,
        "elevation_m": 350,
        "slope_deg": 28.0,
        "susceptibility": "Moderate",
        "critical_infrastructure": "Teesta River Basin Corridor",
    },
    {
        "id": "STN-RVG",
        "name": "Ravangla Ridge",
        "district": "Namchi",
        "lat": 27.3072,
        "lon": 88.3639,
        "elevation_m": 2100,
        "slope_deg": 35.8,
        "susceptibility": "High",
        "critical_infrastructure": "Tarku-Ravangla-Legship Road",
    },
    {
        "id": "STN-RNG",
        "name": "Rangpo Border Gate",
        "district": "Pakyong",
        "lat": 27.1772,
        "lon": 88.5306,
        "elevation_m": 330,
        "slope_deg": 25.1,
        "susceptibility": "Low",
        "critical_infrastructure": "NH-10 Sikkim-Bengal Entry Gate",
    }
]

DEFAULT_MODEL_WEIGHTS = {
    "rain_24h": 0.35,      # Normalized against 100mm threshold
    "rain_7d": 0.20,       # Normalized against 300mm antecedent threshold
    "slope": 0.20,         # Normalized against 35° threshold
    "soil_moisture": 0.15, # Normalized against 0.50 m³/m³ saturation
    "susceptibility": 0.10 # GSI zone factor (High=1.0, Med=0.5, Low=0.1)
}

# Operational Calibrated Thresholds
RISK_THRESHOLDS = {
    "LOW": 0.30,
    "MODERATE": 0.55,
    "HIGH": 0.75,
    "CRITICAL": 1.00
}
