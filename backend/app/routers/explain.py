"""
explain.py — /explain Router

Endpoints for full XAI site reports, scenario comparisons, and exportable reports.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import numpy as np
from fastapi import APIRouter, HTTPException

from app.models.explain_models import (
    ExplainSiteRequest, ExplainSiteResponse,
    ExplainCompareRequest, ExplainCompareResponse,
    SiteReportResponse,
)
from app.core.data_loader import get_data_store
from app.core.normalizer import normalize_all_layers
from app.core.scorer import compute_scores, WeightConfig
from app.core.explainer import build_site_xai_report, scenario_diff
from app.core.narrator import (
    generate_site_briefing,
    generate_scenario_narration,
    generate_anomaly_flags,
)
from app.services.donki_service import get_current_alert_level
from app.config import DEFAULT_MAX_SLOPE_DEG, DEFAULT_TOP_N

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/explain", tags=["Explainability"])

# In-memory cache of last scoring result (populated by /score calls)
# In production, this would be stored per-session in a lightweight store
_last_score_cache: dict = {}


def _cache_score_result(result, normalized_layers, raw_layers):
    """Store last scoring result for /explain endpoints to reference."""
    _last_score_cache["result"] = result
    _last_score_cache["normalized"] = normalized_layers
    _last_score_cache["raw"] = raw_layers


# ─── POST /explain/site ───────────────────────────────────────────────────────

@router.post(
    "/site",
    response_model=ExplainSiteResponse,
    summary="Full XAI report for a single candidate site",
    description="Returns risk profile, ice confidence, contribution breakdown, and Claude-generated mission briefing for a site from the last /score result.",
)
async def explain_site(request: ExplainSiteRequest) -> ExplainSiteResponse:
    try:
        store = get_data_store()
        raw_layers = store.all_arrays()
        normalized = normalize_all_layers(raw_layers)
        space_weather = get_current_alert_level()

        # Run scoring to find the requested site
        weights = WeightConfig()
        result = compute_scores(
            normalized_layers=normalized,
            raw_layers=raw_layers,
            weights=weights,
            space_weather_alert=space_weather,
        )

        site = next(
            (s for s in result.top_sites if s.site_id == request.site_id), None
        )
        if site is None:
            raise HTTPException(
                status_code=404,
                detail=f"Site '{request.site_id}' not found in current top sites. Run /score first."
            )

        xai = build_site_xai_report(site, space_weather_alert=space_weather)

        briefing = None
        anomaly = None

        if request.include_briefing:
            briefing = generate_site_briefing(
                site=site,
                risk_profile=xai.get("risk_profile", {}),
                ice_conf=xai.get("ice_confidence", {}),
                space_weather_alert=space_weather,
            )

        if request.include_anomalies:
            anomaly = generate_anomaly_flags(site)

        return ExplainSiteResponse(
            site_id=site.site_id,
            rank=site.rank,
            lat=site.lat,
            lon=site.lon,
            total_score=site.total_score,
            raw_values=site.raw_values,
            contributions=xai.get("contributions", []),
            risk_profile=xai.get("risk_profile", {}),
            ice_confidence=xai.get("ice_confidence", {}),
            mission_briefing=briefing,
            anomaly_flags=anomaly,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in /explain/site: {e}")
        raise HTTPException(status_code=500, detail="Explanation generation failed.")


# ─── POST /explain/compare ────────────────────────────────────────────────────

@router.post(
    "/compare",
    response_model=ExplainCompareResponse,
    summary="What-if scenario comparison with Claude narration",
    description="Runs two scoring configurations and compares results. Claude narrates what changed operationally.",
)
async def explain_compare(request: ExplainCompareRequest) -> ExplainCompareResponse:
    try:
        store = get_data_store()
        raw_layers = store.all_arrays()
        normalized = normalize_all_layers(raw_layers)
        space_weather = get_current_alert_level()

        # Run scenario A
        weights_a = WeightConfig(**request.scenario_a.weights)
        result_a = compute_scores(
            normalized_layers=normalized,
            raw_layers=raw_layers,
            weights=weights_a,
            max_slope_deg=request.scenario_a.max_slope_deg,
            top_n=request.top_n,
            space_weather_alert=space_weather,
        )

        # Run scenario B
        weights_b = WeightConfig(**request.scenario_b.weights)
        result_b = compute_scores(
            normalized_layers=normalized,
            raw_layers=raw_layers,
            weights=weights_b,
            max_slope_deg=request.scenario_b.max_slope_deg,
            top_n=request.top_n,
            space_weather_alert=space_weather,
        )

        # Compute diff
        diff = scenario_diff(
            result_a=result_a,
            result_b=result_b,
            label_a=request.scenario_a.label,
            label_b=request.scenario_b.label,
        )

        # Claude narration
        narration = generate_scenario_narration(diff)

        return ExplainCompareResponse(
            scenario_a_label=diff.scenario_a_label,
            scenario_b_label=diff.scenario_b_label,
            weight_changes=diff.weight_changes,
            top_site_a=diff.top_site_a,
            top_site_b=diff.top_site_b,
            score_delta=diff.score_delta,
            dominant_factor_change=diff.dominant_factor_change,
            narration=narration,
        )

    except Exception as e:
        logger.exception(f"Error in /explain/compare: {e}")
        raise HTTPException(status_code=500, detail="Comparison failed.")


# ─── GET /explain/report/{site_id} ───────────────────────────────────────────

@router.get(
    "/report/{site_id}",
    response_model=SiteReportResponse,
    summary="Exportable full site report",
    description="Returns a complete site report suitable for export to JSON or PDF generation.",
)
async def site_report(site_id: str) -> SiteReportResponse:
    try:
        store = get_data_store()
        raw_layers = store.all_arrays()
        normalized = normalize_all_layers(raw_layers)
        space_weather = get_current_alert_level()

        weights = WeightConfig()
        result = compute_scores(
            normalized_layers=normalized,
            raw_layers=raw_layers,
            weights=weights,
            space_weather_alert=space_weather,
        )

        site = next(
            (s for s in result.top_sites if s.site_id == site_id), None
        )
        if site is None:
            raise HTTPException(status_code=404, detail=f"Site '{site_id}' not found.")

        xai = build_site_xai_report(site, space_weather_alert=space_weather)

        briefing = generate_site_briefing(
            site=site,
            risk_profile=xai.get("risk_profile", {}),
            ice_conf=xai.get("ice_confidence", {}),
            space_weather_alert=space_weather,
        )
        anomaly = generate_anomaly_flags(site)

        # Calculate score percentile among all valid pixels
        flat_scores = [
            v for row in result.score_grid
            for v in row if v is not None
        ]
        score_percentile = 0.0
        if flat_scores:
            score_percentile = round(
                100.0 * sum(1 for s in flat_scores if s <= site.total_score) / len(flat_scores), 1
            )

        return SiteReportResponse(
            site_id=site.site_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            rank=site.rank,
            lat=site.lat,
            lon=site.lon,
            total_score=site.total_score,
            score_percentile=score_percentile,
            raw_values=site.raw_values,
            contributions=xai.get("contributions", []),
            risk_profile=xai.get("risk_profile", {}),
            ice_confidence=xai.get("ice_confidence", {}),
            mission_briefing=briefing,
            anomaly_flags=anomaly,
            weights_used=result.weights_applied,
            space_weather_at_time=space_weather,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in /explain/report/{site_id}: {e}")
        raise HTTPException(status_code=500, detail="Report generation failed.")
