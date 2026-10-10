"""
fetch_real_landslides.py  —  replace the synthetic 155-event file with REAL, CITED events.

Sources (all free):
  A) NASA COOLR / Global Landslide Catalog (rainfall-triggered events with dates, from news &
     reports, each with a citation).  ArcGIS REST, no key.
  B) Manual rows you verify yourselves: GSI Bhusanket / Bhukosh inventory, Sikkim SDMA
     situation reports, GSI Post-Disaster Landslide Study reports, credible news (PTI/Reuters).
     -> put them in manual_events.csv. EVERY row needs a source_url.

Output: real_events.csv with a `source_url` / `citation` column on every row.
Rule: no source -> row rejected. This is what you show the judges.

Usage:
  python fetch_real_landslides.py --region sikkim        # Sikkim + Darjeeling hills
  python fetch_real_landslides.py --region ner           # all North-East (bigger dataset)
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import sys
from typing import Dict, List

import requests

# The service hosts two layer families: "coolr_reports" (GLC + citizen reports, date-stamped)
# and "coolr_events" (mapped event inventories). Try reports first.
CANDIDATE_LAYERS = [
    "https://gis.earthdata.nasa.gov/gis05/rest/services/Landslides/COOLR_Reports_Points/FeatureServer/0/query",
    "https://gis.earthdata.nasa.gov/gis05/rest/services/Landslides/COOLR_Events_Points/FeatureServer/0/query",
]

BBOX = {
    "sikkim": (88.0, 26.8, 89.0, 28.2),        # lon_min, lat_min, lon_max, lat_max (incl. Darjeeling hills)
    "ner":    (88.0, 21.9, 97.5, 29.5),
}

REQUIRED = ["event_id", "event_date", "lat", "lon", "location_accuracy", "trigger", "source_url", "citation"]


def query_layer(url: str, bbox, offset: int = 0) -> Dict:
    xmin, ymin, xmax, ymax = bbox
    params = {
        "where": "1=1",
        "geometry": json.dumps({"xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax,
                                "spatialReference": {"wkid": 4326}}),
        "geometryType": "esriGeometryEnvelope", "inSR": 4326, "outSR": 4326,
        "spatialRel": "esriSpatialRelIntersects", "outFields": "*",
        "returnGeometry": "true", "resultOffset": offset, "resultRecordCount": 2000, "f": "json",
    }
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def to_date(v) -> str:
    """ArcGIS returns epoch-ms for date fields; sometimes strings."""
    if v is None or v == "":
        return ""
    if isinstance(v, (int, float)):
        return dt.datetime.utcfromtimestamp(v / 1000).date().isoformat()
    return str(v)[:10]


def normalise(feat: Dict) -> Dict:
    a = {k.lower(): v for k, v in feat.get("attributes", {}).items()}
    g = feat.get("geometry", {})
    return {
        "event_id": f"COOLR-{a.get('objectid') or a.get('ev_id') or a.get('event_id')}",
        "event_date": to_date(a.get("event_date") or a.get("ev_date") or a.get("date")),
        "event_time": a.get("event_time") or "",
        "lat": g.get("y"), "lon": g.get("x"),
        "location_accuracy": a.get("location_accuracy") or a.get("loc_acc") or "",
        "trigger": a.get("landslide_trigger") or a.get("trigger") or "",
        "size": a.get("landslide_size") or a.get("size") or "",
        "fatalities": a.get("fatality_count") or a.get("fatalities") or "",
        "place": a.get("event_title") or a.get("title") or a.get("location_description") or "",
        "source_url": a.get("source_link") or a.get("src_link") or a.get("url") or "",
        "citation": a.get("source_name") or a.get("citation") or "NASA COOLR",
        "dataset": "NASA COOLR/GLC",
    }


def fetch_coolr(bbox) -> List[Dict]:
    for url in CANDIDATE_LAYERS:
        try:
            rows, offset = [], 0
            while True:
                js = query_layer(url, bbox, offset)
                if "error" in js:
                    raise RuntimeError(js["error"])
                feats = js.get("features", [])
                rows += [normalise(f) for f in feats]
                if not js.get("exceededTransferLimit") or not feats:
                    break
                offset += len(feats)
            print(f"[COOLR] {len(rows)} features from {url.split('/services/')[1]}")
            if rows:
                return rows
        except Exception as e:  # noqa
            print(f"[COOLR] {url} failed: {e}")
    print("[COOLR] All endpoints failed. Download CSV manually from the COOLR download page "
          "(linked at landslides.nasa.gov) and save as coolr_manual.csv")
    return []


def load_manual(path: str) -> List[Dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return [dict(r, dataset=r.get("dataset") or "manual-verified") for r in csv.DictReader(f)]


def validate(rows: List[Dict]) -> List[Dict]:
    ok, bad = [], 0
    seen = set()
    for r in rows:
        if not r.get("event_date") or r.get("lat") in (None, "") or r.get("lon") in (None, ""):
            bad += 1; continue
        if not (r.get("source_url") or "").startswith("http"):
            bad += 1; continue                         # NO SOURCE = NOT REAL DATA
        trig = (r.get("trigger") or "").lower()
        if trig and not any(k in trig for k in ("rain", "downpour", "monsoon", "storm", "cloud", "unknown")):
            bad += 1; continue                         # keep rainfall-triggered only for this model
        key = (r["event_date"], round(float(r["lat"]), 3), round(float(r["lon"]), 3))
        if key in seen:
            bad += 1; continue
        seen.add(key)
        ok.append(r)
    print(f"[VALIDATE] kept {len(ok)} | rejected {bad} (no date/coords/source, non-rain trigger, or duplicate)")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="sikkim", choices=list(BBOX))
    ap.add_argument("--manual", default="manual_events.csv")
    ap.add_argument("--out", default="real_events.csv")
    ap.add_argument("--min-year", type=int, default=2007)
    args = ap.parse_args()

    rows = fetch_coolr(BBOX[args.region]) + load_manual(args.manual) + load_manual("coolr_manual.csv")
    rows = [r for r in rows if r.get("event_date", "")[:4].isdigit() and int(r["event_date"][:4]) >= args.min_year]
    rows = validate(rows)
    if not rows:
        sys.exit("No valid events. Fill manual_events.csv (see template) and re-run.")
    cols = sorted({k for r in rows for k in r}, key=lambda k: (k not in REQUIRED, k))
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader(); w.writerows(rows)
    years = {}
    for r in rows:
        years[r["event_date"][:4]] = years.get(r["event_date"][:4], 0) + 1
    print(f"[DONE] {len(rows)} real events -> {args.out}  | per year: {dict(sorted(years.items()))}")


if __name__ == "__main__":
    main()
