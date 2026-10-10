# TerraSentinel Fix Kit

Drop-in code that makes the deck's claims true and removes the problems found in the audit.
Put this folder at the **repo root** (`landslide-early-warning-system/fixkit/`) so it can reuse `backend/`.

```bash
pip install numpy pandas scikit-learn xgboost requests joblib pytest
pytest -q test_fixkit.py          # 11 offline tests, all should pass
```

## What each file fixes

| File | Problem it fixes |
|---|---|
| `sanity_probe.py` | Proves the current model is unsafe to demo (it fails 4 of 5 physics checks). Run it before every demo. |
| `fetch_real_landslides.py` | Replaces the 155 randomly generated "GSI" events with real, cited events (NASA COOLR + your verified rows). A row without a source URL is rejected. |
| `manual_events_template.csv` | Template for events you verify yourself (SDMA situation reports, GSI reports, PTI/Reuters). |
| `weather_fix.py` | Fixes the soil-moisture bug (wrong archive variable names led to a month-based fallback). Uses the same 0–28 cm quantity for training and live data. Never invents data. |
| `build_features.py` | Leakage-free training set with case-crossover negatives (same place on another date, plus same date at another place). Rain is taken only before the event day. |
| `physics_engine.py` | Real physics. Correct Sikkim and Gangtok I-D thresholds (mm/day, days), plus infinite-slope Factor of Safety with Monte Carlo, giving P(FoS < 1). |
| `train_fusion.py` | XGBoost with monotone constraints and an L2 logistic meta-learner. Compares 5 systems on one held-out test set with bootstrap 95% CIs. |
| `fusion_inference.py` | Backend scoring with an explanation generated from the same numbers (fixes "UI formula ≠ computed formula"). Physics-only fallback outside the ML's training range. |
| `replay_real_event.py` | Replaces hand-typed replay timelines. Computes the timeline from archived rainfall hour by hour, so lead time is measured, not typed. |
| `cap_alert.py` | CAP v1.2 alert export. Draft → officer approve() → Actual. Use `status="Exercise"` for demos. |
| `terrain_npz.py` | Fixes the live demo: on Vercel the DEM never loads (no rasterio), so every click returns a typed station slope. Precomputes slope into a numpy file and returns None outside coverage. |

## Run order (real data)

```bash
# 0. See the problem (optional, 5 sec)
python sanity_probe.py --model ../backend/app/data/models/xgb_model.joblib --schema old

# 1. Real events  (start with --region ner for more events; Sikkim-only is small)
python fetch_real_landslides.py --region ner
#    + add verified rows to manual_events.csv, re-run

# 2. Features (needs internet, cached in .feature_cache.json)
python build_features.py --events real_events.csv --out features.csv --temporal 2 --spatial 1
#    NOTE: backend terrain only covers Sikkim. For NER-wide events, download extra SRTM /
#    Copernicus GLO-30 tiles first, or restrict --bbox to Sikkim + Darjeeling.

# 3. Train + honest comparison (pick a test start year that leaves >= 5 test positives)
python train_fusion.py --features features.csv --test-from 2017 --out artifacts
#    -> artifacts/fusion_table.md  (paste into the deck), fusion_report.json

# 4. Gate: must be 5/5 (or 4/5 with only T5 failing for an ML-only model) before demo
python sanity_probe.py --model artifacts/xgb_monotone.joblib --schema new

# 5. Replay a HELD-OUT real event (not in training years)
python replay_real_event.py --lat .. --lon .. --date YYYY-MM-DD --slope .. \
       --name "..." --source "https://..." --artifacts artifacts --out replay_event.json

# 6. Live-demo terrain (laptop, needs rasterio)
python terrain_npz.py build ../backend/app/data/dem/processed/sikkim_dem_srtm_30m.tif terrain_sikkim.npz

# 7. CAP demo alert
python cap_alert.py
```

## Integration checklist (backend)

- [ ] `risk_engine._compute_hazard_decision` → call `FusionModel.assess()`; show `explanation` in the 6-layer panel.
- [ ] `weather_service` → use `weather_fix.live_features()` (same features as training).
- [ ] `terrain_service` → `NpzTerrain.lookup()`; if it returns None, the UI says "outside coverage".
- [ ] `test_events.json` → replace with `replay_real_event.py` output (keep `source_url`, `evidence_grade`).
- [ ] `metrics.json` → generate from `fusion_report.json`. Delete the hard-coded `median_warning_lead_time_hours`.
- [ ] Replace `sikkim_susceptibility.geojson` with real GSI NLSM polygons from Bhukosh (free download).
- [ ] Delete or rename `ml_pipeline/build_gsi_dataset.py` → `make_synthetic_demo_data.py`, and keep it out of training.
- [ ] Add a `/api/alerts/cap` endpoint returning `build_alert(..., status="Draft")` and an officer `approve` action.

## Honest limits (say these before judges find them)

- ERA5 rainfall is ~9–25 km resolution. It underestimates convective cloudbursts in narrow valleys. Roadmap: IMD AWS, GPM IMERG, radar.
- Soil strength ranges are literature values. Calibrate with GSI post-disaster study reports.
- News-based catalogues under-report remote areas, so negatives may contain unreported slides.
- The model is for rainfall triggers only. Earthquake and GLOF triggers (e.g., Oct 2023 South Lhonak) are out of scope.
