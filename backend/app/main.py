"""
main.py — LunaAstra FastAPI Application Entry Point

Startup sequence:
  1. Load all raster layers into memory (mock or GeoTIFF)
  2. Start DONKI space weather polling scheduler
  3. Mount all API routers
  4. Serve on localhost:8000
"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import ALLOWED_ORIGINS, USE_MOCK_DATA
from app.core.data_loader import load_all_layers
from app.routers import score, explain, space_weather, assistant

# ─── Logging Setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ─── Lifespan (startup / shutdown) ───────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.
    Runs startup logic before serving requests, cleanup on shutdown.
    """
    # ── Startup ───────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("  LunaAstra Backend — Starting Up")
    logger.info(f"  Mode: {'MOCK DATA' if USE_MOCK_DATA else 'REAL GeoTIFF'}")
    logger.info("=" * 60)

    # Load raster data into memory
    store = load_all_layers()
    logger.info(f"DataStore loaded: {list(store.layers.keys())}, shape={store.grid_shape}")

    # Start space weather polling
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from app.services.donki_service import setup_donki_scheduler, poll_donki

        scheduler = AsyncIOScheduler()
        setup_donki_scheduler(scheduler)
        scheduler.start()
        logger.info("APScheduler started: DONKI polling active")
        app.state.scheduler = scheduler
    except ImportError:
        logger.warning("apscheduler not installed — space weather polling disabled. pip install apscheduler")
        app.state.scheduler = None

    logger.info("LunaAstra backend ready. Listening on http://localhost:8000")
    logger.info("API docs: http://localhost:8000/docs")

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────
    logger.info("LunaAstra Backend — Shutting Down")
    if hasattr(app.state, "scheduler") and app.state.scheduler:
        app.state.scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")


# ─── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="LunaAstra — Lunar Habitat AI Decision Support System",
    description="""
## Overview
AI-powered decision support system for identifying optimal lunar habitat locations.

Fuses 5 NASA/ISRO satellite datasets into a scored, ranked, explainable tool:
- **Water Ice Availability** (LEND)
- **Solar Illumination** (Diviner/LRO)
- **Radiation Safety** (CRaTER/LRO)
- **Terrain Suitability** (LOLA DEM)
- **Earth Communication Visibility** (geometric model)

## Hackathon: SW02 — Lunar Habitat Site Selection using AI

## Architecture
- Core scoring: deterministic NumPy weighted sum (fully auditable)
- XAI layer: risk profiles, ice confidence, contribution breakdowns
- AI narration: Claude API for natural language I/O only
- Space weather: NASA DONKI live radiation alerts
    """,
    version="1.0.0",
    contact={"name": "LunaAstra Team", "url": "https://github.com/superiorshree/LunaAstra-WSM"},
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(score.router)
app.include_router(explain.router)
app.include_router(space_weather.router)
app.include_router(assistant.router)


# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    """Quick health check — confirms backend is alive."""
    from app.core.data_loader import get_data_store
    try:
        store = get_data_store()
        return {
            "status":      "healthy",
            "data_loaded": store.is_loaded,
            "grid_shape":  store.grid_shape,
            "layers":      list(store.layers.keys()),
            "mock_mode":   USE_MOCK_DATA,
        }
    except Exception as e:
        return {"status": "degraded", "error": str(e)}


@app.get("/", tags=["System"])
async def root():
    return {
        "name":    "LunaAstra Backend",
        "version": "1.0.0",
        "docs":    "/docs",
        "health":  "/health",
    }
