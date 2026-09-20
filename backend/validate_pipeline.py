import os, sys, json, joblib, numpy as np, pandas as pd

backend_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(backend_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.services.terrain_service import terrain_service
from app.services.risk_engine import risk_engine
from app.services.weather_service import weather_service

print("=" * 80)
print("  STEP 1 & 2 & 3: REPRODUCE SELECTED-POINT PREDICTION & RESOLVE DISCREPANCIES")
print("=" * 80)

model_path = os.path.join(backend_dir, "app", "data", "models", "xgb_model.joblib")
xgb = joblib.load(model_path)

# Let's inspect how hazard_index is computed in risk_engine.py:
# raw_rule_score = (
#     0.30 * min(2.0, rain_24h / 50.0) +
#     0.15 * min(2.0, rain_48h / 80.0) +
#     0.15 * min(2.0, rain_7d / 180.0) +
#     0.20 * min(2.0, slope / 35.0) +
#     0.10 * min(2.0, soil_0_10 / 0.38) +
#     0.10 * suscep_factor
# )
# Notice: For a point with slope=28.0, rain_24h=38, rain_48h=62, rain_7d=115, soil=0.34, suscep_factor=0.5:
# 0.30*(38/50) + 0.15*(62/80) + 0.15*(115/180) + 0.20*(28/35) + 0.10*(0.34/0.38) + 0.10*0.5
# = 0.228 + 0.11625 + 0.0958 + 0.160 + 0.0894 + 0.050 = 0.739 -> 0.74
# Let's test various combinations to see what gave 0.52:

def calc_hazard(r24, r48, r7d, slope, soil, suscep):
    score = (
        0.30 * min(2.0, r24 / 50.0) +
        0.15 * min(2.0, r48 / 80.0) +
        0.15 * min(2.0, r7d / 180.0) +
        0.20 * min(2.0, slope / 35.0) +
        0.10 * min(2.0, soil / 0.38) +
        0.10 * suscep
    )
    return round(score, 2)

print(f"Sample 1 (r24=9, r48=33.2, r7d=150.2, slope=21.8, soil=0.272, suscep=0.1): Hazard = {calc_hazard(9, 33.2, 150.2, 21.8, 0.272, 0.1)}")
print(f"Sample 2 (r24=10, r48=24.3, r7d=56.6, slope=30.2, soil=0.289, suscep=1.0): Hazard = {calc_hazard(10, 24.3, 56.6, 30.2, 0.289, 1.0)}")
print(f"Sample 3 (r24=14.8, r48=36.6, r7d=84.7, slope=32.0, soil=0.337, suscep=0.5): Hazard = {calc_hazard(14.8, 36.6, 84.7, 32.0, 0.337, 0.5)}")

# Let's test what feature vector gives ML Prob ~ 79.2%:
test_vectors = [
    ("Namchi Slope high antecedent", [0.7, 9.0, 33.2, 150.2, 0.272, 0.262, 0.246, 21.8, 461.0, 0.1]),
    ("Moderate rain 25mm + 120mm 7d", [5.0, 25.0, 45.0, 120.0, 0.32, 0.31, 0.29, 24.0, 950.0, 0.1]),
    ("Heavy 7d rain (180mm) gentle slope", [2.0, 15.0, 35.0, 180.0, 0.34, 0.33, 0.30, 18.0, 800.0, 0.1]),
    ("Valley Inundation (220mm 7d)", [3.0, 20.0, 50.0, 220.0, 0.36, 0.35, 0.32, 15.0, 600.0, 0.1]),
]

for name, v in test_vectors:
    prob = xgb.predict_proba(np.array(v).reshape(1, -1))[0, 1]
    hz = calc_hazard(v[1], v[2], v[3], v[7], v[4], v[9])
    comp = 0.55 * prob + 0.45 * hz
    print(f"Vector '{name}':")
    print(f"  ML Prob: {prob*100:.1f}%, Hazard Index: {hz:.2f}, Compound Risk: {comp:.3f}")

print("\n" + "=" * 80)
print("  STEP 4: MODEL CALIBRATION & THRESHOLDS ON VALIDATION HOLDOUT")
print("=" * 80)

# Load holdout dataset
from ml_pipeline.data_loader import load_gsi_events
from ml_pipeline.negative_sampling import generate_negative_samples
from ml_pipeline.train_and_validate import extract_features

pos_df, _ = load_gsi_events()
pos_df["label"] = 1
neg_df = generate_negative_samples(pos_df, neg_to_pos_ratio=2.0, min_exclusion_km=2.0, seed=42)
full_df = pd.concat([pos_df, neg_df], ignore_index=True).sort_values("datetime").reset_index(drop=True)

test_df = full_df[full_df["year"] >= 2024].reset_index(drop=True)
X_test, y_test = extract_features(test_df)

probs_test = xgb.predict_proba(X_test)[:, 1]

# Calibration analysis across probability bins
print("Probability Bins vs Empirical Positive Rate on 2024 Holdout (83 samples):")
bins = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
for i in range(len(bins)-1):
    low, high = bins[i], bins[i+1]
    mask = (probs_test >= low) & (probs_test < high) if high < 1.0 else (probs_test >= low) & (probs_test <= high)
    n = np.sum(mask)
    if n > 0:
        pos_rate = np.mean(y_test[mask])
        print(f"  Bin [{low:.1f} - {high:.1f}]: N={n:2d}, Mean Pred Prob={np.mean(probs_test[mask]):.3f}, Actual Pos Rate={pos_rate:.3f}")
    else:
        print(f"  Bin [{low:.1f} - {high:.1f}]: N= 0")

print("\n" + "=" * 80)
print("  STEP 13: SENSITIVITY ANALYSIS (INDEPENDENT FEATURE PERTURBATIONS)")
print("=" * 80)

# Base vector: moderate point outside polygon
# [rain_6h, rain_24h, rain_48h, rain_7d, soil_0_10, soil_10_40, soil_27_81, slope, elevation, suscep_factor]
base_vec = [1.0, 10.0, 20.0, 60.0, 0.28, 0.27, 0.25, 20.0, 1000.0, 0.1]

print(f"Base Vector: Rain24=10mm, Rain7d=60mm, Soil=0.28, Slope=20deg, Suscep=0.1 (Low)")
base_prob = xgb.predict_proba(np.array(base_vec).reshape(1, -1))[0, 1]
base_hz = calc_hazard(10, 20, 60, 20, 0.28, 0.1)
print(f"Base Output: ML Prob = {base_prob*100:.1f}%, Hazard Index = {base_hz:.2f}, Compound = {0.55*base_prob + 0.45*base_hz:.3f}\n")

# Sensitivity A: Vary Rain 7d from 20mm to 300mm
print("1. Sensitivity to 7-Day Antecedent Rain (rain_7d):")
for r7 in [20, 60, 100, 150, 200, 300]:
    v = list(base_vec)
    v[3] = r7
    p = xgb.predict_proba(np.array(v).reshape(1, -1))[0, 1]
    hz = calc_hazard(v[1], v[2], v[3], v[7], v[4], v[9])
    print(f"  rain_7d = {r7:3d} mm -> ML Prob = {p*100:5.1f}%, Hazard = {hz:.2f}, Compound = {0.55*p + 0.45*hz:.3f}")

# Sensitivity B: Vary Slope from 5 deg to 50 deg
print("\n2. Sensitivity to Slope Gradient (slope_deg):")
for s in [5, 15, 25, 35, 45]:
    v = list(base_vec)
    v[7] = s
    p = xgb.predict_proba(np.array(v).reshape(1, -1))[0, 1]
    hz = calc_hazard(v[1], v[2], v[3], v[7], v[4], v[9])
    print(f"  slope = {s:2d} deg   -> ML Prob = {p*100:5.1f}%, Hazard = {hz:.2f}, Compound = {0.55*p + 0.45*hz:.3f}")

# Sensitivity C: Vary Soil Moisture from 0.15 to 0.38 m3/m3
print("\n3. Sensitivity to Soil Moisture (soil_0_10cm & soil_10_40cm):")
for sm in [0.15, 0.22, 0.28, 0.34, 0.38]:
    v = list(base_vec)
    v[4] = sm
    v[5] = sm * 0.95
    v[6] = sm * 0.88
    p = xgb.predict_proba(np.array(v).reshape(1, -1))[0, 1]
    hz = calc_hazard(v[1], v[2], v[3], v[7], v[4], v[9])
    print(f"  soil = {sm:.2f} m3/m3 -> ML Prob = {p*100:5.1f}%, Hazard = {hz:.2f}, Compound = {0.55*p + 0.45*hz:.3f}")

# Sensitivity D: Vary Susceptibility Factor (0.1, 0.5, 1.0)
print("\n4. Sensitivity to Susceptibility Factor (suscep_factor):")
for sf, label in [(0.1, "Low / Outside Mapped"), (0.5, "Moderate Corridor"), (1.0, "High Risk Corridor")]:
    v = list(base_vec)
    v[9] = sf
    p = xgb.predict_proba(np.array(v).reshape(1, -1))[0, 1]
    hz = calc_hazard(v[1], v[2], v[3], v[7], v[4], v[9])
    print(f"  suscep = {sf:.1f} ({label:20s}) -> ML Prob = {p*100:5.1f}%, Hazard = {hz:.2f}, Compound = {0.55*p + 0.45*hz:.3f}")
