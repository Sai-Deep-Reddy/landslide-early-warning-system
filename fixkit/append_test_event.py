import json

with open("replay_pakyong_2018.json", "r", encoding="utf-8") as f:
    pak = json.load(f)

# Sample key hours
target_hours = [-72.0, -48.0, -36.0, -24.0, -12.0, -6.0, 0.0]
timeline_samples = []
step_idx = 0
for step in pak["timeline"]:
    if any(abs(step["rel_hour"] - th) < 0.1 for th in target_hours):
        rel_h = int(step["rel_hour"])
        time_str = f"T{rel_h:+d}h" if rel_h != 0 else "T-0h Event"
        status_msg = (
            "CRITICAL: High failure probability. Road blockage warning issued."
            if step["risk_score"] >= 0.65 else
            "MODERATE: Approaching threshold. Heavy rain continuous."
            if step["risk_score"] >= 0.40 else
            "LOW: Soil retention stable under normal drainage."
        )
        time_part = step["timestamp"][11:16]
        timeline_samples.append({
            "step_index": step_idx,
            "rel_hour": rel_h,
            "timestamp": step["timestamp"] + "Z",
            "time_display": f"{time_str} ({time_part})",
            "rain_intensity_mmh": round(step["rain_intensity_mmh"], 1),
            "rain_6h_mm": round(step.get("rain_6h_mm", step["rain_intensity_mmh"] * 4.0), 1),
            "rain_24h_mm": round(step["rain_24h_mm"], 1),
            "rain_7d_mm": round(step["rain_7d_mm"], 1),
            "soil_moisture_0_10cm": round(step["soil_0_28cm"], 3),
            "soil_0_28cm": round(step["soil_0_28cm"], 3),
            "id_ratio": round(step["id_ratio"], 3),
            "p_failure_physics": round(step["p_failure_physics"], 3),
            "risk_score": round(step["risk_score"], 3),
            "risk_level": step["risk_level"],
            "mode": step["mode"],
            "status_message": status_msg
        })
        step_idx += 1

event_obj = {
    "event_id": "REAL-PAKYONG-2018",
    "title": "Pakyong Subdivision Road Blockages (May 2018)",
    "location": "Pakyong Subdivision, East Sikkim",
    "district": "Pakyong",
    "lat": pak["lat"],
    "lon": pak["lon"],
    "elevation_m": 1450,
    "slope_deg": 34.0,
    "susceptibility": "High",
    "slide_timestamp": pak["reference_time"] + "Z",
    "actual_slide_time_str": "May 26, 2018 at 00:00 IST",
    "warning_issued_time_str": pak["first_alert"] + " IST",
    "calculated_lead_time_hours": pak["lead_time_hours"],
    "source_url": pak["source_url"],
    "evidence_grade": pak["evidence_grade"],
    "data_source": pak["data"],
    "event_summary": "Continuous heavy downpours triggered multiple landslides causing 45 road blockages across Pakyong subdivision. Real verified event with news source and hourly ERA5 reanalysis.",
    "timeline": timeline_samples
}

with open("backend/app/data/test_events.json", "r", encoding="utf-8") as f:
    events = json.load(f)

# Keep first event if already present
if len(events) == 1:
    events.append(event_obj)
elif len(events) > 1:
    events = [events[0], event_obj]

with open("backend/app/data/test_events.json", "w", encoding="utf-8") as f:
    json.dump(events, f, indent=2)

print("Updated test_events.json with 2 events: count =", len(events))
