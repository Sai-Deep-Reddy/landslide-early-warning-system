"""
build_features.py  —  leakage-free training table from REAL events.

Why the old negatives were a problem:
  positives = 21 hand-picked road anchors, 91% in Jun-Sep
  negatives = uniform random points, uniform May-Oct
  => model learns "near a road anchor" + "is it Jun-Sep", not landslide physics.

Case-crossover design (standard in epidemiology & landslide-trigger studies):
  TEMPORAL control : SAME location, different monsoon date (no event within 5 km / +-7 days)
                     -> location can't be used to cheat
  SPATIAL control  : SAME date, different location >= 5 km away on a real slope
                     -> calendar/month can't be used to cheat
  What's left for the model to learn = the weather difference. That's the signal you want.

Usage (needs internet; ~2-4 s per sample, results cached):
  python build_features.py --events real_events.csv --out features.csv --temporal 2 --spatial 1
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import os
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

from physics_engine import physics_assessment
from weather_fix import features_at

CACHE = ".feature_cache.json"
MONSOON = (5, 6, 7, 8, 9, 10)


# ---- terrain: reuse the team's SRTM service if available ---------------------------------
def _terrain_fn():
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in [os.path.join(here, "..", "backend"), os.path.join(here, "backend"), "backend"]:
        if os.path.isdir(cand) and cand not in sys.path:
            sys.path.insert(0, cand)
    try:
        from app.services.terrain_service import terrain_service  # type: ignore
        def f(lat, lon):
            t = terrain_service.compute_terrain_metrics(lat, lon)
            return {"slope_deg": t["slope_deg"], "elevation_m": t["elevation_m"]}
        return f
    except Exception as e:  # noqa
        print(f"[WARN] terrain_service not importable ({e}); slope will be missing")
        return lambda lat, lon: {"slope_deg": None, "elevation_m": None}


def km(a_lat, a_lon, b_lat, b_lon) -> float:
    r = 6371.0
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dphi, dl = p2 - p1, math.radians(b_lon - a_lon)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def load_events(path: str) -> List[Dict]:
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["lat"], r["lon"] = float(r["lat"]), float(r["lon"])
        r["date"] = dt.date.fromisoformat(r["event_date"][:10])
    return rows


def near_event(events, lat, lon, day, km_r=5.0, days=7) -> bool:
    return any(abs((e["date"] - day).days) <= days and km(e["lat"], e["lon"], lat, lon) < km_r for e in events)


def make_samples(events: List[Dict], n_temporal: int, n_spatial: int, bbox, seed: int, terrain) -> List[Dict]:
    rng = random.Random(seed)
    years = sorted({e["date"].year for e in events})
    out = []
    for e in events:
        out.append({"sample_id": e["event_id"], "label": 1, "neg_type": "", "lat": e["lat"], "lon": e["lon"],
                    "day": e["date"], "group": e["event_id"], "source_url": e.get("source_url", "")})
        # temporal controls: same place, other monsoon dates
        k, tries = 0, 0
        while k < n_temporal and tries < 200:
            tries += 1
            d = dt.date(rng.choice(years), rng.choice(MONSOON), rng.randint(1, 28))
            if abs((d - e["date"]).days) < 30 or near_event(events, e["lat"], e["lon"], d):
                continue
            out.append({"sample_id": f"{e['event_id']}-T{k}", "label": 0, "neg_type": "temporal",
                        "lat": e["lat"], "lon": e["lon"], "day": d, "group": e["event_id"], "source_url": ""})
            k += 1
        # spatial controls: same date, elsewhere on a real slope
        k, tries = 0, 0
        while k < n_spatial and tries < 300:
            tries += 1
            lat = rng.uniform(bbox[1], bbox[3]); lon = rng.uniform(bbox[0], bbox[2])
            if near_event(events, lat, lon, e["date"], km_r=5.0, days=3):
                continue
            t = terrain(lat, lon)
            if t["slope_deg"] is not None and t["slope_deg"] < 15:   # flat valley floors are trivial negatives
                continue
            out.append({"sample_id": f"{e['event_id']}-S{k}", "label": 0, "neg_type": "spatial",
                        "lat": round(lat, 4), "lon": round(lon, 4), "day": e["date"], "group": e["event_id"],
                        "source_url": ""})
            k += 1
    return out


def enrich(s: Dict, terrain, cache: Dict) -> Optional[Dict]:
    key = f"{s['lat']:.4f},{s['lon']:.4f},{s['day']}"
    if key not in cache:
        # cutoff = 00:00 IST of the day => only rain BEFORE the event day (no post-event leakage)
        cache[key] = features_at(s["lat"], s["lon"], dt.datetime.combine(s["day"], dt.time(0, 0)))
    w = cache[key]
    if not w:
        return None
    t = terrain(s["lat"], s["lon"])
    if t["slope_deg"] is None:
        return None
    phys = physics_assessment(t["slope_deg"], w["daily_rain_7d"], w["soil_0_28cm"])
    row = {k: v for k, v in s.items() if k != "day"}
    row.update(event_date=s["day"].isoformat(), year=s["day"].year,
               slope_deg=t["slope_deg"], elevation_m=t["elevation_m"],
               **{k: v for k, v in w.items() if k != "daily_rain_7d"},
               id_ratio=phys["id_threshold"]["ratio"],
               p_failure_phys=phys["slope_stability"]["p_failure"])
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", default="real_events.csv")
    ap.add_argument("--out", default="features.csv")
    ap.add_argument("--temporal", type=int, default=2)
    ap.add_argument("--spatial", type=int, default=1)
    ap.add_argument("--bbox", default="88.0,26.8,89.0,28.2", help="lon_min,lat_min,lon_max,lat_max")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()

    terrain = _terrain_fn()
    events = load_events(a.events)
    samples = make_samples(events, a.temporal, a.spatial, [float(x) for x in a.bbox.split(",")], a.seed, terrain)
    print(f"[SAMPLES] {sum(s['label'] for s in samples)} positives, "
          f"{sum(1 - s['label'] for s in samples)} negatives")

    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    with ThreadPoolExecutor(a.workers) as ex:
        rows = list(ex.map(lambda s: enrich(s, terrain, cache), samples))
    json.dump(cache, open(CACHE, "w"))
    kept = [r for r in rows if r]
    print(f"[ENRICH] kept {len(kept)}/{len(rows)} (dropped = missing weather/terrain; NOT imputed)")
    cols = list(kept[0].keys())
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(kept)
    print(f"[DONE] -> {a.out}")


if __name__ == "__main__":
    main()
