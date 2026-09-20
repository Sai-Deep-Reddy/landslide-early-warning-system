"""
Simulation, Historical Replay & Dynamic Model Validation Router
Endpoints: /api/simulate, /api/replay, /api/validation
"""

import os
import json
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from app.config import DATA_DIR, METRICS_PATH, PILOT_STATIONS
from app.services.risk_engine import risk_engine

router = APIRouter(tags=["What-If Simulation, Historical Replay & Validation"])


class SimulationRequest(BaseModel):
    rain_boost_pct: float = Field(30.0, description="Percentage increase in rainfall (e.g. 30 for +30%)")
    target_station_ids: Optional[List[str]] = Field(None, description="Optional list of station IDs to simulate")


@router.post("/simulate")
def run_what_if_simulation(payload: SimulationRequest) -> Dict[str, Any]:
    """
    Executes 'What-If' scenario stress-testing across Himalayan corridors
    using dynamic rainfall surge multipliers.
    """
    stations_to_eval = PILOT_STATIONS
    if payload.target_station_ids:
        stations_to_eval = [s for s in PILOT_STATIONS if s["id"] in payload.target_station_ids]

    boosted_results = []
    escalated_stations = []

    for stn in stations_to_eval:
        base = risk_engine.calculate_risk(lat=stn["lat"], lon=stn["lon"], rain_boost_pct=0.0)
        boosted = risk_engine.calculate_risk(lat=stn["lat"], lon=stn["lon"], rain_boost_pct=payload.rain_boost_pct)

        is_escalated = base["risk_level"] != boosted["risk_level"]
        delta_score = round(boosted["risk_score"] - base["risk_score"], 2)

        stn_entry = {
            "station_id": stn["id"],
            "station_name": stn["name"],
            "district": stn["district"],
            "lat": stn["lat"],
            "lon": stn["lon"],
            "slope_deg": stn["slope_deg"],
            "baseline_score": base["risk_score"],
            "baseline_level": base["risk_level"],
            "baseline_ml_prob": base["ml_probability"],
            "simulated_score": boosted["risk_score"],
            "simulated_ml_prob": boosted["ml_probability"],
            "simulated_level": boosted["risk_level"],
            "score_delta": delta_score,
            "simulated_rain_24h": boosted["factors"]["rain_24h"],
            "simulated_factors": boosted["factors"],
            "simulated_note": boosted["note"],
            "escalated": is_escalated
        }
        boosted_results.append(stn_entry)
        if is_escalated or boosted["risk_level"] in ["HIGH", "CRITICAL"]:
            escalated_stations.append(stn_entry)

    return {
        "simulation_parameter": {
            "rain_boost_percentage": payload.rain_boost_pct,
            "total_stations_evaluated": len(stations_to_eval),
            "critical_or_escalated_count": len(escalated_stations)
        },
        "summary": f"Scenario Simulation (+{payload.rain_boost_pct}% rainfall): {len(escalated_stations)} vulnerable corridors reached elevated hazard thresholds.",
        "station_results": boosted_results,
        "critical_escalations": escalated_stations
    }


@router.get("/replay")
def get_historical_replay_events() -> List[Dict[str, Any]]:
    """
    Returns benchmark historical landslide events with hourly timeline progressions
    for judicial demonstration of warning lead-time.
    """
    test_path = os.path.join(DATA_DIR, "test_events.json")
    if not os.path.exists(test_path):
        return []

    with open(test_path, "r", encoding="utf-8") as f:
        events = json.load(f)
    return events


@router.get("/validation")
def get_model_validation_metrics() -> Dict[str, Any]:
    """
    Returns genuine empirical validation metrics computed by the ML pipeline on the holdout test set.
    Dynamically loads from metrics.json (generated from chronological 2018-2023 vs 2024 split).
    """
    if os.path.exists(METRICS_PATH):
        try:
            with open(METRICS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            pass

    raise HTTPException(
        status_code=500,
        detail="Validation metrics not available. Run `python ml_pipeline/train_and_validate.py` to train models and generate metrics."
    )
