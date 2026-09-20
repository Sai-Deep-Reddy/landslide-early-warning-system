"""
Multi-Scenario Decision Fusion & Scientific Decomposition Test Suite
Validates the calibrated continuous weighted fusion:
Compound Risk = 0.55 * ML_Probability + 0.45 * Physics_Hazard_Index
Risk Bands: <0.45 LOW, 0.45-0.65 MODERATE, >=0.65 HIGH, >=0.85 CRITICAL
"""

import sys
import os
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.main import app
from app.services.risk_engine import risk_engine
from app.services.terrain_service import terrain_service

client = TestClient(app)


def test_scenario_1_outside_low_dynamic():
    """1. Outside mapped GSI coverage + Low dynamic rainfall/moisture."""
    payload = {
        "lat": 27.700,
        "lon": 88.650,
        "slope_deg": 12.0,
        "elevation_m": 2200.0,
        "rain_6h": 0.0,
        "rain_24h": 2.0,
        "rain_48h": 5.0,
        "rain_7d": 18.0,
        "soil_0_10cm": 0.20,
        "soil_10_40cm": 0.18,
        "susceptibility": "Low"
    }
    res = client.post("/api/risk/manual", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["risk_level"] == "LOW"
    assert data["compound_risk"] < 0.45
    assert data["ml_probability"] < 0.40
    assert data["prediction_trace"]["static_susceptibility"]["is_inside_mapped_polygon"] is False


def test_scenario_2_outside_elevated_dynamic():
    """2. Outside mapped GSI coverage + Elevated 7-day antecedent rainfall."""
    payload = {
        "lat": 27.250,
        "lon": 88.450,
        "slope_deg": 21.8,
        "elevation_m": 461.0,
        "rain_6h": 0.7,
        "rain_24h": 9.0,
        "rain_48h": 33.2,
        "rain_7d": 150.2,
        "soil_0_10cm": 0.272,
        "soil_10_40cm": 0.262,
        "susceptibility": "Low"
    }
    res = client.post("/api/risk/manual", json=payload)
    assert res.status_code == 200
    data = res.json()
    # Continuous compound score = 0.55*0.731 + 0.45*0.45 ~ 0.60 (MODERATE band, not falsely forced to Low or High)
    assert data["risk_level"] == "MODERATE"
    assert 0.45 <= data["compound_risk"] < 0.65
    assert data["ml_probability"] > 0.60
    assert "outside mapped gsi susceptibility polygons" in data["note"].lower()


def test_scenario_3_inside_low_suscep_elevated():
    """3. Inside low susceptibility corridor + Elevated dynamic rainfall."""
    payload = {
        "lat": 27.1772,  # Rangpo Border Gate (Low Susceptibility Mapped Polygon)
        "lon": 88.5306,
        "slope_deg": 18.0,
        "elevation_m": 373.0,
        "rain_6h": 8.0,
        "rain_24h": 32.0,
        "rain_48h": 55.0,
        "rain_7d": 140.0,
        "soil_0_10cm": 0.32,
        "soil_10_40cm": 0.30,
        "susceptibility": "Low"
    }
    res = client.post("/api/risk/manual", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["risk_level"] in ["MODERATE", "LOW"]
    assert data["prediction_trace"]["static_susceptibility"]["susceptibility_class"] == "Low"


def test_scenario_4_inside_high_suscep_elevated():
    """4. Inside high susceptibility corridor + Elevated dynamic conditions."""
    payload = {
        "lat": 27.5042,  # Mangan high-risk corridor
        "lon": 88.5284,
        "slope_deg": 41.2,
        "elevation_m": 842.0,
        "rain_6h": 18.0,
        "rain_24h": 58.0,
        "rain_48h": 95.0,
        "rain_7d": 210.0,
        "soil_0_10cm": 0.36,
        "soil_10_40cm": 0.35,
        "susceptibility": "High"
    }
    res = client.post("/api/risk/manual", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["risk_level"] in ["HIGH", "CRITICAL"]
    assert data["compound_risk"] >= 0.65


def test_scenario_5_high_ml_low_physics():
    """5. High ML probability with Moderate/Low physical score."""
    # Low slope (15 deg) + high antecedent 7d rain (200mm)
    payload = {
        "lat": 27.250,
        "lon": 88.450,
        "slope_deg": 15.0,
        "elevation_m": 500.0,
        "rain_6h": 1.0,
        "rain_24h": 8.0,
        "rain_48h": 20.0,
        "rain_7d": 200.0,
        "soil_0_10cm": 0.28,
        "soil_10_40cm": 0.26,
        "susceptibility": "Low"
    }
    res = client.post("/api/risk/manual", json=payload)
    assert res.status_code == 200
    data = res.json()
    # Compound weighting dampens isolated ML spike
    assert data["compound_risk"] == round(0.55 * data["ml_probability"] + 0.45 * data["risk_score"], 3)
    assert data["risk_level"] in ["MODERATE", "LOW"]


def test_scenario_6_low_ml_high_physics():
    """6. Low ML probability with High physical gradient/susceptibility."""
    # Steep scarp (42 deg) with dry rainfall (0mm)
    payload = {
        "lat": 27.600,
        "lon": 88.580,
        "slope_deg": 42.0,
        "elevation_m": 2200.0,
        "rain_6h": 0.0,
        "rain_24h": 0.0,
        "rain_48h": 0.0,
        "rain_7d": 0.0,
        "soil_0_10cm": 0.15,
        "soil_10_40cm": 0.14,
        "susceptibility": "High"
    }
    res = client.post("/api/risk/manual", json=payload)
    assert res.status_code == 200
    data = res.json()
    # Without rainfall triggering pore pressure, compound risk remains low/moderate
    assert data["ml_probability"] < 0.25
    assert data["compound_risk"] < 0.45
    assert data["risk_level"] == "LOW"


def test_scenario_7_both_high():
    """7. Both ML probability and Physical Hazard are high (Cloudburst on Steep Incline)."""
    payload = {
        "lat": 27.601,
        "lon": 88.582,
        "slope_deg": 44.5,
        "elevation_m": 2250.0,
        "rain_6h": 55.0,
        "rain_24h": 135.0,
        "rain_48h": 195.0,
        "rain_7d": 340.0,
        "soil_0_10cm": 0.52,
        "soil_10_40cm": 0.46,
        "susceptibility": "High"
    }
    res = client.post("/api/risk/manual", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["risk_level"] in ["CRITICAL", "HIGH"]
    assert data["compound_risk"] >= 0.65
    assert data["telemetry_metadata"]["gsi_id_threshold_status"] == "BREACHED"


def test_scenario_8_both_low():
    """8. Both ML probability and Physical Hazard are low (Dry Gentle Valley)."""
    payload = {
        "lat": 27.180,
        "lon": 88.520,
        "slope_deg": 8.0,
        "elevation_m": 400.0,
        "rain_6h": 0.0,
        "rain_24h": 0.0,
        "rain_48h": 1.0,
        "rain_7d": 5.0,
        "soil_0_10cm": 0.12,
        "soil_10_40cm": 0.12,
        "susceptibility": "Low"
    }
    res = client.post("/api/risk/manual", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["risk_level"] == "LOW"
    assert data["compound_risk"] < 0.25
    assert data["ml_probability"] < 0.15


def test_scientific_trace_schema():
    """Validates presence of all 6 explicit layers in the prediction trace."""
    res = client.get("/api/risk?lat=27.3389&lon=88.6065")
    assert res.status_code == 200
    trace = res.json()["prediction_trace"]
    
    assert "static_susceptibility" in trace
    assert "dynamic_conditions" in trace
    assert "ml_prediction" in trace
    assert "physics_hazard_index" in trace
    assert "compound_risk" in trace
    assert trace["compound_risk"]["formula"] == "0.55 * ML_Probability + 0.45 * Physics_Hazard_Index"


if __name__ == "__main__":
    print("Running Multi-Scenario Decision Fusion Test Suite...")
    test_scenario_1_outside_low_dynamic()
    print("[PASS] Scenario 1: Outside + Low Dynamic")
    test_scenario_2_outside_elevated_dynamic()
    print("[PASS] Scenario 2: Outside + Elevated Dynamic")
    test_scenario_3_inside_low_suscep_elevated()
    print("[PASS] Scenario 3: Inside Low Susceptibility + Elevated Dynamic")
    test_scenario_4_inside_high_suscep_elevated()
    print("[PASS] Scenario 4: Inside High Susceptibility + Elevated Dynamic")
    test_scenario_5_high_ml_low_physics()
    print("[PASS] Scenario 5: High ML / Low Physics")
    test_scenario_6_low_ml_high_physics()
    print("[PASS] Scenario 6: Low ML / High Physics")
    test_scenario_7_both_high()
    print("[PASS] Scenario 7: Both High (Cloudburst Emergency)")
    test_scenario_8_both_low()
    print("[PASS] Scenario 8: Both Low (Dry Valley)")
    test_scientific_trace_schema()
    print("[PASS] 6-Layer Scientific Decomposition Trace Schema")
    print("\nALL 8 DECISION FUSION SCENARIOS & TRACE TESTS PASSED SUCCESSFULLY! :)")
