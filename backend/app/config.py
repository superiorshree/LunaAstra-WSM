"""
config.py — LunaAstra Backend Configuration

All environment variables, file paths, and global constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── Base Paths ───────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent          # backend/
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Ensure data directories exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

# ─── GeoTIFF Paths ────────────────────────────────────────────────────────────
GEOTIFF_PATHS = {
    "ice":          RAW_DATA_DIR / "ice.tif",
    "illumination": RAW_DATA_DIR / "illumination.tif",
    "radiation":    RAW_DATA_DIR / "radiation.tif",
    "slope":        RAW_DATA_DIR / "slope.tif",
    "comm":         RAW_DATA_DIR / "comm.tif",
}

# ─── Scoring Configuration ────────────────────────────────────────────────────
# Which direction is "better" for each factor
# True  = higher raw value → higher normalized score (e.g., ice, illumination)
# False = lower raw value  → higher normalized score (e.g., slope, radiation)
FACTOR_HIGHER_IS_BETTER = {
    "ice":          True,
    "illumination": True,
    "radiation":    False,   # lower radiation = safer
    "slope":        False,   # flatter terrain = better
    "comm":         True,
}

FACTOR_DISPLAY_NAMES = {
    "ice":          "Water Ice Availability",
    "illumination": "Solar Illumination",
    "radiation":    "Radiation Safety",
    "slope":        "Terrain Suitability",
    "comm":         "Earth Comm Visibility",
}

FACTOR_UNITS = {
    "ice":          "wt% H₂O",
    "illumination": "% illuminated",
    "radiation":    "mSv/day",
    "slope":        "degrees",
    "comm":         "% visibility",
}

# Default weights (equal weighting, must sum to 1.0)
DEFAULT_WEIGHTS = {
    "ice":          0.2,
    "illumination": 0.2,
    "radiation":    0.2,
    "slope":        0.2,
    "comm":         0.2,
}

# Default hard constraint: max slope in degrees
DEFAULT_MAX_SLOPE_DEG = 15.0

# Top N sites to return per scoring request
DEFAULT_TOP_N = 5

# ─── XAI Risk Thresholds ──────────────────────────────────────────────────────
RISK_THRESHOLDS = {
    "LOW":    0.70,   # normalized score >= 0.70 → LOW RISK
    "MEDIUM": 0.40,   # normalized score >= 0.40 → MEDIUM RISK
    # below 0.40 → HIGH RISK
}

# Ice confidence weights (proxy signals)
ICE_CONFIDENCE_WEIGHTS = {
    "ice_score":  0.6,   # primary signal: LEND neutron flux proxy
    "temp_score": 0.4,   # secondary: Diviner temperature (colder = more likely)
}

# ─── External APIs ────────────────────────────────────────────────────────────
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
CLAUDE_MODEL   = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")

NASA_API_KEY   = os.getenv("NASA_API_KEY", "DEMO_KEY")
DONKI_BASE_URL = "https://api.nasa.gov/DONKI"

# Space weather polling interval (seconds)
DONKI_POLL_INTERVAL_SECONDS = int(os.getenv("DONKI_POLL_INTERVAL", 300))  # 5 min

# ─── Space Weather Alert Thresholds ───────────────────────────────────────────
SPACE_WEATHER_RADIATION_PENALTY = {
    "NORMAL":   0.00,   # no penalty
    "ELEVATED": 0.15,   # subtract 0.15 from normalized radiation score
    "HIGH":     0.35,   # subtract 0.35 from normalized radiation score
}

# ─── Mock Data Configuration (Phase 1) ───────────────────────────────────────
# Used when real GeoTIFFs are not yet available
USE_MOCK_DATA = os.getenv("USE_MOCK_DATA", "true").lower() == "true"
MOCK_GRID_ROWS = int(os.getenv("MOCK_GRID_ROWS", 100))
MOCK_GRID_COLS = int(os.getenv("MOCK_GRID_COLS", 100))

# Mock geographic bounds (South Polar Region, degrees)
MOCK_LAT_MIN = -90.0
MOCK_LAT_MAX = -60.0
MOCK_LON_MIN = -180.0
MOCK_LON_MAX =  180.0

# ─── Database ─────────────────────────────────────────────────────────────────
SQLITE_DB_PATH = PROCESSED_DATA_DIR / "lunastra.db"

# ─── CORS ─────────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "app://.",             # Electron renderer process origin
]
