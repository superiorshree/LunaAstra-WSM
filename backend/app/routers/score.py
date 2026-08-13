"""
score.py — POST /score Router

The primary scoring endpoint. Accepts weights + constraints,
runs the full deterministic pipeline, returns heatmap + ranked sites.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from app.models.score_models import ScoreRequest, ScoreResponse, SiteResponse
from app.core.data_loader import get_data_store
from app.core.normalizer import normalize_all_layers
from app.core.scorer import compute_scores, WeightConfig
from app.core.explainer import build_site_xai_report
from app.services.donki_service import get_current_alert_level

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/score", tags=["Scoring"])


@router.post(
    "",
    response_model=ScoreResponse,
    summary="Score all lunar pixels and return ranked sites",
    description="""
Runs the full MCDA scoring pipeline:
1. Loads cached normalized raster layers
2. Applies space-weather radiation penalty (if active)
3. Computes weighted sum across all pixels (NumPy vectorized)
4. Masks pixels violating hard constraints (slope > max_slope_deg)
5. Extracts top-N highest scoring valid pixels
6. Returns full heatmap grid + ranked sites with XAI breakdowns

The core math is fully deterministic and auditable.
    """,
)
async def score(request: ScoreRequest) -> ScoreResponse:
    """
    POST /score

    Body:
        weights:       Priority weights per factor (auto-normalized to sum 1.0)
        max_slope_deg: Hard constraint threshold (degrees)
        top_n:         Number of top sites to return (default 5)
        include_xai:   Include risk profiles, ice confidence, contributions
    """
    try:
        # ── 1. Load cached raster data ─────────────────────────────────────
        store = get_data_store()
        raw_layers = store.all_arrays()

        # ── 2. Normalize layers ────────────────────────────────────────────
        normalized = normalize_all_layers(raw_layers)

        # ── 3. Get current space weather alert ────────────────────────────
        space_weather = get_current_alert_level()

        # ── 4. Build weight config ─────────────────────────────────────────
        weights = WeightConfig(
            ice=request.weights.ice,
            illumination=request.weights.illumination,
            radiation=request.weights.radiation,
            slope=request.weights.slope,
            comm=request.weights.comm,
        )

        # ── 5. Run scoring engine ──────────────────────────────────────────
        result = compute_scores(
            normalized_layers=normalized,
            raw_layers=raw_layers,
            weights=weights,
            max_slope_deg=request.max_slope_deg,
            top_n=request.top_n,
            space_weather_alert=space_weather,
        )

        # ── 6. Build site responses with optional XAI ──────────────────────
        site_responses = []
        for site in result.top_sites:
            site_dict = {
                "rank":              site.rank,
                "site_id":           site.site_id,
                "lat":               site.lat,
                "lon":               site.lon,
                "row":               site.row,
                "col":               site.col,
                "total_score":       site.total_score,
                "raw_values":        site.raw_values,
                "normalized_scores": site.normalized_scores,
            }

            if request.include_xai:
                xai = build_site_xai_report(
                    site=site,
                    space_weather_alert=space_weather,
                )
                site_dict["contributions"] = xai.get("contributions")
                site_dict["risk_profile"]  = xai.get("risk_profile")
                site_dict["ice_confidence"] = xai.get("ice_confidence")

            site_responses.append(SiteResponse(**site_dict))

        logger.info(
            f"POST /score → {len(site_responses)} sites, "
            f"valid_pixels={result.valid_pixel_count}"
        )

        return ScoreResponse(
            score_grid=result.score_grid,
            grid_rows=result.grid_rows,
            grid_cols=result.grid_cols,
            lat_min=result.lat_min,
            lat_max=result.lat_max,
            lon_min=result.lon_min,
            lon_max=result.lon_max,
            top_sites=site_responses,
            weights_applied=result.weights_applied,
            max_slope_constraint=result.max_slope_constraint,
            space_weather_alert=result.space_weather_alert,
            radiation_penalty_applied=result.radiation_penalty_applied,
            valid_pixel_count=result.valid_pixel_count,
            masked_pixel_count=result.masked_pixel_count,
            total_pixels=result.grid_rows * result.grid_cols,
        )

    except RuntimeError as e:
        logger.error(f"DataStore not ready: {e}")
        raise HTTPException(status_code=503, detail="Data store not initialized. Retry in a moment.")
    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error in /score: {e}")
        raise HTTPException(status_code=500, detail="Internal scoring error.")
