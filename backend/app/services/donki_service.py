"""
donki_service.py — NASA DONKI Space Weather Poller

Polls the NASA DONKI API on a schedule for solar flare / radiation storm events.
The current alert level is stored in-process and applied as a radiation penalty
by the scoring engine.

APScheduler runs the poll every N minutes (configured in config.py).
The alert level is available synchronously via get_current_alert_level().
"""

import logging
import httpx
from datetime import datetime, timedelta, timezone
from typing import Dict

from app.config import NASA_API_KEY, DONKI_BASE_URL, DONKI_POLL_INTERVAL_SECONDS

logger = logging.getLogger(__name__)


# ─── In-process alert state ───────────────────────────────────────────────────

_alert_state: Dict = {
    "level":        "NORMAL",    # "NORMAL" | "ELEVATED" | "HIGH"
    "last_polled":  None,
    "active_events": [],
    "source":       "initializing",
}


def get_current_alert_level() -> str:
    """Return the current space weather alert level (thread-safe read)."""
    return _alert_state["level"]


def get_full_alert_state() -> Dict:
    """Return the full alert state dict for the /space-weather endpoint."""
    return dict(_alert_state)


# ─── DONKI API Polling ────────────────────────────────────────────────────────

async def poll_donki() -> None:
    """
    Async poll of NASA DONKI API for recent solar flare and radiation events.

    Checks two endpoints:
      - /FLR (Solar Flares): flare class determines severity
      - /SEP (Solar Energetic Particles): direct radiation storm indicator

    Alert mapping:
      X-class flare OR SEP event   → HIGH
      M-class flare                → ELEVATED
      No significant events        → NORMAL
    """
    global _alert_state

    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = now.strftime("%Y-%m-%d")

    params = {
        "startDate": start_date,
        "endDate":   end_date,
        "api_key":   NASA_API_KEY,
    }

    active_events = []
    level = "NORMAL"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Check solar flares
            flr_resp = await client.get(f"{DONKI_BASE_URL}/FLR", params=params)
            if flr_resp.status_code == 200:
                flares = flr_resp.json() or []
                for flare in flares:
                    flare_class = flare.get("classType", "")
                    if flare_class.startswith("X"):
                        level = "HIGH"
                        active_events.append({
                            "type":       "Solar Flare",
                            "class":      flare_class,
                            "begin_time": flare.get("beginTime", ""),
                            "severity":   "HIGH",
                        })
                    elif flare_class.startswith("M") and level != "HIGH":
                        level = "ELEVATED"
                        active_events.append({
                            "type":       "Solar Flare",
                            "class":      flare_class,
                            "begin_time": flare.get("beginTime", ""),
                            "severity":   "ELEVATED",
                        })

            # Check solar energetic particle events (radiation storms)
            sep_resp = await client.get(f"{DONKI_BASE_URL}/SEP", params=params)
            if sep_resp.status_code == 200:
                seps = sep_resp.json() or []
                if seps:
                    level = "HIGH"
                    for sep in seps:
                        active_events.append({
                            "type":       "SEP Radiation Storm",
                            "begin_time": sep.get("eventTime", ""),
                            "severity":   "HIGH",
                        })

        _alert_state = {
            "level":         level,
            "last_polled":   now.isoformat(),
            "active_events": active_events,
            "source":        "NASA DONKI",
        }
        logger.info(f"DONKI poll complete: level={level}, events={len(active_events)}")

    except httpx.TimeoutException:
        logger.warning("DONKI API timeout — retaining previous alert level")
        _alert_state["source"] = "cached (timeout)"
    except Exception as e:
        logger.error(f"DONKI poll error: {e} — retaining previous alert level")
        _alert_state["source"] = f"cached (error: {type(e).__name__})"


# ─── Scheduler Setup ──────────────────────────────────────────────────────────

def setup_donki_scheduler(scheduler) -> None:
    """
    Register the DONKI polling job with APScheduler.
    Called from main.py lifespan startup.

    Args:
        scheduler: An AsyncIOScheduler instance from apscheduler.
    """
    scheduler.add_job(
        poll_donki,
        trigger="interval",
        seconds=DONKI_POLL_INTERVAL_SECONDS,
        id="donki_poll",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),  # run immediately on startup
    )
    logger.info(
        f"DONKI scheduler registered: "
        f"polling every {DONKI_POLL_INTERVAL_SECONDS}s"
    )
