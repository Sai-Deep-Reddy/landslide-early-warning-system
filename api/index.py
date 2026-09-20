"""
Vercel Serverless Function Entrypoint for Landslide Early Warning System (LEWS)
SIH PS 26001
"""
import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.main import app
from fastapi import Request

@app.middleware("http")
async def fix_vercel_path(request: Request, call_next):
    subpath = request.query_params.get("path")
    if subpath:
        clean_subpath = subpath.strip("/")
        if clean_subpath in ["docs", "openapi.json", "redoc"]:
            request.scope["path"] = f"/{clean_subpath}"
        else:
            request.scope["path"] = f"/api/{clean_subpath}"
    response = await call_next(request)
    return response

@app.get("/api/index")
@app.get("/api/index.py")
def vercel_root():
    return {
        "status": "online",
        "service": "Landslide Early-Warning System (LEWS) on Vercel",
        "pilot_region": "Sikkim & Eastern Himalayas",
        "docs_url": "/docs"
    }
