"""
space_weather.py — GET /space-weather Router

Returns the current solar activity alert level from the DONKI poller.
"""

import logging
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Optional

from app.services.donki_service import get_full_alert_state

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/space-weather", tags=["Space Weather"])


class SpaceWeatherResponse(BaseModel):
    level:          str               # "NORMAL" | "ELEVATED" | "HIGH"
    last_polled:    Optional[str]     # ISO timestamp
    active_events:  List[Dict]
    source:         str
    radiation_penalty_active: float   # How much is being subtracted from radiation scores
    alert_color:    str               # hex for frontend banner
    alert_message:  str               # Human-readable status


ALERT_COLORS = {
    "NORMAL":   "#22c55e",
    "ELEVATED": "#f59e0b",
    "HIGH":     "#ef4444",
}

ALERT_MESSAGES = {
    "NORMAL":   "Space weather nominal. No significant solar activity detected.",
    "ELEVATED": "Elevated solar activity detected (M-class flare). Moderate radiation increase applied to scoring.",
    "HIGH":     "⚠️ High solar activity detected (X-class flare or SEP event). Significant radiation penalty active — habitat sites near poles preferred.",
}

ALERT_PENALTIES = {
    "NORMAL":   0.00,
    "ELEVATED": 0.15,
    "HIGH":     0.35,
}


@router.get(
    "",
    response_model=SpaceWeatherResponse,
    summary="Current solar activity alert level",
    description="Returns the most recent NASA DONKI poll result. Used by the frontend to display the live space weather banner and by the scoring engine for radiation penalties.",
)
async def space_weather() -> SpaceWeatherResponse:
    state = get_full_alert_state()
    level = state.get("level", "NORMAL")

    return SpaceWeatherResponse(
        level=level,
        last_polled=state.get("last_polled"),
        active_events=state.get("active_events", []),
        source=state.get("source", "unknown"),
        radiation_penalty_active=ALERT_PENALTIES.get(level, 0.0),
        alert_color=ALERT_COLORS.get(level, "#22c55e"),
        alert_message=ALERT_MESSAGES.get(level, "Status unknown."),
    )
