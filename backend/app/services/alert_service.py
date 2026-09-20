"""
Alert Management & Field Reporting Service
Maintains real-time active warnings and handles crowdsourced field officer reports.
"""

import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.config import PILOT_STATIONS
from app.services.risk_engine import risk_engine


class AlertService:
    def __init__(self):
        self._field_reports: List[Dict[str, Any]] = [
            {
                "report_id": 101,
                "timestamp": "2026-08-28T11:45:00Z",
                "lat": 27.2917,
                "lon": 88.2394,
                "location_name": "Gyalshing-Pelling Km 12",
                "district": "Gyalshing",
                "officer_name": "Insp. T. Bhutia (Sikkim Police / SDRF)",
                "observation_type": "Tension Crack Observed",
                "notes": "Spotted 4-inch wide longitudinal ground crack across road shoulder after continuous downpour.",
                "photo_url": "https://images.unsplash.com/photo-1588681664899-f142ff2dc9b1?w=800",
                "status": "Verified by Geologist",
                "severity": "High"
            },
            {
                "report_id": 102,
                "timestamp": "2026-08-28T14:10:00Z",
                "lat": 27.5042,
                "lon": 88.5284,
                "location_name": "Mangan North Axis Km 8",
                "district": "Mangan",
                "officer_name": "Sub-Divisional Magistrate Mangan",
                "observation_type": "Minor Mud Slump",
                "notes": "Small loose scree and water seepage at toe of cutting slope. BRO machinery on standby.",
                "photo_url": "https://images.unsplash.com/photo-1518458028785-8fbcd101ebb9?w=800",
                "status": "Under Monitoring",
                "severity": "Moderate"
            }
        ]
        self._next_report_id = 103

    def get_active_alerts(self, rain_boost_pct: float = 0.0) -> List[Dict[str, Any]]:
        """
        Generates dynamic alerts by running hazard checks on all pilot monitoring points.
        """
        alerts = []
        now_iso = datetime.now(timezone.utc).isoformat()

        alert_counter = 1
        for stn in PILOT_STATIONS:
            risk = risk_engine.calculate_risk(
                lat=stn["lat"],
                lon=stn["lon"],
                rain_boost_pct=rain_boost_pct
            )

            if risk["risk_level"] in ["HIGH", "CRITICAL"]:
                alerts.append({
                    "alert_id": f"ALT-{datetime.now().strftime('%Y%m%d')}-{alert_counter:03d}",
                    "station_id": stn["id"],
                    "location_name": stn["name"],
                    "district": stn["district"],
                    "lat": stn["lat"],
                    "lon": stn["lon"],
                    "datetime": now_iso,
                    "level": risk["risk_level"],
                    "risk_score": risk["risk_score"],
                    "rain_24h_mm": risk["factors"]["rain_24h"],
                    "slope_deg": risk["factors"]["slope_deg"],
                    "soil_moisture": risk["factors"]["soil_0_10cm"],
                    "critical_infrastructure": stn["critical_infrastructure"],
                    "description": f"{risk['risk_level']} hazard detected: {risk['factors']['rain_24h']}mm rain onto {risk['factors']['slope_deg']}° slope in {stn['district']}.",
                    "action_required": risk["emergency_advisories"][0]
                })
                alert_counter += 1
            elif risk["risk_level"] == "MODERATE":
                alerts.append({
                    "alert_id": f"ALT-{datetime.now().strftime('%Y%m%d')}-{alert_counter:03d}",
                    "station_id": stn["id"],
                    "location_name": stn["name"],
                    "district": stn["district"],
                    "lat": stn["lat"],
                    "lon": stn["lon"],
                    "datetime": now_iso,
                    "level": "MODERATE",
                    "risk_score": risk["risk_score"],
                    "rain_24h_mm": risk["factors"]["rain_24h"],
                    "slope_deg": risk["factors"]["slope_deg"],
                    "soil_moisture": risk["factors"]["soil_0_10cm"],
                    "critical_infrastructure": stn["critical_infrastructure"],
                    "description": f"Moderate Advisory: Sustained rainfall at {stn['name']}.",
                    "action_required": risk["emergency_advisories"][0]
                })
                alert_counter += 1

        return alerts

    def add_field_report(
        self,
        lat: float,
        lon: float,
        location_name: Optional[str],
        district: Optional[str],
        officer_name: str,
        observation_type: str,
        notes: str,
        photo_url: Optional[str] = None,
        severity: str = "Moderate"
    ) -> Dict[str, Any]:
        """Saves a crowdsourced or field officer report."""
        report = {
            "report_id": self._next_report_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "lat": lat,
            "lon": lon,
            "location_name": location_name or f"Coordinates ({round(lat, 4)}, {round(lon, 4)})",
            "district": district or "Sikkim",
            "officer_name": officer_name or "Field Patrol Unit",
            "observation_type": observation_type or "Slope Movement",
            "notes": notes,
            "photo_url": photo_url or "https://images.unsplash.com/photo-1545486332-9e0999c535b2?w=800",
            "status": "Submitted to Control Room",
            "severity": severity
        }
        self._next_report_id += 1
        self._field_reports.insert(0, report)
        return report

    def get_field_reports(self) -> List[Dict[str, Any]]:
        return self._field_reports


alert_service = AlertService()
