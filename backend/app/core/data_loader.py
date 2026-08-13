"""
data_loader.py — GeoTIFF / Mock Data Loader

Responsible for loading all 5 environmental raster layers into memory.
In Phase 1: generates mock NumPy arrays simulating aligned GeoTIFF data.
In Phase 2+: reads real GeoTIFF files via rasterio with Dask-backed chunking.

Architecture note:
  All data is loaded ONCE at backend startup into a global DataStore.
  Scoring requests read from this in-memory store — no per-request I/O.
"""

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from app.config import (
    USE_MOCK_DATA,
    MOCK_GRID_ROWS,
    MOCK_GRID_COLS,
    MOCK_LAT_MIN,
    MOCK_LAT_MAX,
    MOCK_LON_MIN,
    MOCK_LON_MAX,
    GEOTIFF_PATHS,
    FACTOR_HIGHER_IS_BETTER,
)

logger = logging.getLogger(__name__)


# ─── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class RasterLayer:
    """A single environmental raster layer with metadata."""
    name: str
    data: np.ndarray          # 2D array [rows, cols], float32, raw values
    nodata_value: Optional[float] = None
    lat_min: float = MOCK_LAT_MIN
    lat_max: float = MOCK_LAT_MAX
    lon_min: float = MOCK_LON_MIN
    lon_max: float = MOCK_LON_MAX
    source: str = "mock"      # "mock" | "geotiff"
    shape: Tuple[int, int] = field(init=False)

    def __post_init__(self):
        self.shape = self.data.shape


@dataclass
class DataStore:
    """
    Central in-memory store for all 5 raster layers.
    Loaded once at startup; shared across all scoring requests.
    """
    layers: Dict[str, RasterLayer] = field(default_factory=dict)
    is_loaded: bool = False
    grid_shape: Optional[Tuple[int, int]] = None

    def get_array(self, factor: str) -> np.ndarray:
        """Return raw numpy array for a factor."""
        return self.layers[factor].data

    def all_arrays(self) -> Dict[str, np.ndarray]:
        """Return dict of {factor_name: ndarray} for all layers."""
        return {name: layer.data for name, layer in self.layers.items()}


# Global singleton — loaded once at FastAPI startup
_data_store: Optional[DataStore] = None


def get_data_store() -> DataStore:
    """Return the global DataStore. Raises if not yet loaded."""
    if _data_store is None or not _data_store.is_loaded:
        raise RuntimeError(
            "DataStore not initialized. Call load_all_layers() at app startup."
        )
    return _data_store


# ─── Mock Data Generator ──────────────────────────────────────────────────────

def _generate_mock_layers(rows: int, cols: int) -> Dict[str, RasterLayer]:
    """
    Generate realistic-looking mock raster data for all 5 factors.

    Uses seeded random + spatial smoothing to simulate real geospatial
    patterns (e.g., clustered ice deposits, pole-biased illumination).
    This is intentionally more structured than pure random noise so that
    scoring produces meaningfully differentiated top sites.
    """
    rng = np.random.default_rng(seed=42)  # deterministic mock data

    def smooth_field(base: np.ndarray, sigma: float = 5.0) -> np.ndarray:
        """Apply simple Gaussian-like spatial smoothing via uniform filter."""
        from scipy.ndimage import uniform_filter
        return uniform_filter(base.astype(np.float32), size=int(sigma * 2 + 1))

    logger.info(f"Generating mock raster data: {rows}×{cols} grid")

    layers = {}

    # ── Ice: clustered deposits, biased toward south pole ──────────────────
    ice_base = rng.exponential(scale=0.3, size=(rows, cols)).astype(np.float32)
    # Add two synthetic "known ice deposit" hotspots
    ice_base[80:95, 40:60] += 2.0   # Cabeus analog
    ice_base[70:85, 75:90] += 1.5   # Haworth analog
    layers["ice"] = RasterLayer(
        name="ice",
        data=np.clip(smooth_field(ice_base, sigma=4), 0, None),
        source="mock",
    )

    # ── Illumination: high near poles, crater shadows low ──────────────────
    illum_base = rng.uniform(0, 100, size=(rows, cols)).astype(np.float32)
    # Pole rim peaks
    illum_base[85:, :] = np.clip(illum_base[85:, :] + 40, 0, 100)
    # Crater shadow regions (low illumination)
    illum_base[60:75, 20:45] = np.clip(illum_base[60:75, 20:45] - 50, 0, 100)
    layers["illumination"] = RasterLayer(
        name="illumination",
        data=smooth_field(illum_base, sigma=6),
        source="mock",
    )

    # ── Radiation: elevated in open terrain, lower in shielded craters ─────
    rad_base = rng.uniform(0.5, 10.0, size=(rows, cols)).astype(np.float32)
    # Shielded crater floors have lower radiation
    rad_base[60:75, 20:45] = np.clip(rad_base[60:75, 20:45] - 4, 0.1, None)
    layers["radiation"] = RasterLayer(
        name="radiation",
        data=smooth_field(rad_base, sigma=5),
        source="mock",
    )

    # ── Slope: mostly flat near poles, rough in crater walls ───────────────
    slope_base = np.abs(rng.normal(loc=3.0, scale=5.0, size=(rows, cols))).astype(np.float32)
    # Steep crater walls
    slope_base[60:65, 20:45] = rng.uniform(25, 40, size=(5, 25)).astype(np.float32)
    slope_base[73:76, 20:45] = rng.uniform(20, 35, size=(3, 25)).astype(np.float32)
    layers["slope"] = RasterLayer(
        name="slope",
        data=np.clip(smooth_field(slope_base, sigma=3), 0, None),
        source="mock",
    )

    # ── Comm: geometric visibility, highest near equator-facing terrain ─────
    comm_base = rng.uniform(20, 100, size=(rows, cols)).astype(np.float32)
    # Near-pole terrain has lower Earth visibility
    comm_base[90:, :] = np.clip(comm_base[90:, :] - 40, 0, 100)
    layers["comm"] = RasterLayer(
        name="comm",
        data=np.clip(smooth_field(comm_base, sigma=8), 0, 100),
        source="mock",
    )

    logger.info("Mock raster layers generated successfully.")
    return layers


