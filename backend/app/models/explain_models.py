"""
explain_models.py — Pydantic schemas for /explain endpoints
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


# ─── /explain/site ────────────────────────────────────────────────────────────

class ExplainSiteRequest(BaseModel):
    """Request body for POST /explain/site."""
    site_id:     str = Field(..., description="Site ID from /score response (e.g., SITE_001)")
    include_briefing:  bool = Field(default=True, description="Generate Claude mission briefing")
    include_anomalies: bool = Field(default=True, description="Generate Claude anomaly flags")

    model_config = {"json_schema_extra": {
        "example": {
            "site_id": "SITE_001",
            "include_briefing": True,
            "include_anomalies": True
        }
    }}


class ExplainSiteResponse(BaseModel):
    """Full XAI report for a single site."""
    site_id:        str
    rank:           int
    lat:            float
    lon:            float
    total_score:    float
    raw_values:     Dict[str, float]
    contributions:  List[Dict]
    risk_profile:   Dict[str, Dict]
    ice_confidence: Dict

    # Claude-generated (may be None if API unavailable)
    mission_briefing: Optional[str] = None
    anomaly_flags:    Optional[str] = None


# ─── /explain/compare ────────────────────────────────────────────────────────

class ScenarioConfig(BaseModel):
    """A single scoring configuration for comparison."""
    label:         str
    weights:       Dict[str, float]
    max_slope_deg: float = 15.0


class ExplainCompareRequest(BaseModel):
    """Request body for POST /explain/compare."""
    scenario_a: ScenarioConfig
    scenario_b: ScenarioConfig
    top_n:      int = Field(default=5, ge=1, le=20)

    model_config = {"json_schema_extra": {
        "example": {
            "scenario_a": {
                "label": "Prioritize Water",
                "weights": {"ice": 0.5, "illumination": 0.1, "radiation": 0.2, "slope": 0.1, "comm": 0.1}
            },
            "scenario_b": {
                "label": "Prioritize Sunlight",
                "weights": {"ice": 0.1, "illumination": 0.5, "radiation": 0.2, "slope": 0.1, "comm": 0.1}
            }
        }
    }}


class ExplainCompareResponse(BaseModel):
    """Response from POST /explain/compare."""
    scenario_a_label: str
    scenario_b_label: str
    weight_changes:   Dict[str, Dict]
    top_site_a:       Optional[Dict]
    top_site_b:       Optional[Dict]
    score_delta:      float
    dominant_factor_change: Optional[str]

    # Claude narration of what changed and why
    narration: Optional[str] = None


# ─── /explain/report/{site_id} ────────────────────────────────────────────────

class SiteReportResponse(BaseModel):
    """Exportable site report (JSON/PDF-ready)."""
    site_id:          str
    generated_at:     str
    rank:             int
    lat:              float
    lon:              float
    total_score:      float
    score_percentile: float       # What % of all sites scored lower
    raw_values:       Dict[str, float]
    contributions:    List[Dict]
    risk_profile:     Dict[str, Dict]
    ice_confidence:   Dict
    mission_briefing: Optional[str]
    anomaly_flags:    Optional[str]
    weights_used:     Dict[str, float]
    space_weather_at_time: str
