"""
FastAPI Application Entrypoint
Landslide Early-Warning System (LEWS) - SIH PS 26001
"""

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import ALLOWED_ORIGINS, LOG_LEVEL
from app.api.routes_risk import router as risk_router
from app.api.routes_events import router as events_router
from app.api.routes_alerts import router as alerts_router
from app.api.routes_simulate import router as simulate_router

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("lews.main")

app = FastAPI(
    title="Landslide Early-Warning System (LEWS) API",
    description="Operational Early-Warning & Decision Support System for Rainfall-Triggered Landslides (Sikkim / NER Pilot) - SIH PS 26001",
    version="2.4.0"
)

# Restrict CORS to configured origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Register API Routers under /api
app.include_router(risk_router, prefix="/api")
app.include_router(events_router, prefix="/api")
app.include_router(alerts_router, prefix="/api")
app.include_router(simulate_router, prefix="/api")

# Mount Static assets directory
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def serve_dashboard():
    """Serves the interactive GIS command dashboard."""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {
        "status": "online",
        "service": "Landslide Early-Warning System (LEWS)",
        "docs_url": "/docs"
    }


@app.get("/api/health", tags=["System Health"])
def health_check():
    return {
        "status": "healthy",
        "system": "Landslide Early-Warning System (LEWS)",
        "pilot_region": "Sikkim & Eastern Himalayas (Eastern Himalayan Corridor)",
        "models_active": ["Random Forest Classifier (Primary ML)", "Calibrated Heuristic Physics Rule Engine"],
        "weather_data_source": "IMD Protocol & Open-Meteo Multi-depth Telemetry",
        "spatial_dem": "Copernicus DEM GLO-30 (30m Resampled Raster)"
    }
