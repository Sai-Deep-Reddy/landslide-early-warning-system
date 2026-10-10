"""
weather_fix.py  —  fixes the soil-moisture bug and the train/serve mismatch.

THE BUG (in ml_pipeline/era5_weather_fetcher.py):
  The archive API (ERA5-Land) does NOT have soil_moisture_0_to_1cm / 1_to_3cm / ...
  Those names exist only in the FORECAST API. The archive returned nothing, so the code
  silently fell back to:  0.385 if month in Jun-Sep else 0.23.
  => every "soil moisture" value in training is just a MONTH FLAG.
  => the model's top-2 "features" (soil_10_40cm, soil_0_10cm) are the calendar.

THE FIX:
  * Archive (training, replay): soil_moisture_0_to_7cm, soil_moisture_7_to_28cm
  * Forecast (live)           : soil_moisture_0_to_1cm ... 9_to_27cm
  * Convert BOTH to one comparable quantity: depth-weighted mean over ~0-28 cm.
  * NEVER fall back silently. Missing data -> None -> sample is dropped and counted.
"""
from __future__ import annotations

import datetime as dt
from typing import Dict, List, Optional

import numpy as np
import requests

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

ARCHIVE_SOIL = {"soil_moisture_0_to_7cm": 7, "soil_moisture_7_to_28cm": 21}           # thickness cm
FORECAST_SOIL = {"soil_moisture_0_to_1cm": 1, "soil_moisture_1_to_3cm": 2,
                 "soil_moisture_3_to_9cm": 6, "soil_moisture_9_to_27cm": 18}


def _weighted_soil(hourly: Dict, layers: Dict[str, int], idx: int) -> Optional[float]:
    vals, wts = [], []
    for name, thick in layers.items():
        series = hourly.get(name) or []
        if idx < len(series) and series[idx] is not None:
            vals.append(float(series[idx]))
            wts.append(thick)
    if not vals or sum(wts) < 0.8 * sum(layers.values()):   # require most of the column
        return None
    return float(np.average(vals, weights=wts))


def fetch_archive(lat: float, lon: float, start: dt.date, end: dt.date, timeout: int = 30) -> Optional[Dict]:
    params = {
        "latitude": round(lat, 4), "longitude": round(lon, 4),
        "start_date": start.isoformat(), "end_date": end.isoformat(),
        "hourly": ",".join(["precipitation", *ARCHIVE_SOIL.keys()]),
        "timezone": "Asia/Kolkata",          # IST, so "day" = local calendar day
    }
    r = requests.get(ARCHIVE_URL, params=params, timeout=timeout)
    if r.status_code != 200:
        return None
    return r.json()


def features_at(lat: float, lon: float, when: dt.datetime, history_days: int = 8) -> Optional[Dict]:
    """
    Pre-event features using ONLY data strictly before `when` (local IST, naive datetime).
    If the event time is unknown (date only), pass when = 00:00 of the event date
    -> features use rain up to the previous midnight => zero post-event leakage.
    """
    data = fetch_archive(lat, lon, (when - dt.timedelta(days=history_days)).date(), when.date())
    if not data or "hourly" not in data:
        return None
    h = data["hourly"]
    times = h["time"]
    cutoff = when.strftime("%Y-%m-%dT%H:%M")
    idx = max((i for i, t in enumerate(times) if t < cutoff), default=-1)  # strictly before
    if idx < 24 * 7:
        return None
    precip = np.nan_to_num(np.array(h["precipitation"][: idx + 1], dtype=float), nan=0.0)
    soil = _weighted_soil(h, ARCHIVE_SOIL, idx)
    if soil is None:
        return None                                   # drop, do NOT invent
    daily = [float(precip[-24 * (k + 1): len(precip) - 24 * k].sum()) for k in reversed(range(7))]
    return {
        "rain_6h": float(precip[-6:].sum()),
        "rain_24h": float(precip[-24:].sum()),
        "rain_48h": float(precip[-48:].sum()),
        "rain_72h": float(precip[-72:].sum()),
        "rain_7d": float(precip[-168:].sum()),
        "max_1h_24h": float(precip[-24:].max()),
        "soil_0_28cm": round(soil, 4),
        "daily_rain_7d": daily,                         # oldest first, for physics_engine
    }


def live_features(lat: float, lon: float, timeout: int = 20) -> Optional[Dict]:
    """Live equivalent of features_at() — same feature definitions, same soil depth band."""
    params = {
        "latitude": round(lat, 4), "longitude": round(lon, 4),
        "hourly": ",".join(["precipitation", *FORECAST_SOIL.keys()]),
        "past_days": 7, "forecast_days": 2, "timezone": "Asia/Kolkata",
    }
    r = requests.get(FORECAST_URL, params=params, timeout=timeout)
    if r.status_code != 200:
        return None
    h = r.json()["hourly"]
    now = dt.datetime.now().strftime("%Y-%m-%dT%H:00")
    idx = max((i for i, t in enumerate(h["time"]) if t <= now), default=-1)
    precip = np.nan_to_num(np.array(h["precipitation"][: idx + 1], dtype=float), nan=0.0)
    soil = _weighted_soil(h, FORECAST_SOIL, idx)
    nxt = np.nan_to_num(np.array(h["precipitation"][idx + 1: idx + 25], dtype=float), nan=0.0)
    daily = [float(precip[-24 * (k + 1): len(precip) - 24 * k].sum()) for k in reversed(range(7))]
    return {
        "rain_6h": float(precip[-6:].sum()), "rain_24h": float(precip[-24:].sum()),
        "rain_48h": float(precip[-48:].sum()), "rain_72h": float(precip[-72:].sum()),
        "rain_7d": float(precip[-168:].sum()), "max_1h_24h": float(precip[-24:].max()),
        "soil_0_28cm": None if soil is None else round(soil, 4),
        "daily_rain_7d": daily, "forecast_next_24h": float(nxt.sum()),
    }


if __name__ == "__main__":
    # Run this on your laptop (needs internet). Mangan, the evening before the June 2024 event.
    f = features_at(27.5042, 88.5284, dt.datetime(2024, 6, 13, 0, 0))
    print(f if f else "No data (check internet / API)")
