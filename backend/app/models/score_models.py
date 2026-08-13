"""
score_models.py — Pydantic schemas for /score endpoint

Defines the request and response shapes for the core scoring API.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator


# ─── Request ──────────────────────────────────────────────────────────────────

class WeightsInput(BaseModel):
    """User-provided priority weights. Will be auto-normalized to sum 1.0."""
    ice:          float = Field(default=0.2, ge=0.0, le=1.0)
    illumination: float = Field(default=0.2, ge=0.0, le=1.0)
    radiation:    float = Field(default=0.2, ge=0.0, le=1.0)
    slope:        float = Field(default=0.2, ge=0.0, le=1.0)
    comm:         float = Field(default=0.2, ge=0.0, le=1.0)

    @field_validator("*", mode="before")
    @classmethod
    def must_be_non_negative(cls, v):
        if isinstance(v, (int, float)) and v < 0:
            raise ValueError("All weights must be >= 0")
        return v

    model_config = {"json_schema_extra": {
        "example": {
            "ice": 0.35,
            "illumination": 0.25,
            "radiation": 0.20,
            "slope": 0.15,
            "comm": 0.05
        }
    }}


class ScoreRequest(BaseModel):
    """Full request body for POST /score."""
    weights:       WeightsInput = Field(default_factory=WeightsInput)
    max_slope_deg: float = Field(
        default=15.0,
        ge=0.0,
        le=90.0,
        description="Hard constraint: exclude pixels where slope exceeds this value (degrees)"
    )
    top_n:         int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of top-ranked sites to return"
    )
    include_xai:   bool = Field(
        default=True,
        description="Include risk profiles, ice confidence, and contribution breakdowns"
    )

    model_config = {"json_schema_extra": {
        "example": {
            "weights": {"ice": 0.35, "illumination": 0.25, "radiation": 0.20, "slope": 0.15, "comm": 0.05},
            "max_slope_deg": 15.0,
            "top_n": 5,
            "include_xai": True
        }
    }}


# ─── Response ─────────────────────────────────────────────────────────────────

class ContributionItem(BaseModel):
    """Single factor contribution entry for chart rendering."""
    factor:           str
    display_name:     str
    contribution:     float
    percentage:       float
    weight:           float
    normalized_score: float
    raw_value:        Optional[float]
    unit:             str


class RiskFactorItem(BaseModel):
    """Risk assessment for a single factor."""
    display_name:     str
    risk_level:       str         # "LOW" | "MEDIUM" | "HIGH"
    color:            str         # hex
    emoji:            str
    normalized_score: float
    raw_value:        float
    unit:             str
    note:             Optional[str] = None


class IceConfidenceItem(BaseModel):
    """Ice detection confidence output."""
    confidence_pct: float
    label:          str
    color:          str
    signals:        Dict[str, float]
    weights_used:   Dict[str, float]
    note:           str


class SiteResponse(BaseModel):
    """A single ranked candidate site in the response."""
    rank:              int
    site_id:           str
    lat:               float
    lon:               float
    row:               int
    col:               int
    total_score:       float
    raw_values:        Dict[str, float]
    normalized_scores: Dict[str, float]

    # XAI fields (populated when include_xai=True)
    contributions:   Optional[List[ContributionItem]] = None
    risk_profile:    Optional[Dict[str, RiskFactorItem]] = None
    ice_confidence:  Optional[IceConfidenceItem] = None


class ScoreResponse(BaseModel):
    """Full response from POST /score."""
    # Heatmap data for 2D/3D overlay
    score_grid:    List[List[Optional[float]]]
    grid_rows:     int
    grid_cols:     int

    # Geographic bounds for overlay alignment
    lat_min:       float
    lat_max:       float
    lon_min:       float
    lon_max:       float

    # Top-N ranked sites
    top_sites:     List[SiteResponse]

    # Applied configuration (echoed for transparency)
    weights_applied:            Dict[str, float]
    max_slope_constraint:       float
    space_weather_alert:        str
    radiation_penalty_applied:  float

    # Summary stats
    valid_pixel_count:   int
    masked_pixel_count:  int
    total_pixels:        int
