import os, sys, json, joblib, numpy as np, pandas as pd
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

gsi_path = os.path.join(os.path.dirname(__file__), 'app', 'data', 'gsi_landslides.json')
with open(gsi_path, 'r', encoding='utf-8') as f:
    gsi_data = json.load(f)

records = gsi_data.get('records', [])
metadata = gsi_data.get('metadata', {})
df_pos = pd.DataFrame(records)

print(f"Total positive records in gsi_landslides.json: {len(df_pos)}")
print(f"Columns: {list(df_pos.columns)}")
print(f"Metadata: {metadata}")
print(f"Positive samples by year:\n{df_pos['year'].value_counts().sort_index()}")

# Check negative sampling
from ml_pipeline.negative_sampling import generate_negative_samples
df_neg = generate_negative_samples(df_pos, neg_to_pos_ratio=2.0, min_exclusion_km=2.0, seed=42)
print(f"\nGenerated negative controls count: {len(df_neg)}")
print(f"Negative controls by year:\n{df_neg['year'].value_counts().sort_index()}")

# Feature stats
print("\n--- Positive Samples Feature Summary ---")
print(df_pos[['trigger_rain_24h_mm', 'trigger_rain_7d_mm', 'soil_moisture_0_10cm', 'slope_deg', 'elevation_m']].describe().T[['mean', 'std', 'min', '50%', 'max']])

print("\n--- Negative Controls Feature Summary ---")
print(df_neg[['trigger_rain_24h_mm', 'trigger_rain_7d_mm', 'soil_moisture_0_10cm', 'slope_deg', 'elevation_m']].describe().T[['mean', 'std', 'min', '50%', 'max']])

# Test XGBoost on vector
model_path = os.path.join(os.path.dirname(__file__), 'app', 'data', 'models', 'xgb_model.joblib')
xgb = joblib.load(model_path)
v = np.array([[0.7, 9.0, 33.2, 150.2, 0.272, 0.262, 0.246, 21.8, 461.0, 0.1]])
prob = xgb.predict_proba(v)[0, 1]
print(f"\nTest Point Vector [0.7, 9.0, 33.2, 150.2, 0.272, 0.262, 0.246, 21.8, 461.0, 0.1]:")
print(f"XGBoost predict_proba: {prob:.4f} ({prob*100:.1f}%)")

# What if rain_7d drops from 150 to 30?
v_low_rain = np.array([[0.7, 9.0, 12.0, 30.0, 0.272, 0.262, 0.246, 21.8, 461.0, 0.1]])
prob_low = xgb.predict_proba(v_low_rain)[0, 1]
print(f"Test Point Vector with 7d Rain=30mm: {prob_low:.4f} ({prob_low*100:.1f}%)")
