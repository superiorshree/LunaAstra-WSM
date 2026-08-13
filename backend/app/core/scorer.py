"""
scorer.py — Core Deterministic Scoring Engine

Implements the Multi-Criteria Decision Analysis (MCDA) weighted sum model:

  score(pixel) = Σ (weight_i × normalized_score_i)  for i in {factors}

Steps:
  1. Receive normalized layers + user weights
  2. Apply space-weather radiation penalty (if active)
  3. Compute weighted sum across all pixels simultaneously (NumPy vectorized)
  4. Apply hard constraints (mask out pixels where slope > max_slope)
  5. Extract top-N highest-scoring valid pixels
  6. Return full score grid + top sites with coordinate metadata

Architecture note:
  This module contains ZERO AI/ML logic. It is fully deterministic
  and auditable. Every score can be reproduced by hand from the inputs.
"""

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.config import (
    MOCK_LAT_MIN, MOCK_LAT_MAX, MOCK_LON_MIN, MOCK_LON_MAX,
    SPACE_WEATHER_RADIATION_PENALTY,
    DEFAULT_MAX_SLOPE_DEG,
    DEFAULT_TOP_N,
)

logger = logging.getLogger(__name__)


# ─── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class WeightConfig:
    """User-provided priority weights for each factor."""
    ice:          float = 0.2
    illumination: float = 0.2
    radiation:    float = 0.2
    slope:        float = 0.2
    comm:         float = 0.2

    def as_dict(self) -> Dict[str, float]:
        return {
            "ice":          self.ice,
            "illumination": self.illumination,
            "radiation":    self.radiation,
            "slope":        self.slope,
            "comm":         self.comm,
        }

    def validate(self) -> None:
        """Ensure weights are non-negative and sum to ~1.0."""
        weights = self.as_dict()
        if any(w < 0 for w in weights.values()):
            raise ValueError(f"All weights must be non-negative. Got: {weights}")
        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(
                f"Weights must sum to 1.0 (got {total:.4f}). "
                f"Normalize your weights before calling scorer."
            )

    def normalize(self) -> "WeightConfig":
        """Return a new WeightConfig with weights normalized to sum 1.0."""
        weights = self.as_dict()
        total = sum(weights.values())
        if total == 0:
            raise ValueError("Cannot normalize weights: all weights are zero.")
        normalized = {k: v / total for k, v in weights.items()}
        return WeightConfig(**normalized)


@dataclass
class ScoredSite:
    """A single candidate habitat site with full scoring metadata."""
    rank: int
    site_id: str                           # e.g., "SITE_001"
    lat: float                             # latitude in degrees
    lon: float                             # longitude in degrees
    row: int                               # pixel row index
    col: int                               # pixel column index
    total_score: float                     # 0.0–1.0 weighted sum

    # Raw values from original raster layers (before normalization)
    raw_values: Dict[str, float] = field(default_factory=dict)

    # Normalized scores [0.0–1.0] per factor
    normalized_scores: Dict[str, float] = field(default_factory=dict)

    # Contribution breakdown: weight × normalized_score per factor
    # This is the explainability layer — shows exactly how much each
    # factor contributed to the total score.
    contributions: Dict[str, float] = field(default_factory=dict)


@dataclass
class ScoreResult:
    """Full result from a single /score request."""
    # Flattened score grid for heatmap rendering (row-major, NaN = masked)
    score_grid: List[List[Optional[float]]]
    grid_rows: int
    grid_cols: int

    # Geographic bounds for overlay alignment
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float

    # Top N candidate sites
    top_sites: List[ScoredSite]

    # Applied configuration (echoed back for transparency)
    weights_applied: Dict[str, float]
    max_slope_constraint: float
    space_weather_alert: str
    radiation_penalty_applied: float

    # Summary stats
    valid_pixel_count: int
    masked_pixel_count: int


# ─── Core Scoring Engine ──────────────────────────────────────────────────────

