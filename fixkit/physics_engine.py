"""
physics_engine.py  —  drop-in replacement for the heuristic "physics hazard index".

Two honest, citable physics components:

1) Rainfall Intensity-Duration (I-D) threshold exceedance
   - Sikkim regional : I = 43.26 * D^-0.78   (I in mm/day, D in days)   Harilal et al. 2019, Landslides 16
   - Gangtok local   : I = 100   * D^-0.92   (I in mm/day, D in days)   Harilal et al. 2019, Landslides 16
   - Caine global    : I = 14.82 * D^-0.39   (I in mm/h,   D in hours)  Caine 1980
   NOTE: Caine is NOT a safe "floor" for Sikkim. At D = 1 day Caine needs ~103 mm,
         the Sikkim regional threshold needs only ~43 mm. Use the regional equation.

2) Infinite-slope limit-equilibrium Factor of Safety (the same stability core that
   TRIGRS / SHALSTAB / SINMAP use), with Monte Carlo over uncertain soil strength
   -> gives P(FoS < 1), a physically meaningful probability of failure.

       FoS = c' / (g * z * sin(b) * cos(b))  +  (1 - m * g_w / g) * tan(phi') / tan(b)

   b = slope angle, c' = effective cohesion (kPa), phi' = friction angle,
   g = soil unit weight (kN/m3), g_w = 9.81, z = failure depth (m),
   m = wetness = saturated fraction of the soil column (0..1).

Honest naming for slides:  "Infinite-slope FoS with rainfall-driven wetness and
Monte Carlo strength uncertainty (TRIGRS-style stability core). Full TRIGRS transient
infiltration = roadmap."
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np

G_W = 9.81  # unit weight of water, kN/m3

# ----------------------------------------------------------------------------
# 1) I-D thresholds
# ----------------------------------------------------------------------------
ID_THRESHOLDS: Dict[str, Dict] = {
    "sikkim_regional": {"alpha": 43.26, "beta": 0.78, "unit": "day",
                        "ref": "Harilal et al. (2019) Landslides 16, doi:10.1007/s10346-019-01244-1"},
    "gangtok_local":   {"alpha": 100.0, "beta": 0.92, "unit": "day",
                        "ref": "Harilal et al. (2019) Landslides 16, doi:10.1007/s10346-019-01244-1"},
    "caine_global":    {"alpha": 14.82, "beta": 0.39, "unit": "hour",
                        "ref": "Caine (1980) Geografiska Annaler A 62"},
}


def threshold_intensity(duration: float, name: str = "sikkim_regional") -> float:
    """Threshold mean intensity for a given duration (units follow the equation)."""
    t = ID_THRESHOLDS[name]
    return t["alpha"] * duration ** (-t["beta"])


def id_exceedance_daily(daily_rain_mm: Sequence[float],
                        name: str = "sikkim_regional",
                        max_days: int = 7) -> Dict:
    """
    daily_rain_mm: daily totals, OLDEST first, MOST RECENT last.
    For each window D = 1..max_days: I_obs = sum(last D days)/D ; ratio = I_obs / I_threshold(D).
    Returns the worst (max) ratio. ratio >= 1.0 means the published threshold is exceeded.
    """
    t = ID_THRESHOLDS[name]
    if t["unit"] != "day":
        raise ValueError(f"{name} is an hourly threshold; use id_exceedance_hourly")
    rain = np.asarray(daily_rain_mm, dtype=float)
    rain = np.nan_to_num(rain, nan=0.0)
    best = {"ratio": 0.0, "duration_days": None, "observed_mm_per_day": 0.0,
            "threshold_mm_per_day": None, "equation": name, "ref": t["ref"]}
    for d in range(1, min(max_days, len(rain)) + 1):
        i_obs = rain[-d:].sum() / d
        i_th = threshold_intensity(d, name)
        r = i_obs / i_th
        if r > best["ratio"]:
            best.update(ratio=round(float(r), 3), duration_days=d,
                        observed_mm_per_day=round(float(i_obs), 1),
                        threshold_mm_per_day=round(float(i_th), 1))
    return best


def id_exceedance_hourly(hourly_rain_mm: Sequence[float],
                         name: str = "caine_global",
                         durations_h: Sequence[int] = (1, 3, 6, 12, 24, 48, 72, 120, 168)) -> Dict:
    """Same idea for hourly thresholds (Caine). hourly_rain_mm oldest first."""
    t = ID_THRESHOLDS[name]
    if t["unit"] != "hour":
        raise ValueError(f"{name} is a daily threshold; use id_exceedance_daily")
    rain = np.nan_to_num(np.asarray(hourly_rain_mm, dtype=float), nan=0.0)
    best = {"ratio": 0.0, "duration_h": None, "equation": name, "ref": t["ref"]}
    for d in durations_h:
        if d > len(rain):
            break
        r = (rain[-d:].sum() / d) / threshold_intensity(d, name)
        if r > best["ratio"]:
            best.update(ratio=round(float(r), 3), duration_h=d)
    return best


def hourly_to_daily(hourly_rain_mm: Sequence[float]) -> List[float]:
    """Rolling 24h blocks ending at the most recent hour (so 'day 1' = last 24h)."""
    h = np.nan_to_num(np.asarray(hourly_rain_mm, dtype=float), nan=0.0)
    n_days = len(h) // 24
    if n_days == 0:
        return [float(h.sum())]
    h = h[-n_days * 24:]
    return [float(b.sum()) for b in h.reshape(n_days, 24)]


# ----------------------------------------------------------------------------
# 2) Infinite-slope Factor of Safety
# ----------------------------------------------------------------------------
@dataclass
class SoilParams:
    """Uniform ranges for Monte Carlo. Defaults = typical residual soils / colluvium
    over phyllite-schist-gneiss in the Sikkim Himalaya (literature ranges; calibrate!)."""
    cohesion_kpa: tuple = (2.0, 12.0)       # effective cohesion incl. some root cohesion
    phi_deg: tuple = (26.0, 38.0)           # effective friction angle
    depth_m: tuple = (1.0, 3.0)             # shallow-landslide failure depth
    unit_weight: tuple = (18.0, 20.0)       # kN/m3
    drainable_porosity: tuple = (0.08, 0.18)
    theta_fc: float = 0.30                  # field capacity (m3/m3)
    theta_sat: float = 0.45                 # saturation (m3/m3)
    n_samples: int = 2000
    seed: int = 7


def factor_of_safety(slope_deg, cohesion_kpa, phi_deg, depth_m, unit_weight, wetness):
    """Vectorised infinite-slope FoS. Returns inf for ~flat ground."""
    b = np.radians(np.asarray(slope_deg, dtype=float))
    b = np.clip(b, np.radians(0.5), np.radians(89.0))
    coh = np.asarray(cohesion_kpa) / (np.asarray(unit_weight) * np.asarray(depth_m) * np.sin(b) * np.cos(b))
    fric = (1.0 - np.asarray(wetness) * G_W / np.asarray(unit_weight)) * np.tan(np.radians(phi_deg)) / np.tan(b)
    return coh + fric


def antecedent_rain_index(daily_rain_mm: Sequence[float], k: float = 0.85) -> float:
    """Classic API: API_t = k * API_{t-1} + P_t  (oldest first)."""
    api = 0.0
    for p in np.nan_to_num(np.asarray(daily_rain_mm, dtype=float), nan=0.0):
        api = k * api + p
    return float(api)


def wetness_from_inputs(soil_moisture: Optional[float], api_mm: float,
                        depth_m, drainable_porosity, p: SoilParams):
    """
    Saturated fraction m (0..1). Two pathways, take the max:
      a) reanalysis soil moisture above field capacity -> perched water table
      b) rainfall storage: API filling the drainable pore space of the column
    """
    m_soil = 0.0
    if soil_moisture is not None and not math.isnan(soil_moisture):
        m_soil = float(np.clip((soil_moisture - p.theta_fc) / (p.theta_sat - p.theta_fc), 0.0, 1.0))
    capacity_mm = np.asarray(drainable_porosity) * np.asarray(depth_m) * 1000.0
    m_rain = np.clip(api_mm / capacity_mm, 0.0, 1.0)
    return np.maximum(m_soil, m_rain)


def failure_probability(slope_deg: float,
                        daily_rain_mm: Sequence[float],
                        soil_moisture: Optional[float] = None,
                        params: Optional[SoilParams] = None) -> Dict:
    """Monte Carlo P(FoS < 1). Deterministic for a given seed (reproducible demos)."""
    p = params or SoilParams()
    rng = np.random.default_rng(p.seed)
    n = p.n_samples
    c = rng.uniform(*p.cohesion_kpa, n)
    phi = rng.uniform(*p.phi_deg, n)
    z = rng.uniform(*p.depth_m, n)
    g = rng.uniform(*p.unit_weight, n)
    ne = rng.uniform(*p.drainable_porosity, n)

    api = antecedent_rain_index(daily_rain_mm)
    m = wetness_from_inputs(soil_moisture, api, z, ne, p)
    fos = factor_of_safety(slope_deg, c, phi, z, g, m)
    fos_dry = factor_of_safety(slope_deg, c, phi, z, g, 0.0)
    return {
        "p_failure": round(float(np.mean(fos < 1.0)), 3),
        "fos_median": round(float(np.median(fos)), 3),
        "fos_p10": round(float(np.percentile(fos, 10)), 3),
        "fos_dry_median": round(float(np.median(fos_dry)), 3),
        "wetness_median": round(float(np.median(m)), 3),
        "api_mm": round(api, 1),
        "model": "infinite-slope limit equilibrium + Monte Carlo strength uncertainty",
    }


# ----------------------------------------------------------------------------
# 3) One call for the API / UI
# ----------------------------------------------------------------------------
def physics_assessment(slope_deg: float,
                       daily_rain_mm: Sequence[float],
                       soil_moisture: Optional[float] = None,
                       region: str = "sikkim_regional",
                       params: Optional[SoilParams] = None) -> Dict:
    idx = id_exceedance_daily(daily_rain_mm, region)
    fos = failure_probability(slope_deg, daily_rain_mm, soil_moisture, params)
    return {
        "id_threshold": idx,                 # ratio >= 1 => published threshold exceeded
        "slope_stability": fos,              # p_failure in [0,1]
        "threshold_breached": idx["ratio"] >= 1.0,
    }


if __name__ == "__main__":
    # Quick demo — numbers you can sanity-check by hand
    print("Sikkim 1-day threshold:", round(threshold_intensity(1), 1), "mm/day")
    print("Sikkim 2-day threshold:", round(threshold_intensity(2) * 2, 1), "mm cumulative over 48h")
    print("Caine 24h threshold   :", round(threshold_intensity(24, 'caine_global') * 24, 1), "mm cumulative over 24h")
    for slope in (20, 35, 45):
        dry = physics_assessment(slope, [0, 0, 0, 0, 0, 0, 0])
        wet = physics_assessment(slope, [20, 30, 25, 40, 60, 90, 150])
        print(f"slope {slope:>2}deg  dry P(fail)={dry['slope_stability']['p_failure']:.2f}  "
              f"storm P(fail)={wet['slope_stability']['p_failure']:.2f}  ID ratio={wet['id_threshold']['ratio']}")
