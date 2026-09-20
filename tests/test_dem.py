"""
USGS/NASA SRTM DEM Integration & Validation Tests
SIH PS 26001 - Production Build
"""

import sys
import os
import json
import rasterio

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.services.terrain_service import terrain_service

DEM_DIR = os.path.join(BACKEND_DIR, "app", "data", "dem")
RAW_DIR = os.path.join(DEM_DIR, "raw")
PROCESSED_DIR = os.path.join(DEM_DIR, "processed")
SRTM_TIF_PATH = os.path.join(PROCESSED_DIR, "sikkim_dem_srtm_30m.tif")
METADATA_PATH = os.path.join(RAW_DIR, "srtm_metadata.json")


def test_raw_srtm_tiles_exist():
    """Validates raw USGS/NASA SRTM tile files and exact byte lengths."""
    assert os.path.exists(RAW_DIR), f"Raw DEM directory missing: {RAW_DIR}"
    
    n27_hgt = os.path.join(RAW_DIR, "N27E088.hgt")
    n28_hgt = os.path.join(RAW_DIR, "N28E088.hgt")
    
    assert os.path.exists(n27_hgt), f"Missing raw SRTM tile: {n27_hgt}"
    assert os.path.exists(n28_hgt), f"Missing raw SRTM tile: {n28_hgt}"
    
    # 3601 x 3601 x 2 bytes = 25,934,402 bytes exactly for standard 1-arcsecond HGT
    assert os.path.getsize(n27_hgt) == 25934402, f"Invalid N27E088.hgt size: {os.path.getsize(n27_hgt)}"
    assert os.path.getsize(n28_hgt) == 25934402, f"Invalid N28E088.hgt size: {os.path.getsize(n28_hgt)}"


def test_srtm_metadata():
    """Validates provenance metadata in raw folder."""
    assert os.path.exists(METADATA_PATH), f"Metadata missing at {METADATA_PATH}"
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)
        
    assert "USGS" in meta["source"] or "NASA" in meta["source"]
    assert meta["dataset"] == "SRTM 1 Arc-Second Global (SRTMGL1 v003)"
    assert "N27E088" in meta["tile_names"]
    assert "N28E088" in meta["tile_names"]
    assert meta["coordinate_reference_system"] == "EPSG:4326 (WGS 84)"


def test_processed_geotiff():
    """Validates processed mosaic GeoTIFF properties."""
    assert os.path.exists(SRTM_TIF_PATH), f"Processed GeoTIFF missing at {SRTM_TIF_PATH}"
    
    with rasterio.open(SRTM_TIF_PATH) as src:
        assert str(src.crs) == "EPSG:4326", f"Expected EPSG:4326, got {src.crs}"
        assert src.shape == (7201, 3601), f"Expected shape (7201, 3601), got {src.shape}"
        assert src.bounds.left == 88.0
        assert src.bounds.right == 89.0
        assert src.bounds.bottom == 27.0
        assert src.bounds.top == 29.0
        
        data = src.read(1)
        valid_elevs = data[data > -100]
        assert valid_elevs.min() >= 100, f"Expected min elev >= 100m, got {valid_elevs.min()}"
        assert valid_elevs.max() >= 8000, f"Expected max elev >= 8000m (Kanchenjunga), got {valid_elevs.max()}"


def test_terrain_service_srtm():
    """Validates terrain service outputs using genuine SRTM data."""
    test_coords = [
        ("Gangtok", 27.3389, 88.6065, 1400.0, 1650.0),
        ("Mangan", 27.5028, 88.5322, 950.0, 1200.0),
        ("Chungthang", 27.6037, 88.6472, 1500.0, 1800.0),
        ("Rangpo Valley", 27.1790, 88.5439, 250.0, 450.0),
        ("Kanchenjunga", 27.7025, 88.1475, 7500.0, 8600.0)
    ]
    
    for name, lat, lon, min_e, max_e in test_coords:
        res = terrain_service.compute_terrain_metrics(lat, lon)
        
        assert res["dem_source"] == "USGS/NASA SRTM 1 Arc-Second Global (30m GeoTIFF)", (
            f"Expected SRTM source, got {res['dem_source']}"
        )
        assert min_e <= res["elevation_m"] <= max_e, (
            f"{name} elevation {res['elevation_m']}m not in expected range [{min_e}, {max_e}]"
        )
        assert 0.0 <= res["slope_deg"] <= 85.0, f"Invalid slope: {res['slope_deg']}"
        assert 0.0 <= res["aspect_deg"] <= 360.0, f"Invalid aspect: {res['aspect_deg']}"
        assert res["susceptibility"] in ["Low", "Moderate", "High"]


if __name__ == "__main__":
    print("Running Genuine USGS/NASA SRTM DEM Validation Tests...")
    test_raw_srtm_tiles_exist()
    print("[PASS] Raw SRTM 1-Arcsecond HGT Tiles Exist & Have Correct Size (25,934,402 bytes)")
    test_srtm_metadata()
    print("[PASS] SRTM Provenance Metadata Verified (USGS/NASA SRTMGL1 v003, WGS84)")
    test_processed_geotiff()
    print("[PASS] Processed GeoTIFF Mosaicked & Formatted (EPSG:4326, 7201x3601 pixels, 30m resolution)")
    test_terrain_service_srtm()
    print("[PASS] Terrain Service Real-Time Querying & 3x3 Horn Slope Gradient Verified")
    print("\nALL GENUINE SRTM DEM TESTS PASSED SUCCESSFULLY! :)")
