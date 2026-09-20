"""
Landslide Events & Field Reporting Router: /api/landslides and /api/report
"""

import os
import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, Body, HTTPException
from pydantic import BaseModel, Field
from app.config import DATA_DIR
from app.services.alert_service import alert_service
from app.services.terrain_service import terrain_service

router = APIRouter(tags=["Landslide Events & Incident Reports"])


@router.get("/susceptibility")
def get_susceptibility_geojson() -> Dict[str, Any]:
    """
    Returns GSI NLSM Susceptibility zones as a standard GeoJSON FeatureCollection.
    Features contain multi-polygon coordinates, susceptibility class, slope ranges, and critical corridors.
    """
    return terrain_service.get_susceptibility_geojson()


class FieldReportRequest(BaseModel):
    lat: float = Field(..., example=27.305)
    lon: float = Field(..., example=88.612)
    location_name: Optional[str] = Field(None, example="Gyalshing Pelling Km 14")
    district: Optional[str] = Field(None, example="Gyalshing")
    officer_name: Optional[str] = Field("Field Patrol Officer", example="Sub-Divisional Officer")
    observation_type: Optional[str] = Field("Slope Movement", example="Tension Crack / Rockfall")
    notes: str = Field(..., example="Fresh ground crack observed across road shoulder")
    photo_url: Optional[str] = Field(None, example="https://images.unsplash.com/photo-1545486332-9e0999c535b2")
    severity: Optional[str] = Field("Moderate", example="High")


@router.get("/landslides")
def get_historical_landslides(
    bbox: Optional[str] = Query(None, description="Bounding box formatted as 'min_lon,min_lat,max_lon,max_lat'"),
    from_date: Optional[str] = Query(None, alias="from", description="Filter events after YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, alias="to", description="Filter events before YYYY-MM-DD"),
    district: Optional[str] = Query(None, description="Filter by district name (e.g. 'Gyalshing', 'Mangan', 'Gangtok')")
) -> List[Dict[str, Any]]:
    """
    Returns field-validated historical landslides from GSI Inventory.
    Supports spatial bounding box filtering, temporal windowing, and district slicing.
    """
    gsi_path = os.path.join(DATA_DIR, "gsi_landslides.json")
    if not os.path.exists(gsi_path):
        return []

    with open(gsi_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    if isinstance(raw_data, dict) and "records" in raw_data:
        events = raw_data["records"]
    elif isinstance(raw_data, list):
        events = raw_data
    else:
        events = []

    filtered = []

    # Parse Bounding Box if provided
    bbox_parsed = None
    if bbox:
        try:
            parts = [float(p.strip()) for p in bbox.split(",")]
            if len(parts) == 4:
                bbox_parsed = {
                    "min_lon": parts[0],
                    "min_lat": parts[1],
                    "max_lon": parts[2],
                    "max_lat": parts[3]
                }
        except Exception:
            pass

    for ev in events:
        # Spatial bbox check
        if bbox_parsed:
            if not (bbox_parsed["min_lon"] <= ev["lon"] <= bbox_parsed["max_lon"] and
                    bbox_parsed["min_lat"] <= ev["lat"] <= bbox_parsed["max_lat"]):
                continue

        # Date filtering
        ev_date = ev.get("event_date", "")
        if from_date and ev_date < from_date:
            continue
        if to_date and ev_date > to_date:
            continue

        # District filtering
        if district and district.lower() not in ev.get("district", "").lower():
            continue

        filtered.append(ev)

    return filtered


@router.post("/report")
def submit_field_report(report: FieldReportRequest) -> Dict[str, Any]:
    """
    Allows field officers, SDRF responders, and registered citizens to submit real-time ground observations.
    """
    saved = alert_service.add_field_report(
        lat=report.lat,
        lon=report.lon,
        location_name=report.location_name,
        district=report.district,
        officer_name=report.officer_name,
        observation_type=report.observation_type,
        notes=report.notes,
        photo_url=report.photo_url,
        severity=report.severity
    )
    return {
        "status": "received",
        "message": "Field incident report registered and transmitted to Sikkim Disaster Operations Center.",
        "report": saved
    }


@router.get("/reports")
def list_field_reports() -> List[Dict[str, Any]]:
    """Returns submitted ground observation reports."""
    return alert_service.get_field_reports()
