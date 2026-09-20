# LEWS Implementation Progress Checklist
## SIH Problem Statement 26001 — Sikkim Pilot

> Last Updated: 2026-08-31

---

## Phase 1: Data Infrastructure & Topography
- [x] **Genuine SRTM DEM Integration** — USGS/NASA SRTM 1-arcsecond (30m) tiles (`N27E088`, `N28E088`) mosaicked to GeoTIFF
- [x] **Terrain Service** — Real `rasterio`-based elevation/slope/aspect calculation with Horn's 3x3 convolution
- [x] **ERA5-Land Weather Fetcher** — Open-Meteo Historical Archive for training data backfill
- [x] **Live Weather Service** — Open-Meteo Forecast API with actual current temp, humidity, wind, 24h rainfall windows, and 24h hourly forecast array
- [x] **Multi-Depth Soil Moisture Observations** — Open-Meteo / ECMWF multi-layer soil moisture (`0-1cm`, `1-3cm`, `3-9cm`, `9-27cm`, and `27-81cm`)
- [x] **Remove Synthetic Weather Fallback** — Strict `LIVE → CACHED → STALE/UNAVAILABLE` provenance chain
- [x] **GSI NLSM Susceptibility GeoJSON** — 11 verified vector polygons across 6 districts with geometry properties
- [x] **ERA5 Weather Cache** — Cached historical telemetry for 465 samples

## Phase 2: Historical Landslide Dataset
- [x] **155-event GSI Landslide Inventory** — 2018–2024, with pre-failure ERA5-Land telemetry backfill
- [x] **310 Negative Controls** — Real non-landslide environmental observations at non-event sites (≥2km buffer)
- [!] **PDF Source Extraction** — `Landslide_Sikkim.pdf` is an 18-page scanned image PDF (0 extractable text characters) → **BLOCKED, requires OCR**
- [!] **Uploaded GeoJSON (Sikkim_Landslide.json)** — File uploaded as 0-byte stream → **BLOCKED, requires re-upload**

## Phase 3: ML Training & Validation
- [x] **Chronological Train/Test Split** — Train: 2018–2023 (382 samples), Test: 2024 Monsoon (83 samples)
- [x] **XGBoost Classifier** — Trained with zero leakage, persisted to joblib artifact
- [x] **Random Forest Classifier** — Trained as fallback baseline, persisted to joblib artifact
- [x] **GSI I-D Rule Baseline** — Empirical power-law threshold ($I = 43.26 D^{-0.78}$, $48\text{h} \ge 36.7\text{mm}$)
- [x] **Model Metrics** — Precision/Recall/F1/ROC-AUC computed on held-out 2024 test data
- [x] **Model Calibration Audit** — Verified across 5 probability bins on 2024 holdout dataset

## Phase 4: Calibrated Decision Fusion & Risk Engine
- [x] **Calibrated Continuous Weighted Fusion**:
  - $\text{Compound Risk} = 0.55 \times \text{ML Probability} + 0.45 \times \text{Physics Hazard Index}$
  - Risk Bands: $<0.45\text{ (LOW)}$, $0.45\text{--}<0.65\text{ (MODERATE)}$, $\ge 0.65\text{ (HIGH)}$, $\ge 0.85\text{ (CRITICAL)}$
- [x] **Removed Arbitrary Hard ML Overrides** — ML probability contributes continuously through compound score
- [x] **Preserved Physical Cloudburst Emergency Trigger** — GSI Intensity-Duration threshold breach ($I \ge 43.26 D^{-0.78}$ on $\ge 30^\circ$ slope) raises compound risk to $\ge 0.68$
- [x] **Scientific Decomposition in API Trace** — Distinct layers for Static Susceptibility, Dynamic Conditions, ML Vector, Physics Hazard, Compound Risk, and Scientific Synthesis
- [x] **Point Risk API** — `GET /api/risk?lat=&lon=`
- [x] **Offline Manual Risk API** — `POST /api/risk/manual` & `GET /api/risk/manual`
- [x] **Data Center Overview API** — `GET /api/data_center/overview`

## Phase 5: Frontend UI & Evidence Center
- [x] **Frontend Script Load & Error Resolution** — Eliminated parse-time SyntaxErrors, enabling immediate Leaflet map rendering & event listeners
- [x] **Interactive GIS Command Map** — Leaflet map with click → risk calculation, HTTPS Google Satellite tiles, CartoDB Dark, OpenTopoMap
- [x] **Synchronized Map Legend** — Bottom-left legend updated to calibrated 4-tier decision fusion thresholds (<0.45 Low, 0.45-0.64 Moderate, >=0.65 High, >=0.85 Critical)
- [x] **Susceptibility Polygons** — Hover/click with properties inspection
- [x] **6-Layer Scientific Risk Inspector Panel**:
  - 1. Static Susceptibility (Inside/Outside Mapped Coverage, Class, Factor, Source)
  - 2. Dynamic Conditions & Terrain (24h/48h/7d Rain, Soil Moisture, SRTM 30m Slope, Freshness)
  - 3. ML Prediction (XGBoost v3.0 Probability %)
  - 4. Physics Hazard Index (GSI I-D Power-law weighted score)
  - 5. Final Compound Risk (0.55 × ML + 0.45 × Physics Gauge & Band Badge)
  - 6. Scientific Synthesis (Transparent explanation of static vs dynamic factors)
- [x] **Concurrent Station & Risk Pipeline** — Multi-threaded station telemetry evaluation (<1s)
- [x] **Real-Time Data Center Explorer** — Dedicated subtabs for Weather, Soil, Landslides, GeoJSON, SRTM DEM, and 5-Stage Decision Pipeline
- [x] **Genuinely Functional Manual Risk Calculator** — Custom inputs with presets & live calculation
- [x] **What-If Scenario Simulator** — Rainfall surge stress-tester (+10% to +100%)
- [x] **Historical Replay Mode** — Time-travel through verified monsoon failure events
- [x] **Right-Side Dashboard Checklist** — Live audit panel with `[x]`, `[~]`, `[ ]`, `[!]` tags

## Phase 6: Automated Test Verification
- [x] **DEM Validation Suite** — `tests/test_dem.py` — **ALL PASSED**
- [x] **Model Integrity Suite** — `tests/test_model.py` — **ALL PASSED**
- [x] **API Integration Suite** — `tests/test_api.py` — **ALL 13/13 PASSED**
- [x] **Multi-Scenario Decision Fusion Suite** — `tests/test_decision_fusion.py` — **ALL 8/8 SCENARIOS PASSED**

---

## Current External Blockers (Awaiting User Action)
1. **`Landslide_Sikkim.pdf`**: Scanned raster image PDF (18 pages, 0 extractable text characters). Requires OCR or digital table export.
2. **`Sikkim_Landslide.json`**: Uploaded as 0-byte stream. System is using the 11 verified GSI NLSM polygons in `sikkim_susceptibility.geojson`.
