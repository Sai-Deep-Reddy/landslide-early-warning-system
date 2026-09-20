"""
Landslide Early-Warning System (LEWS) - Startup Runner
SIH PS 26001
"""

import sys
import os
import uvicorn

# Ensure backend directory is on Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

if __name__ == "__main__":
    print("=" * 70)
    print("  LANDSLIDE EARLY-WARNING SYSTEM (LEWS) - SIH PS 26001")
    print("  Eastern Himalayas Pilot: Sikkim Region")
    print("=" * 70)
    print("\n  Starting FastAPI Application & GIS Command Center...")
    print("  Access Web Dashboard at:  http://127.0.0.1:8000")
    print("  Access Swagger API at:   http://127.0.0.1:8000/docs")
    print("=" * 70 + "\n")
    
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
