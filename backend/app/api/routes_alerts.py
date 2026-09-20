"""
Alerts API Router: /api/alerts
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Query
from app.services.alert_service import alert_service

router = APIRouter(tags=["Disaster Warning & Alerts"])


@router.get("/alerts")
def get_active_hazard_alerts(
    rain_boost_pct: float = Query(0.0, description="Rainfall booster for simulated alert escalation")
) -> List[Dict[str, Any]]:
    """
    Returns list of active high-priority landslide warnings, recommended evacuation directives, and affected highway corridors.
    """
    return alert_service.get_active_alerts(rain_boost_pct=rain_boost_pct)
