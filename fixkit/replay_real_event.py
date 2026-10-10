"""
replay_real_event.py  —  replaces the hand-typed timelines in backend/app/data/test_events.json

Computes the risk timeline HOUR BY HOUR from real archived rainfall (ERA5 via Open-Meteo),
using only data available at each hour, and measures lead time honestly.

Lead time rules (say these out loud to judges):
  * If the report gives an event TIME  -> lead = event_time - first alert hour
  * If the report gives only a DATE    -> lead is measured to 00:00 of that date
                                          (conservative lower bound; stated as such)
  * IMPORTANT: if this event was in the TRAINING set, the replay is a demo, not evidence.
               Use an event from the TEST years for any "validation" claim.

Usage:
  python replay_real_event.py --lat 27.5042 --lon 88.5284 --date 2024-06-13 \
      --slope 38 --name "Mangan, North Sikkim" --source "<news/SDMA url>" \
      [--time 02:00] [--artifacts artifacts/] [--out replay_mangan_2024.json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json

import numpy as np

from fusion_inference import FusionModel
from weather_fix import ARCHIVE_SOIL, _weighted_soil, fetch_archive


def timeline(lat, lon, event_day: dt.date, event_time: str | None, slope_deg: float,
             elevation_m: float, model: FusionModel, hours_before: int = 72, alert_level: float = 0.65):
    start = event_day - dt.timedelta(days=11)
    data = fetch_archive(lat, lon, start, event_day + dt.timedelta(days=1))
    if not data:
        raise SystemExit("No archive data (internet? date older than ~5 days?)")
    h = data["hourly"]
    times = [dt.datetime.fromisoformat(t) for t in h["time"]]
    precip = np.nan_to_num(np.array(h["precipitation"], dtype=float), nan=0.0)

    ref = dt.datetime.combine(event_day, dt.time.fromisoformat(event_time) if event_time else dt.time(0, 0))
    i_ref = max(i for i, t in enumerate(times) if t <= ref)
    steps, first_alert = [], None
    for i in range(max(168, i_ref - hours_before), i_ref + 1):
        p = precip[: i + 1]                                    # ONLY data up to this hour
        daily = [float(p[len(p) - 24 * (k + 1): len(p) - 24 * k].sum()) for k in reversed(range(7))]
        w = {"rain_6h": float(p[-6:].sum()), "rain_24h": float(p[-24:].sum()),
             "rain_48h": float(p[-48:].sum()), "rain_72h": float(p[-72:].sum()),
             "rain_7d": float(p[-168:].sum()), "max_1h_24h": float(p[-24:].max()),
             "soil_0_28cm": _weighted_soil(h, ARCHIVE_SOIL, i), "daily_rain_7d": daily}
        r = model.assess(slope_deg, elevation_m, w)
        if first_alert is None and r["risk"] >= alert_level:
            first_alert = times[i]
        steps.append({"timestamp": times[i].isoformat(), "rel_hour": round((times[i] - ref).total_seconds() / 3600, 1),
                      "rain_intensity_mmh": round(float(precip[i]), 1), "rain_24h_mm": round(w["rain_24h"], 1),
                      "rain_7d_mm": round(w["rain_7d"], 1), "soil_0_28cm": w["soil_0_28cm"],
                      "id_ratio": r["physics"]["id_threshold"]["ratio"],
                      "p_failure_physics": r["physics"]["slope_stability"]["p_failure"],
                      "risk_score": r["risk"], "risk_level": r["level"], "mode": r["mode"]})
    lead = None if first_alert is None else round((ref - first_alert).total_seconds() / 3600, 1)
    return steps, first_alert, lead, ref


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, required=True); ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--date", required=True); ap.add_argument("--time", default=None, help="HH:MM IST if reported")
    ap.add_argument("--slope", type=float, required=True); ap.add_argument("--elev", type=float, default=1300)
    ap.add_argument("--name", default="event"); ap.add_argument("--source", required=True)
    ap.add_argument("--artifacts", default=None); ap.add_argument("--alert", type=float, default=0.65)
    ap.add_argument("--in-training-set", action="store_true", help="flag events used for training")
    ap.add_argument("--out", default="replay.json")
    a = ap.parse_args()

    model = FusionModel(a.artifacts)
    steps, first, lead, ref = timeline(a.lat, a.lon, dt.date.fromisoformat(a.date), a.time,
                                       a.slope, a.elev, model, alert_level=a.alert)
    out = {
        "event": a.name, "lat": a.lat, "lon": a.lon, "reference_time": ref.isoformat(),
        "reference_basis": "reported event time" if a.time else "00:00 of reported date (lower bound)",
        "source_url": a.source, "alert_threshold": a.alert,
        "first_alert": None if first is None else first.isoformat(), "lead_time_hours": lead,
        "evidence_grade": "DEMO ONLY (event in training data)" if a.in_training_set else "held-out event",
        "data": "ERA5 / ERA5-Land via Open-Meteo archive (hourly)", "timeline": steps,
    }
    json.dump(out, open(a.out, "w"), indent=2)
    print(f"{a.name}: first alert {out['first_alert']} | lead time {lead} h "
          f"({out['reference_basis']}) | {out['evidence_grade']} -> {a.out}")
    if lead is None:
        print("No alert before the event. REPORT THIS HONESTLY - a miss is a finding, not a failure.")


if __name__ == "__main__":
    main()