def compute_scores(
    normalized_layers: Dict[str, np.ndarray],
    raw_layers: Dict[str, np.ndarray],
    weights: WeightConfig,
    max_slope_deg: float = DEFAULT_MAX_SLOPE_DEG,
    top_n: int = DEFAULT_TOP_N,
    space_weather_alert: str = "NORMAL",
) -> ScoreResult:
    """
    Run the full deterministic scoring pipeline.

    Args:
        normalized_layers:  Dict of {factor: ndarray [0,1]} from normalizer.py
        raw_layers:         Dict of {factor: ndarray raw} for reporting
        weights:            User-provided weight configuration
        max_slope_deg:      Hard constraint: exclude pixels where slope > this
        top_n:              Number of top sites to return
        space_weather_alert: "NORMAL" | "ELEVATED" | "HIGH"

    Returns:
        ScoreResult with heatmap grid + top N sites + metadata
    """
    weights = weights.normalize()
    weights.validate()

    weight_dict = weights.as_dict()
    grid_shape = next(iter(normalized_layers.values())).shape
    rows, cols = grid_shape

    logger.info(
        f"Scoring {rows}×{cols} grid | "
        f"weights={weight_dict} | "
        f"max_slope={max_slope_deg}° | "
        f"space_weather={space_weather_alert}"
    )

    # ── Step 1: Apply space-weather radiation penalty ──────────────────────
    penalty = SPACE_WEATHER_RADIATION_PENALTY.get(space_weather_alert, 0.0)
    layers = dict(normalized_layers)   # shallow copy to avoid mutating original

    if penalty > 0:
        penalized_rad = np.clip(layers["radiation"] - penalty, 0.0, 1.0)
        penalized_rad[np.isnan(layers["radiation"])] = np.nan
        layers["radiation"] = penalized_rad
        logger.info(f"Applied radiation penalty: -{penalty:.2f} (alert={space_weather_alert})")

    # ── Step 2: Weighted sum across all pixels simultaneously ──────────────
    score_grid = np.zeros(grid_shape, dtype=np.float32)
    nan_mask   = np.zeros(grid_shape, dtype=bool)

    for factor, w in weight_dict.items():
        layer = layers[factor]
        nan_mask |= np.isnan(layer)         # accumulate NaN positions
        score_grid += w * np.nan_to_num(layer, nan=0.0)

    # ── Step 3: Hard constraint — mask pixels where slope > max_slope_deg ──
    raw_slope = raw_layers.get("slope")
    if raw_slope is not None:
        slope_violated = raw_slope > max_slope_deg
        nan_mask |= slope_violated
        masked_count = int(np.sum(slope_violated & ~np.isnan(raw_slope)))
        logger.info(f"Hard constraint: masked {masked_count} pixels with slope > {max_slope_deg}°")
    else:
        masked_count = 0

    # Apply combined NaN mask
    score_grid[nan_mask] = np.nan

    valid_count = int(np.sum(~nan_mask))
    logger.info(f"Valid pixels for ranking: {valid_count} / {rows * cols}")

    # ── Step 4: Extract top-N highest-scoring valid pixels ─────────────────
    # Use argpartition for efficiency on large grids
    flat_scores = score_grid.flatten()
    valid_indices = np.where(~np.isnan(flat_scores))[0]

    if valid_indices.size == 0:
        logger.warning("No valid pixels after masking. Returning empty site list.")
        top_sites = []
    else:
        actual_n = min(top_n, valid_indices.size)
        # Partial sort: find indices of top-N without sorting everything
        top_partition = np.argpartition(
            flat_scores[valid_indices], -actual_n
        )[-actual_n:]
        top_flat_indices = valid_indices[top_partition]
        # Sort these top-N by score descending
        top_flat_indices = top_flat_indices[
            np.argsort(flat_scores[top_flat_indices])[::-1]
        ]

        top_sites = _build_top_sites(
            flat_indices=top_flat_indices,
            score_grid=score_grid,
            normalized_layers=layers,
            raw_layers=raw_layers,
            weight_dict=weight_dict,
            grid_shape=grid_shape,
        )

    # ── Step 5: Build score grid for heatmap (NaN → None for JSON) ─────────
    score_list = [
        [None if np.isnan(v) else round(float(v), 4) for v in row]
        for row in score_grid
    ]

    return ScoreResult(
        score_grid=score_list,
        grid_rows=rows,
        grid_cols=cols,
        lat_min=MOCK_LAT_MIN,
        lat_max=MOCK_LAT_MAX,
        lon_min=MOCK_LON_MIN,
        lon_max=MOCK_LON_MAX,
        top_sites=top_sites,
        weights_applied=weight_dict,
        max_slope_constraint=max_slope_deg,
        space_weather_alert=space_weather_alert,
        radiation_penalty_applied=penalty,
        valid_pixel_count=valid_count,
        masked_pixel_count=int(np.sum(nan_mask)),
    )


def _build_top_sites(
    flat_indices: np.ndarray,
    score_grid: np.ndarray,
    normalized_layers: Dict[str, np.ndarray],
    raw_layers: Dict[str, np.ndarray],
    weight_dict: Dict[str, float],
    grid_shape: Tuple[int, int],
) -> List[ScoredSite]:
    """
    Build ScoredSite objects for the top-N pixels.

    For each site, computes:
      - Geographic coordinates from pixel position
      - Raw values from original raster layers
      - Normalized scores per factor
      - Contribution breakdown (weight × normalized_score)
        ← This is the explainability data sent to the frontend
    """
    rows, cols = grid_shape
    sites = []

    for rank, flat_idx in enumerate(flat_indices, start=1):
        row = int(flat_idx // cols)
        col = int(flat_idx % cols)

        # Convert pixel position → geographic coordinates
        lat = MOCK_LAT_MIN + (row / rows) * (MOCK_LAT_MAX - MOCK_LAT_MIN)
        lon = MOCK_LON_MIN + (col / cols) * (MOCK_LON_MAX - MOCK_LON_MIN)

        total_score = float(score_grid[row, col])

        # Per-factor normalized scores and contributions
        norm_scores = {}
        contributions = {}
        raw_vals = {}

        for factor, w in weight_dict.items():
            norm_val = float(normalized_layers[factor][row, col])
            norm_scores[factor] = round(norm_val, 4)
            contributions[factor] = round(w * norm_val, 4)   # ← XAI data

            raw_layer = raw_layers.get(factor)
            if raw_layer is not None:
                raw_vals[factor] = round(float(raw_layer[row, col]), 4)

        site = ScoredSite(
            rank=rank,
            site_id=f"SITE_{rank:03d}",
            lat=round(lat, 4),
            lon=round(lon, 4),
            row=row,
            col=col,
            total_score=round(total_score, 4),
            raw_values=raw_vals,
            normalized_scores=norm_scores,
            contributions=contributions,
        )
        sites.append(site)

    return sites
