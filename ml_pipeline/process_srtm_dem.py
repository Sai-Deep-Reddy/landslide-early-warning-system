"""
USGS/NASA SRTM 1 Arc-Second (30m) DEM Processing Pipeline
Mosaics and verifies genuine SRTM tiles (N27E088 and N28E088) into production GeoTIFF.
"""

import sys
import os
import numpy as np
import rasterio
from rasterio.transform import from_bounds

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEM_DIR = os.path.join(PROJECT_ROOT, "backend", "app", "data", "dem")
RAW_DIR = os.path.join(DEM_DIR, "raw")
PROCESSED_DIR = os.path.join(DEM_DIR, "processed")


def process_srtm_tiles():
    """
    Mosaics raw USGS/NASA SRTM 1-arcsecond tiles (N28E088 and N27E088)
    into a continuous EPSG:4326 GeoTIFF covering the entire Sikkim region.
    """
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    
    hgt28_path = os.path.join(RAW_DIR, "N28E088.hgt")
    hgt27_path = os.path.join(RAW_DIR, "N27E088.hgt")

    if not os.path.exists(hgt28_path) or not os.path.exists(hgt27_path):
        raise FileNotFoundError(
            f"Raw SRTM tiles missing in {RAW_DIR}. "
            f"Expected N28E088.hgt and N27E088.hgt."
        )

    # Read 3601x3601 16-bit signed integer big-endian grids
    data28 = np.fromfile(hgt28_path, dtype=">i2").reshape((3601, 3601))
    data27 = np.fromfile(hgt27_path, dtype=">i2").reshape((3601, 3601))

    # Stack N28 on top of N27 (omitting overlapping border row at lat 28.0)
    combined = np.vstack([data28[:-1, :], data27])
    
    # Bounding box: West=88.0, South=27.0, East=89.0, North=29.0
    transform = from_bounds(88.0, 27.0, 89.0, 29.0, 3601, 7201)
    out_tif = os.path.join(PROCESSED_DIR, "sikkim_dem_srtm_30m.tif")

    with rasterio.open(
        out_tif,
        "w",
        driver="GTiff",
        height=combined.shape[0],
        width=combined.shape[1],
        count=1,
        dtype=combined.dtype,
        crs="EPSG:4326",
        transform=transform,
        nodata=-32768,
        compress="deflate"
    ) as dst:
        dst.write(combined, 1)

    print(f"[SUCCESS] Processed genuine USGS/NASA SRTM DEM GeoTIFF saved at: {out_tif}")
    print(f"  Dimensions: {combined.shape[1]}x{combined.shape[0]} pixels (~30m resolution)")
    print(f"  Elevation range: min={combined[combined > -100].min()}m, max={combined.max()}m")
    print(f"  Coverage: Lat [27.0, 29.0], Lon [88.0, 89.0]")


if __name__ == "__main__":
    process_srtm_tiles()
