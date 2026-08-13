"""
normalizer.py — Per-Layer Min-Max Normalization

Converts raw raster values to a 0.0–1.0 scale where:
  1.0 = most suitable for habitat
  0.0 = least suitable

Direction is controlled by FACTOR_HIGHER_IS_BETTER in config:
  - ice, illumination, comm → higher raw = higher score (standard min-max)
  - radiation, slope        → lower raw = higher score (inverted min-max)

NaN pixels (nodata / masked) are preserved through normalization
and later used for hard constraint masking in scorer.py.
"""

import logging
import numpy as np
from typing import Dict

from app.config import FACTOR_HIGHER_IS_BETTER

logger = logging.getLogger(__name__)


def normalize_layer(
    data: np.ndarray,
    higher_is_better: bool,
    percentile_clip: float = 2.0,
) -> np.ndarray:
    """
    Normalize a single 2D raster layer to [0.0, 1.0].

    Args:
        data:              Raw 2D float32 array. May contain NaN.
        higher_is_better:  If True, max → 1.0. If False, min → 1.0 (inverted).
        percentile_clip:   Clip outliers at this percentile before scaling.
                           Prevents a single extreme pixel from compressing
                           the entire range. Default 2% is conservative.

    Returns:
        Normalized float32 array [0.0, 1.0], NaN preserved.
    """
    valid = data[~np.isnan(data)]

    if valid.size == 0:
        logger.warning("Layer has no valid (non-NaN) pixels. Returning zeros.")
        return np.zeros_like(data)

    # Clip to percentile range to handle outliers
    vmin = np.percentile(valid, percentile_clip)
    vmax = np.percentile(valid, 100.0 - percentile_clip)

    if vmax == vmin:
        logger.warning(f"Layer has zero range after clipping (all values = {vmin}). Returning 0.5.")
        result = np.full_like(data, 0.5, dtype=np.float32)
        result[np.isnan(data)] = np.nan
        return result

    # Clip data to [vmin, vmax]
    clipped = np.clip(data, vmin, vmax)

    # Min-max normalize to [0, 1]
    normalized = (clipped - vmin) / (vmax - vmin)

    # Invert if lower raw value = better outcome
    if not higher_is_better:
        normalized = 1.0 - normalized

    # Restore NaN mask
    normalized[np.isnan(data)] = np.nan

    return normalized.astype(np.float32)


def normalize_all_layers(
    raw_layers: Dict[str, np.ndarray],
    percentile_clip: float = 2.0,
) -> Dict[str, np.ndarray]:
    """
    Normalize all 5 raster layers in one pass.

    Args:
        raw_layers:       Dict of {factor_name: raw_ndarray}.
        percentile_clip:  Outlier clipping percentile (default 2%).

    Returns:
        Dict of {factor_name: normalized_ndarray [0.0, 1.0]}.
    """
    normalized = {}
    for factor, data in raw_layers.items():
        higher_is_better = FACTOR_HIGHER_IS_BETTER.get(factor, True)
        normalized[factor] = normalize_layer(
            data=data,
            higher_is_better=higher_is_better,
            percentile_clip=percentile_clip,
        )
        valid_count = np.sum(~np.isnan(normalized[factor]))
        logger.debug(
            f"Normalized '{factor}': "
            f"higher_is_better={higher_is_better}, "
            f"valid_pixels={valid_count}"
        )

    return normalized
