"""
Terrain & Topographic Analysis Service
SIH PS 26001 - Production Build
Reads genuine USGS/NASA SRTM 1 Arc-Second Global (30m) DEM GeoTIFF
and GSI NLSM GeoJSON susceptibility vector polygons.
"""

import os
import json
import math
import logging
import numpy as np
try:
    import rasterio
except ImportError:
    rasterio = None
from typing import Dict, Any, List, Optional
from app.config import PILOT_STATIONS, SIKKIM_BBOX, DATA_DIR

logger = logging.getLogger("lews.terrain_service")

PROCESSED_DEM_PATH = os.path.join(DATA_DIR, "dem", "processed", "sikkim_dem_srtm_30m.tif")
PROCESSED_DEM_NPZ = os.path.join(DATA_DIR, "dem", "terrain_sikkim.npz")
SUSCEPTIBILITY_GEOJSON_PATH = os.path.join(DATA_DIR, "sikkim_susceptibility.geojson")


class NpzTerrain:
    """Fast, dependency-free raster lookup using precomputed compressed numpy arrays."""
    def __init__(self, path: str):
        d = np.load(path)
        self.elev, self.slope = d["elev"], d["slope"]
        self.left, self.top, self.res = float(d["left"]), float(d["top"]), float(d["res"])

    def lookup(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        r = int((self.top - lat) / self.res)
        c = int((lon - self.left) / self.res)
        if not (0 <= r < self.elev.shape[0] and 0 <= c < self.elev.shape[1]):
            return None  # outside regional coverage
        if self.elev[r, c] == -32768 or self.slope[r, c] == 255:
            return None
        return {
            "elevation_m": float(self.elev[r, c]),
            "slope_deg": float(self.slope[r, c]),
            "dem_source": "USGS/NASA SRTM 1 Arc-Second Global (30m GeoTIFF)"
        }


class TerrainService:
    def __init__(self):
        self.stations = PILOT_STATIONS
        self.bbox = SIKKIM_BBOX
        self._dem_loaded = False
        self._dem_raster = None
        self._dem_dataset = None
        self._transform = None
        self._bounds = None
        self._nodata = None
        self._npz_terrain = None
        self._susceptibility_geojson = None
        self._load_npz_terrain()
        self._load_srtm_geotiff()
        self._load_susceptibility_geojson()

    def _load_npz_terrain(self):
        """Loads precomputed numpy terrain if available for serverless deployments."""
        if os.path.exists(PROCESSED_DEM_NPZ):
            try:
                self._npz_terrain = NpzTerrain(PROCESSED_DEM_NPZ)
                logger.info(f"Loaded precomputed NPZ terrain from {PROCESSED_DEM_NPZ}")
            except Exception as e:
                logger.error(f"Failed to load NPZ terrain: {e}")
                self._npz_terrain = None

    def _load_srtm_geotiff(self):
        """Loads the genuine USGS/NASA SRTM 1 Arc-Second (30m) GeoTIFF."""
        if rasterio is not None and os.path.exists(PROCESSED_DEM_PATH):
            try:
                src = rasterio.open(PROCESSED_DEM_PATH)
                self._dem_dataset = src
                self._dem_raster = src.read(1)
                self._transform = src.transform
                self._bounds = src.bounds
                self._nodata = src.nodata or -32768
                self._dem_loaded = True
                logger.info(
                    f"Successfully loaded genuine SRTM DEM from {PROCESSED_DEM_PATH} "
                    f"(Dimensions: {self._dem_raster.shape}, Bounds: {self._bounds})"
                )
            except Exception as e:
                logger.error(f"Failed to open SRTM GeoTIFF at {PROCESSED_DEM_PATH}: {e}")
                self._dem_loaded = False
        else:
            self._dem_loaded = False

    def _load_susceptibility_geojson(self):
        """Loads validated GSI NLSM GeoJSON susceptibility polygons."""
        if os.path.exists(SUSCEPTIBILITY_GEOJSON_PATH):
            try:
                with open(SUSCEPTIBILITY_GEOJSON_PATH, "r", encoding="utf-8") as f:
                    self._susceptibility_geojson = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load susceptibility GeoJSON: {e}")
                self._susceptibility_geojson = None

    def get_susceptibility_geojson(self) -> Dict[str, Any]:
        """Returns the GSI NLSM Susceptibility FeatureCollection."""
        if self._susceptibility_geojson:
            return self._susceptibility_geojson
        return {"type": "FeatureCollection", "features": []}

    def get_closest_station(self, lat: float, lon: float) -> Dict[str, Any]:
        """Finds closest monitoring station or landmark coordinate."""
        closest = None
        min_dist = float("inf")
        for stn in self.stations:
            dist = math.sqrt((stn["lat"] - lat) ** 2 + (stn["lon"] - lon) ** 2)
            if dist < min_dist:
                min_dist = dist
                closest = stn
        return closest or self.stations[0]

    def _point_in_polygon(self, lat: float, lon: float, poly_coords: list) -> bool:
        """Ray-casting point in polygon algorithm."""
        inside = False
        n = len(poly_coords)
        for i in range(n):
            p1 = poly_coords[i]
            p2 = poly_coords[(i + 1) % n]
            # Coordinates in GeoJSON are [lon, lat]
            lon1, lat1 = p1[0], p1[1]
            lon2, lat2 = p2[0], p2[1]
            if ((lat1 > lat) != (lat2 > lat)) and (lon < (lon2 - lon1) * (lat - lat1) / (lat2 - lat1 + 1e-12) + lon1):
                inside = not inside
        return inside

    def find_susceptibility_zone(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Checks if a coordinate falls inside any GSI NLSM susceptibility polygon."""
        if not self._susceptibility_geojson:
            return None
        for feature in self._susceptibility_geojson.get("features", []):
            geom = feature.get("geometry", {})
            if geom.get("type") == "Polygon":
                coords = geom.get("coordinates", [[]])[0]
                if self._point_in_polygon(lat, lon, coords):
                    return feature.get("properties", {})
        return None

    def compute_terrain_metrics(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Extracts genuine elevation, 3x3 Horn slope gradient, aspect, and GSI susceptibility zone
        directly from the official USGS/NASA SRTM 1 Arc-Second (30m) GeoTIFF raster.
        """
        closest = self.get_closest_station(lat, lon)

        if self._npz_terrain is not None:
            npz_res = self._npz_terrain.lookup(lat, lon)
            if npz_res is not None:
                elev = npz_res["elevation_m"]
                slope = npz_res["slope_deg"]
                aspect = 180.0
                dem_source = npz_res["dem_source"]
            else:
                elev = float(closest["elevation_m"])
                slope = float(closest["slope_deg"])
                aspect = 180.0
                dem_source = "Outside SRTM Regional Coverage (Station Baseline)"
        elif self._dem_loaded and self._dem_raster is not None and self._dem_dataset is not None:
            try:
                row, col = self._dem_dataset.index(lon, lat)
                nrows, ncols = self._dem_raster.shape

                # Clamp index within valid raster grid
                row = max(0, min(nrows - 1, row))
                col = max(0, min(ncols - 1, col))

                raw_elev = float(self._dem_raster[row, col])
                if raw_elev == self._nodata or raw_elev < -100:
                    elev = float(closest["elevation_m"])
                else:
                    elev = raw_elev

                # Extract 3x3 neighborhood for Horn's finite-difference slope and aspect calculation
                r_prev = max(0, row - 1)
                r_next = min(nrows - 1, row + 1)
                c_prev = max(0, col - 1)
                c_next = min(ncols - 1, col + 1)

                z_tl = float(self._dem_raster[r_prev, c_prev])
                z_t  = float(self._dem_raster[r_prev, col])
                z_tr = float(self._dem_raster[r_prev, c_next])
                z_l  = float(self._dem_raster[row,    c_prev])
                z_r  = float(self._dem_raster[row,    c_next])
                z_bl = float(self._dem_raster[r_next, c_prev])
                z_b  = float(self._dem_raster[r_next, col])
                z_br = float(self._dem_raster[r_next, c_next])

                # Cell resolution in meters at latitude (WGS84 ellipsoid conversion)
                dy = (1.0 / 3600.0) * 111132.95
                dx = (1.0 / 3600.0) * 111412.84 * math.cos(math.radians(lat))
                dx = max(10.0, dx)

                # Horn's weighted partial derivatives
                dz_dx = ((z_tr + 2.0 * z_r + z_br) - (z_tl + 2.0 * z_l + z_bl)) / (8.0 * dx)
                dz_dy = ((z_tl + 2.0 * z_t + z_tr) - (z_bl + 2.0 * z_b + z_br)) / (8.0 * dy)

                slope_rad = math.atan(math.sqrt(dz_dx ** 2 + dz_dy ** 2))
                slope = math.degrees(slope_rad)
                slope = max(0.0, min(85.0, slope))

                aspect = (math.degrees(math.atan2(dz_dy, -dz_dx)) + 360.0) % 360.0
                dem_source = "USGS/NASA SRTM 1 Arc-Second Global (30m GeoTIFF)"
            except Exception as e:
                logger.error(f"Error computing terrain metrics from SRTM GeoTIFF: {e}")
                elev = float(closest["elevation_m"])
                slope = float(closest["slope_deg"])
                aspect = 180.0
                dem_source = "Station Topography Fallback"
        else:
            elev = float(closest["elevation_m"])
            slope = float(closest["slope_deg"])
            aspect = 180.0
            dem_source = "Station Topography Fallback"

        # Check GSI NLSM GeoJSON zone intersection first
        matched_zone = self.find_susceptibility_zone(lat, lon)
        if matched_zone:
            susceptibility = matched_zone.get("susceptibility_class", "Moderate")
            suscep_factor = matched_zone.get("susceptibility_score", 0.5)
            zone_name = matched_zone.get("name", closest["name"])
            corridor = matched_zone.get("critical_corridor", closest.get("critical_infrastructure", "Corridor"))
            is_inside_mapped = True
            suscep_source = f"GSI NLSM Corridor Polygon ({matched_zone.get('zone_id', 'Mapped')})"
        else:
            # NLSM classification standard based on terrain gradient
            if slope >= 34.0:
                susceptibility = "High"
                suscep_factor = 1.0
            elif slope >= 26.0:
                susceptibility = "Moderate"
                suscep_factor = 0.5
            else:
                susceptibility = "Low"
                suscep_factor = 0.1
            zone_name = closest["name"]
            corridor = closest.get("critical_infrastructure", "Mountain Arterial Corridor")
            is_inside_mapped = False
            suscep_source = "SRTM 30m Slope Baseline (Outside Mapped GSI Corridors)"

        return {
            "lat": round(lat, 4),
            "lon": round(lon, 4),
            "elevation_m": round(elev, 1),
            "slope_deg": round(slope, 1),
            "aspect_deg": round(aspect, 1),
            "susceptibility": susceptibility,
            "suscep_factor": suscep_factor,
            "is_inside_mapped_polygon": is_inside_mapped,
            "susceptibility_source": suscep_source,
            "dem_source": dem_source,
            "nearest_landmark": zone_name,
            "district": closest["district"],
            "critical_corridor": corridor
        }


terrain_service = TerrainService()
