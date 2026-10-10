"""
terrain_npz.py  —  fixes "click anywhere" on the live Vercel demo.

THE BUG: rasterio is not in requirements.txt, so on Vercel the DEM never loads and
terrain_service returns the NEAREST STATION'S TYPED slope (e.g. 34.5 deg for anywhere near
Gangtok). Also, points outside the raster are silently clamped to the edge pixel.

THE FIX: precompute elevation + Horn slope ONCE on your laptop into a compressed .npz
(numpy only at runtime, no rasterio on the server), and return None outside coverage.

  Laptop (needs rasterio):  python terrain_npz.py build ../backend/app/data/dem/processed/sikkim_dem_srtm_30m.tif terrain_sikkim.npz
  Server (numpy only)    :  from terrain_npz import NpzTerrain; T = NpzTerrain("terrain_sikkim.npz"); T.lookup(27.33, 88.61)
"""
from __future__ import annotations

import math
import sys
from typing import Dict, Optional

import numpy as np


def horn_slope_deg(z: np.ndarray, lat_center: float, res_deg: float) -> np.ndarray:
    z = z.astype(np.float32)
    dy = res_deg * 111132.95
    dx = res_deg * 111412.84 * math.cos(math.radians(lat_center))
    p = np.pad(z, 1, mode="edge")
    tl, t, tr = p[:-2, :-2], p[:-2, 1:-1], p[:-2, 2:]
    l, r = p[1:-1, :-2], p[1:-1, 2:]
    bl, b, br = p[2:, :-2], p[2:, 1:-1], p[2:, 2:]
    dzdx = ((tr + 2 * r + br) - (tl + 2 * l + bl)) / (8 * dx)
    dzdy = ((tl + 2 * t + tr) - (bl + 2 * b + br)) / (8 * dy)
    return np.degrees(np.arctan(np.hypot(dzdx, dzdy)))


def build(tif_path: str, out_path: str, bbox=None):
    import rasterio  # laptop only
    with rasterio.open(tif_path) as ds:
        z = ds.read(1).astype(np.float32)
        nod = ds.nodata
        left, bottom, right, top = ds.bounds
        res = ds.res[0]
    if nod is not None:
        z[z == nod] = np.nan
    if bbox:  # optional crop: lon_min, lat_min, lon_max, lat_max
        c0 = int((bbox[0] - left) / res); c1 = int((bbox[2] - left) / res)
        r0 = int((top - bbox[3]) / res); r1 = int((top - bbox[1]) / res)
        z = z[r0:r1, c0:c1]; left, top = left + c0 * res, top - r0 * res
    slope = horn_slope_deg(np.nan_to_num(z, nan=np.nanmean(z)), top - z.shape[0] * res / 2, res)
    slope[np.isnan(z)] = 255
    elev = np.where(np.isnan(z), -32768, np.round(z)).astype(np.int16)
    np.savez_compressed(out_path, elev=elev, slope=np.clip(np.round(slope), 0, 255).astype(np.uint8),
                        left=left, top=top, res=res)
    print(f"saved {out_path}: {elev.shape}, slope median {np.median(slope[slope < 90]):.1f} deg")


class NpzTerrain:
    def __init__(self, path: str):
        d = np.load(path)
        self.elev, self.slope = d["elev"], d["slope"]
        self.left, self.top, self.res = float(d["left"]), float(d["top"]), float(d["res"])

    def lookup(self, lat: float, lon: float) -> Optional[Dict]:
        r = int((self.top - lat) / self.res); c = int((lon - self.left) / self.res)
        if not (0 <= r < self.elev.shape[0] and 0 <= c < self.elev.shape[1]):
            return None                                   # outside coverage: say so, don't clamp
        if self.elev[r, c] == -32768 or self.slope[r, c] == 255:
            return None
        return {"elevation_m": float(self.elev[r, c]), "slope_deg": float(self.slope[r, c]),
                "dem_source": "SRTM 1 arc-second (precomputed Horn slope)"}


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "build":
        # default crop = Sikkim pilot bbox (keeps the file small enough for Vercel)
        bbox = tuple(map(float, sys.argv[4].split(","))) if len(sys.argv) > 4 else (88.0, 27.0, 88.95, 28.15)
        build(sys.argv[2], sys.argv[3], bbox)
    else:
        print(__doc__)
