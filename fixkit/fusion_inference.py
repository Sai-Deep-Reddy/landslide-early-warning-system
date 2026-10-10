"""
fusion_inference.py  —  replaces the scoring part of backend/app/services/risk_engine.py

Fixes:
  * The UI explanation panel showed a formula that was NOT the one computed.
    Here the explanation is generated FROM the same numbers used to compute the score,
    so it can never drift again (single source of truth).
  * Hard-coded 0.55/0.45 blend -> learned meta-learner (train_fusion.py artifacts).
  * Falls back to physics-only (clearly labelled) if ML artifacts are missing.

Wire-up inside risk_engine.py (sketch):
    from fusion_inference import FusionModel
    FUSION = FusionModel("path/to/artifacts")
    result = FUSION.assess(slope_deg, elevation_m, weather_features)   # weather_fix.live_features()
"""
from __future__ import annotations

import os
from typing import Dict, Optional

import numpy as np

from physics_engine import physics_assessment

ML_FEATURES = ["rain_6h", "rain_24h", "rain_48h", "rain_72h", "rain_7d", "max_1h_24h",
               "soil_0_28cm", "slope_deg", "elevation_m"]

# Risk bands are POLICY choices. Set them from the operating threshold printed by
# train_fusion.py (threshold for the target recall), and say so on the slide.
ML_MIN_SLOPE = 15.0   # keep in sync with build_features.py spatial-control filter
DEFAULT_BANDS = [(0.85, "CRITICAL"), (0.65, "HIGH"), (0.40, "MODERATE"), (0.0, "LOW")]


def _logit(p, eps=1e-4):
    p = float(np.clip(p, eps, 1 - eps))
    return float(np.log(p / (1 - p)))


class FusionModel:
    def __init__(self, artifacts_dir: Optional[str] = None, bands=DEFAULT_BANDS):
        self.ml = self.meta = None
        self.bands = bands
        if artifacts_dir:
            try:
                import joblib
                self.ml = joblib.load(os.path.join(artifacts_dir, "xgb_monotone.joblib"))
                self.meta = joblib.load(os.path.join(artifacts_dir, "meta_learner.joblib"))
            except Exception as e:  # noqa
                print(f"[fusion] ML artifacts not loaded ({e}) -> physics-only mode")

    def band(self, risk: float) -> str:
        return next(name for lo, name in self.bands if risk >= lo)

    def assess(self, slope_deg: float, elevation_m: float, w: Dict, region: str = "sikkim_regional") -> Dict:
        phys = physics_assessment(slope_deg, w["daily_rain_7d"], w.get("soil_0_28cm"), region)
        p_phys = phys["slope_stability"]["p_failure"]
        id_ratio = phys["id_threshold"]["ratio"]

        # ML only sees slopes >= 15 deg in training (build_features.py) -> don't extrapolate
        ml_in_range = slope_deg >= ML_MIN_SLOPE
        if self.ml is not None and self.meta is not None and w.get("soil_0_28cm") is not None and ml_in_range:
            x = np.array([[w["rain_6h"], w["rain_24h"], w["rain_48h"], w["rain_72h"], w["rain_7d"],
                           w["max_1h_24h"], w["soil_0_28cm"], slope_deg, elevation_m]])
            p_ml = float(self.ml.predict_proba(x)[0, 1])
            z = np.array([_logit(p_ml), _logit(p_phys), float(np.log1p(id_ratio))])
            coef, b0 = self.meta.coef_[0], float(self.meta.intercept_[0])
            contrib = coef * z                                   # additive in log-odds space
            risk = float(1 / (1 + np.exp(-(b0 + contrib.sum()))))
            mode = "fused (learned meta-learner)"
            explanation = {
                "formula": "risk = sigmoid(b0 + w1*logit(ML) + w2*logit(Physics) + w3*log(1+ID_ratio))",
                "b0": round(b0, 3),
                "weights": {"ML": round(float(coef[0]), 3), "Physics": round(float(coef[1]), 3),
                            "ID_threshold": round(float(coef[2]), 3)},
                "inputs": {"ML_prob": round(p_ml, 3), "Physics_P_fail": p_phys, "ID_ratio": id_ratio},
                "log_odds_contribution": {"ML": round(float(contrib[0]), 3),
                                          "Physics": round(float(contrib[1]), 3),
                                          "ID_threshold": round(float(contrib[2]), 3)},
            }
        else:
            p_ml = None
            risk = p_phys
            mode = ("physics-only (slope outside ML training range)" if not ml_in_range
                    else "physics-only (ML unavailable or soil data missing)")
            explanation = {"formula": "risk = P(FoS < 1) from infinite-slope Monte Carlo",
                           "inputs": {"Physics_P_fail": p_phys, "ID_ratio": id_ratio}}

        # Safety override: published I-D threshold breached on a slope that can actually fail.
        # (Flat valley floors are excluded; runout/debris-flow reach is a roadmap item.)
        override = False
        if phys["threshold_breached"] and slope_deg >= ML_MIN_SLOPE and risk < 0.65:
            risk, override = 0.65, True

        return {
            "risk": round(risk, 3), "level": self.band(risk), "mode": mode,
            "published_threshold_override": override,
            "physics": phys, "ml_probability": None if p_ml is None else round(p_ml, 3),
            "explanation": explanation,
        }


if __name__ == "__main__":
    fm = FusionModel(None)   # physics-only demo
    w = {"daily_rain_7d": [10, 15, 30, 40, 55, 80, 120], "soil_0_28cm": 0.41,
         "rain_6h": 40, "rain_24h": 120, "rain_48h": 200, "rain_72h": 255, "rain_7d": 350, "max_1h_24h": 25}
    import json
    print(json.dumps(fm.assess(38.0, 1400, w), indent=2))
