import joblib, numpy as np, json, math
from app.services.terrain_service import terrain_service
from app.services.risk_engine import risk_engine
from app.services.weather_service import weather_service

print("=== AUDIT OF POINTS ACROSS SIKKIM ===")

# Test stations first
from app.config import PILOT_STATIONS
print("\n--- PILOT STATIONS AUDIT ---")
for stn in PILOT_STATIONS:
    lat, lon, name = stn['lat'], stn['lon'], stn['name']
    r = risk_engine.calculate_risk(lat, lon)
    matched = terrain_service.find_susceptibility_zone(lat, lon)
    print(f"Station: {name} ({lat}, {lon})")
    print(f"  Inside GeoJSON Polygon: {matched is not None}")
    print(f"  Susceptibility Class: {r['factors']['susceptibility']} (factor={r['factors']['suscep_factor']})")
    print(f"  Slope: {r['factors']['slope_deg']} deg, Elevation: {r['factors']['elevation_m']} m")
    print(f"  Rain 24h: {r['factors']['rain_24h']} mm, 7d: {r['factors']['rain_7d']} mm")
    print(f"  Soil (0-10cm): {r['factors']['soil_0_10cm']} m3/m3, (10-40cm): {r['factors']['soil_10_40cm']} m3/m3")
    print(f"  ML Prob: {r['ml_probability']*100:.1f}%, Hazard Score: {r['risk_score']}, Compound Risk: {r['compound_risk']}, Level: {r['risk_level']}")
    print(f"  Feature Vector: {r['prediction_trace']['stage_3_ml_feature_vector']['feature_values']}")
    print("-" * 60)

# Check points outside polygons with high/moderate dynamic rain
print("\n--- SEARCHING FOR POINTS OUTSIDE POLYGONS WITH ELEVATED RISK ---")
test_coords = [
    (27.45, 88.50, "North of Gangtok"),
    (27.55, 88.60, "North-East Mangan Ridge"),
    (27.35, 88.35, "West Ridge Ravangla"),
    (27.25, 88.45, "South Central Namchi slope"),
    (27.70, 88.65, "Upper North High Altitude"),
    (27.38, 88.75, "East Sikkim High Incline")
]

for lat, lon, desc in test_coords:
    r = risk_engine.calculate_risk(lat, lon)
    matched = terrain_service.find_susceptibility_zone(lat, lon)
    print(f"Coordinate: {desc} ({lat}, {lon})")
    print(f"  Inside GeoJSON Polygon: {matched is not None}")
    print(f"  Susceptibility Class: {r['factors']['susceptibility']} (factor={r['factors']['suscep_factor']})")
    print(f"  Slope: {r['factors']['slope_deg']} deg, Elevation: {r['factors']['elevation_m']} m")
    print(f"  Rain 24h: {r['factors']['rain_24h']} mm, 7d: {r['factors']['rain_7d']} mm")
    print(f"  Soil (0-10cm): {r['factors']['soil_0_10cm']} m3/m3, (10-40cm): {r['factors']['soil_10_40cm']} m3/m3")
    print(f"  ML Prob: {r['ml_probability']*100:.1f}%, Hazard Score: {r['risk_score']}, Compound Risk: {r['compound_risk']}, Level: {r['risk_level']}")
    print(f"  Feature Vector: {r['prediction_trace']['stage_3_ml_feature_vector']['feature_values']}")
    print("-" * 60)
