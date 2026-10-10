"""
sanity_probe.py  —  5 physical-consistency tests for ANY landslide model. Run before every demo.
A model that fails these will embarrass you on the What-If slider in front of judges.

  T1 zero-rain     : no rain for 7 days must NOT produce an alert-level probability
  T2 rain-monotone : more rain (everything else fixed) must never LOWER risk
  T3 month-proxy   : changing only soil moisture between the two old fallback constants
                     (0.23 vs 0.385) must not swing risk more than a big rain change does
  T4 slope-monotone: steeper slope (same weather) must never lower risk
  T5 flat-ground   : a 3-degree slope in a cloudburst should stay low
                     (an ML-only model trained on slopes >=15 deg may fail this; the deployed
                      fusion_inference.py routes such slopes to physics, which handles it)

Usage:
  python sanity_probe.py --model ../backend/app/data/models/xgb_model.joblib --schema old
  python sanity_probe.py --model artifacts/xgb_monotone.joblib --schema new
"""
from __future__ import annotations

import argparse
import warnings

import joblib
import numpy as np

warnings.filterwarnings("ignore")

SCHEMAS = {
    # the team's current model (10 features)
    "old": ["rain_6h", "rain_24h", "rain_48h", "rain_7d", "soil_0_10cm", "soil_10_40cm",
            "soil_27_81cm", "slope_deg", "elevation_m", "suscep_factor"],
    # fix-kit model (9 features)
    "new": ["rain_6h", "rain_24h", "rain_48h", "rain_72h", "rain_7d", "max_1h_24h",
            "soil_0_28cm", "slope_deg", "elevation_m"],
}


def row(schema, r24, soil, slope=35.0, elev=1500.0):
    v = {"rain_6h": r24 * 0.4, "rain_24h": r24, "rain_48h": r24 * 1.5, "rain_72h": r24 * 1.9,
         "rain_7d": r24 * 2.5, "max_1h_24h": r24 / 6, "soil_0_10cm": soil, "soil_10_40cm": soil * 0.88,
         "soil_27_81cm": soil * 0.78, "soil_0_28cm": soil, "slope_deg": slope, "elevation_m": elev,
         "suscep_factor": 1.0}
    return [v[f] for f in SCHEMAS[schema]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--schema", choices=list(SCHEMAS), default="new")
    ap.add_argument("--alert", type=float, default=0.5)
    a = ap.parse_args()
    m = joblib.load(a.model)
    P = lambda rows: m.predict_proba(np.array(rows, dtype=float))[:, 1]
    results = []

    p0 = P([row(a.schema, 0, s) for s in (0.23, 0.30, 0.385)])
    results.append(("T1 zero-rain stays below alert", bool(p0.max() < a.alert), f"max P = {p0.max():.2f}"))

    rains = [0, 10, 25, 50, 75, 100, 150, 200, 300]
    pr = P([row(a.schema, r, 0.35) for r in rains])
    drops = [(rains[i], rains[i + 1]) for i in range(len(rains) - 1) if pr[i + 1] < pr[i] - 0.02]
    results.append(("T2 more rain never lowers risk", not drops,
                    " -> ".join(f"{r}mm:{p:.2f}" for r, p in zip(rains, pr))))

    soil_swing = abs(P([row(a.schema, 0, 0.385)])[0] - P([row(a.schema, 0, 0.23)])[0])
    rain_swing = abs(P([row(a.schema, 150, 0.30)])[0] - P([row(a.schema, 0, 0.30)])[0])
    results.append(("T3 calendar proxy weaker than a 150 mm storm", bool(soil_swing <= rain_swing),
                    f"soil-only swing {soil_swing:.2f} vs rain swing {rain_swing:.2f}"))

    slopes = [10, 20, 30, 40, 50]
    ps = P([row(a.schema, 120, 0.38, slope=s) for s in slopes])
    sdrops = [s for i, s in enumerate(slopes[1:]) if ps[i + 1] < ps[i] - 0.02]
    results.append(("T4 steeper never lowers risk", not sdrops,
                    " -> ".join(f"{s}deg:{p:.2f}" for s, p in zip(slopes, ps))))

    pf = P([row(a.schema, 200, 0.40, slope=3)])[0]
    results.append(("T5 flat ground stays low in cloudburst", bool(pf < a.alert), f"P = {pf:.2f}"))

    print(f"\nSanity probe: {a.model}  (schema={a.schema}, alert line={a.alert})")
    for name, ok, detail in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:45s} {detail}")
    n_fail = sum(not ok for _, ok, _ in results)
    print(f"\n{5 - n_fail}/5 passed" + ("  -> do NOT demo this model" if n_fail else "  -> safe to demo"))


if __name__ == "__main__":
    main()