# ─── GeoTIFF Loader (Phase 2+) ────────────────────────────────────────────────

def _load_geotiff_layers() -> Dict[str, RasterLayer]:
    """
    Load all 5 GeoTIFF files from backend/data/raw/ using rasterio.

    For large files, uses windowed reading to avoid OOM.
    TODO: Wire in Dask for fully lazy loading when datasets exceed RAM.
    """
    try:
        import rasterio
    except ImportError:
        raise ImportError("rasterio is required for GeoTIFF loading. pip install rasterio")

    layers = {}
    for factor, path in GEOTIFF_PATHS.items():
        if not path.exists():
            raise FileNotFoundError(
                f"GeoTIFF not found: {path}\n"
                f"Place your aligned GeoTIFFs in backend/data/raw/ "
                f"or set USE_MOCK_DATA=true in .env for mock mode."
            )

        logger.info(f"Loading GeoTIFF: {path}")
        with rasterio.open(path) as src:
            data = src.read(1).astype(np.float32)   # Band 1
            nodata = src.nodata
            bounds = src.bounds

            # Replace nodata with NaN
            if nodata is not None:
                data[data == nodata] = np.nan

            layers[factor] = RasterLayer(
                name=factor,
                data=data,
                nodata_value=nodata,
                lat_min=bounds.bottom,
                lat_max=bounds.top,
                lon_min=bounds.left,
                lon_max=bounds.right,
                source="geotiff",
            )
            logger.info(
                f"  Loaded {factor}: shape={data.shape}, "
                f"bounds=({bounds.left:.1f},{bounds.bottom:.1f}) → "
                f"({bounds.right:.1f},{bounds.top:.1f})"
            )

    return layers


# ─── Public API ───────────────────────────────────────────────────────────────

def load_all_layers() -> DataStore:
    """
    Load all raster layers and initialize the global DataStore.
    Called once at FastAPI application startup (lifespan event).

    Returns:
        DataStore: fully populated, ready for scoring requests.
    """
    global _data_store

    if USE_MOCK_DATA:
        logger.info("USE_MOCK_DATA=true — loading synthetic raster data.")
        layers = _generate_mock_layers(MOCK_GRID_ROWS, MOCK_GRID_COLS)
    else:
        logger.info("USE_MOCK_DATA=false — loading real GeoTIFF data.")
        layers = _load_geotiff_layers()

    # Verify all layers have the same shape
    shapes = {name: layer.shape for name, layer in layers.items()}
    unique_shapes = set(shapes.values())
    if len(unique_shapes) > 1:
        raise ValueError(
            f"All raster layers must have identical shapes. "
            f"Found: {shapes}"
        )

    grid_shape = next(iter(unique_shapes))
    _data_store = DataStore(
        layers=layers,
        is_loaded=True,
        grid_shape=grid_shape,
    )

    logger.info(
        f"DataStore ready: {len(layers)} layers, "
        f"grid={grid_shape[0]}×{grid_shape[1]}, "
        f"source={'mock' if USE_MOCK_DATA else 'geotiff'}"
    )
    return _data_store
