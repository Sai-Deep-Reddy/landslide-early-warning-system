"""
Vercel Serverless Function Entrypoint for Landslide Early Warning System (LEWS)
SIH PS 26001
"""
import sys
import os

# Set up path so backend/app can be imported as 'app'
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.main import app
