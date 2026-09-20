"""
[DEPRECATED / RETIRED FROM PRODUCTION]
Legacy Synthetic DEM Generator Script

WARNING:
This script contains mathematical approximations used in early proof-of-concept testing.
It has been strictly retired from the production path.
The application now exclusively uses genuine USGS/NASA SRTM 1 Arc-Second Global (30m) GeoTIFFs
located at `backend/app/data/dem/processed/sikkim_dem_srtm_30m.tif`.

DO NOT RUN THIS SCRIPT FOR PRODUCTION TRAINING OR SERVING.
"""

import warnings

def build_dem():
    raise RuntimeError(
        "build_dem_grid.py is DEPRECATED and retired from the production path. "
        "Use genuine USGS/NASA SRTM GeoTIFF via `ml_pipeline/process_srtm_dem.py`."
    )

if __name__ == "__main__":
    warnings.warn(
        "build_dem_grid.py is retired. Use genuine SRTM GeoTIFF data.",
        DeprecationWarning
    )
    print("[DEPRECATED] Synthetic DEM generator is retired from production path.")
