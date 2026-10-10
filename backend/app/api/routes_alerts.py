from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Query, Response
from pydantic import BaseModel
from app.services.alert_service import alert_service
from app.services.cap_alert import build_alert, approve, validate

router = APIRouter(tags=["Disaster Warning & Alerts"])


class CapApproveRequest(BaseModel):
    xml: str
    officer_name: str = "District Disaster Management Officer"
    agency: str = "Sikkim SDMA"


@router.get("/alerts")
def get_active_hazard_alerts(
    rain_boost_pct: float = Query(0.0, description="Rainfall booster for simulated alert escalation")
) -> List[Dict[str, Any]]:
    """
    Returns list of active high-priority landslide warnings, recommended evacuation directives, and affected highway corridors.
    """
    return alert_service.get_active_alerts(rain_boost_pct=rain_boost_pct)


@router.get("/alerts/cap", response_class=Response)
def get_cap_alert(
    level: str = Query("HIGH", description="Risk Level (LOW, MODERATE, HIGH, CRITICAL)"),
    lat: float = Query(27.5042, description="Latitude"),
    lon: float = Query(88.5284, description="Longitude"),
    area_desc: str = Query("Mangan District, North Sikkim", description="Geographic area description"),
    risk: float = Query(0.72, description="Calculated compound risk score"),
    road: str = Query("NH-10 / Mangan-Chungthang Highway", description="Threatened transport corridor"),
    status: str = Query("Exercise", description="CAP status: Draft, Actual, Exercise, Test")
):
    """
    Exports OASIS Common Alerting Protocol (CAP v1.2) XML payload compliant with India's SACHET emergency alerting architecture.
    """
    xml_str = build_alert(
        level=level.upper(),
        lat=lat,
        lon=lon,
        area_desc=area_desc,
        risk=risk,
        road=road,
        status=status,
        sender="terrasentinel.sikkim.sdma@gov.in"
    )
    return Response(content=xml_str, media_type="application/xml")


@router.post("/alerts/cap/approve")
def approve_cap_alert(req: CapApproveRequest) -> Dict[str, Any]:
    """
    Officer approval workflow: signs a Draft CAP alert into an Actual public directive.
    """
    approved_xml = approve(req.xml, officer_name=req.officer_name, agency=req.agency)
    is_valid, reason = validate(approved_xml)
    return {
        "status": "APPROVED",
        "valid": is_valid,
        "validation_note": reason,
        "approved_xml": approved_xml
    }
