"""
Automated Integration Tests for Landslide Early-Warning System (LEWS)
SIH PS 26001 - Production Build
"""

import sys
import os
import json
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.main import app
from app.config import METRICS_PATH

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "Sikkim" in data["pilot_region"]


def test_susceptibility_endpoint():
    response = client.get("/api/susceptibility")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) >= 5
    first = data["features"][0]
    assert "geometry" in first
    assert "properties" in first
    assert "susceptibility_class" in first["properties"]


def test_risk_endpoint():
    response = client.get("/api/risk?lat=27.301&lon=88.611")
    assert response.status_code == 200
    data = response.json()
    assert "risk_score" in data
    assert 0.0 <= data["risk_score"] <= 1.0
    assert "ml_probability" in data
    assert 0.0 <= data["ml_probability"] <= 1.0
    assert data["risk_level"] in ["LOW", "MODERATE", "HIGH", "CRITICAL"]
    assert "factors" in data
    assert "telemetry_metadata" in data
    assert "dem_source" in data["telemetry_metadata"]
    assert "model_version" in data["telemetry_metadata"]


def test_stations_endpoint():
    response = client.get("/api/stations")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 5
    first = data[0]
    assert "name" in first
    assert "risk_assessment" in first
    assert "ml_probability" in first["risk_assessment"]


def test_landslides_endpoint():
    response = client.get("/api/landslides")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 100, f"Expected full historical dataset (>=100 events), got {len(data)}"
    assert "event_date" in data[0]
    assert "type" in data[0]


def test_validation_endpoint_dynamic():
    response = client.get("/api/validation")
    assert response.status_code == 200
    data = response.json()

    # Verify metrics are within true probabilistic bounds
    assert "metrics" in data
    m = data["metrics"]
    assert 0.0 <= m["precision_pct"] <= 100.0
    assert 0.0 <= m["recall_pct"] <= 100.0
    assert 0.0 <= m["f1_score_pct"] <= 100.0
    assert 0.0 <= m["roc_auc"] <= 1.0

    # Ensure dynamic parity with metrics.json on disk
    with open(METRICS_PATH, "r", encoding="utf-8") as f:
        disk_metrics = json.load(f)
    assert data["metrics"] == disk_metrics["metrics"], "API response must match metrics.json on disk"


def test_alerts_endpoint():
    response = client.get("/api/alerts")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_simulate_endpoint():
    payload = {"rain_boost_pct": 50.0}
    response = client.post("/api/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "station_results" in data
    assert len(data["station_results"]) > 0


def test_replay_endpoint():
    response = client.get("/api/replay")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert "timeline" in data[0]


def test_field_report_submission():
    payload = {
        "lat": 27.2917,
        "lon": 88.2394,
        "location_name": "Test Pelling Pass Km 10",
        "district": "Gyalshing",
        "officer_name": "SDRF Inspector",
        "observation_type": "Tension Crack",
        "notes": "Test automated verification report",
        "severity": "Moderate"
    }
    response = client.post("/api/report", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"


def test_manual_risk_calculator_custom_inputs():
    # Scenario 1: Extreme Cloudburst on Steep Mountain Scarp
    scen_high = {
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
    resp_high = client.post("/api/risk/manual", json=scen_high)
    assert resp_high.status_code == 200
    d_high = resp_high.json()
    assert d_high["risk_level"] in ["CRITICAL", "HIGH"]
    assert d_high["ml_probability"] >= 0.50
    assert d_high["telemetry_metadata"]["gsi_id_threshold_status"] == "BREACHED"
    assert d_high["is_manual_mode"] is True

    # Scenario 2: Dry Valley Low Incline
    scen_low = {
        "lat": 27.180,
        "lon": 88.520,
        "slope_deg": 12.0,
        "elevation_m": 680.0,
        "rain_6h": 0.0,
        "rain_24h": 2.0,
        "rain_48h": 5.0,
        "rain_7d": 18.0,
        "soil_0_10cm": 0.20,
        "soil_10_40cm": 0.18,
        "susceptibility": "Low"
    }
    resp_low = client.post("/api/risk/manual", json=scen_low)
    assert resp_low.status_code == 200
    d_low = resp_low.json()
    assert d_low["risk_level"] == "LOW"
    assert d_low["ml_probability"] < 0.40
    assert d_low["telemetry_metadata"]["gsi_id_threshold_status"] == "NOMINAL"

    # Confirm that outputs strictly differ between high and low scenarios
    assert d_high["risk_score"] > d_low["risk_score"]
    assert d_high["ml_probability"] > d_low["ml_probability"]


def test_data_center_overview_actual_data():
    response = client.get("/api/data_center/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OPERATIONAL"
    assert "weather_data" in data
    assert "dem_topography" in data
    assert "susceptibility_geojson" in data
    assert "historical_landslides" in data
    assert data["historical_landslides"]["total_verified_events"] >= 100
    assert data["dem_topography"]["spatial_resolution"] == "30 meters (1 arc-second grid)"


def test_five_stage_prediction_trace():
    response = client.get("/api/risk?lat=27.301&lon=88.611")
    assert response.status_code == 200
    data = response.json()
    assert "prediction_trace" in data
    trace = data["prediction_trace"]
    assert "stage_1_raw_telemetry" in trace
    assert "stage_2_normalized_features" in trace
    assert "stage_3_ml_feature_vector" in trace
    assert "stage_4_model_outputs" in trace
    assert "stage_5_final_decision" in trace
    assert len(trace["stage_3_ml_feature_vector"]["feature_values"]) == 10


if __name__ == "__main__":
    print("Running API Integration Test Suite...")
    test_health()
    print("[PASS] Health Check Passed")
    test_susceptibility_endpoint()
    print("[PASS] GeoJSON Susceptibility Layer API Passed")
    test_risk_endpoint()
    print("[PASS] Risk API with ML Probability & Telemetry Passed")
    test_stations_endpoint()
    print("[PASS] Monitoring Stations API Passed")
    test_landslides_endpoint()
    print("[PASS] Historical GSI Landslides Dataset API Passed")
    test_validation_endpoint_dynamic()
    print("[PASS] Dynamic Model Validation API Passed")
    test_alerts_endpoint()
    print("[PASS] Active Alerts API Passed")
    test_simulate_endpoint()
    print("[PASS] What-If Simulation API Passed")
    test_replay_endpoint()
    print("[PASS] Historical Replay API Passed")
    test_field_report_submission()
    print("[PASS] Field Incident Report Submission Passed")
    test_manual_risk_calculator_custom_inputs()
    print("[PASS] Manual Risk Calculator Custom Inputs & Scenario Test Passed")
    test_data_center_overview_actual_data()
    print("[PASS] Data Center Overview & Actual Data Ingestion Passed")
    test_five_stage_prediction_trace()
    print("[PASS] 5-Stage Prediction & Decision Trace Pipeline Passed")
    print("\nALL API INTEGRATION TESTS PASSED SUCCESSFULLY! :)")

