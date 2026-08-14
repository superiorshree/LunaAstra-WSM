"""
generate_sample_geotiffs.py — Synthetic Lunar South Pole GeoTIFF Generator

Generates 5 co-registered, aligned GeoTIFF files representing real lunar South Pole
datasets (80°S to 90°S) matching LOLA, Diviner, CRaTER, LEND formats:
  - ice.tif           (LEND/Chandrayaan proxy, wt% H2O)
  - illumination.tif  (Diviner/LRO, % solar illumination)
  - radiation.tif     (CRaTER/LRO, mSv/day dose rate)
  - slope.tif         (LOLA DEM, slope in degrees)
  - comm.tif          (Geometric line-of-sight to Earth, %)

Usage:
  python backend/scripts/generate_sample_geotiffs.py
"""

import sys
import os
from pathlib import Path
import numpy as np
from scipy.ndimage import uniform_filter

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
DATA_RAW_DIR = BACKEND_DIR / "data" / "raw"
DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)

ROWS = 200
COLS = 200

# Geographic bounds: Lunar South Pole (-90° to -80° Lat, -180° to 180° Lon)
LAT_MIN = -90.0
LAT_MAX = -80.0
LON_MIN = -180.0
LON_MAX = 180.0


def smooth_field(base: np.ndarray, sigma: float = 4.0) -> np.ndarray:
    return uniform_filter(base.astype(np.float32), size=int(sigma * 2 + 1))


def generate_layers():
    rng = np.random.default_rng(seed=1337)

    # 1. Ice deposits (concentrated in permanently shadowed craters near pole)
    ice_base = rng.exponential(scale=0.25, size=(ROWS, COLS)).astype(np.float32)
    ice_base[160:190, 80:120] += 3.2
    ice_base[140:170, 150:180] += 2.8
    ice_base[130:160, 20:50] += 2.4
    ice = np.clip(smooth_field(ice_base, sigma=3), 0.0, 5.0)

    # 2. Illumination (% annual sunlight - peaks on crater rims, 0 in PSRs)
    illum_base = rng.uniform(5, 65, size=(ROWS, COLS)).astype(np.float32)
    illum_base[160:190, 75:85] = 92.0
    illum_base[160:190, 115:125] = 88.0
    illum_base[165:185, 85:115] = 0.0
    illum = np.clip(smooth_field(illum_base, sigma=4), 0.0, 100.0)

    # 3. Radiation (mSv/day - lower in shielded depressions, higher on open plains)
    rad_base = rng.uniform(1.2, 3.8, size=(ROWS, COLS)).astype(np.float32)
    rad_base[160:190, 80:120] -= 1.0
    radiation = np.clip(smooth_field(rad_base, sigma=5), 0.2, 5.0)

    # 4. Slope (degrees from LOLA DEM - steep crater walls, flat plateaus)
    slope_base = np.abs(rng.normal(loc=4.5, scale=4.0, size=(ROWS, COLS))).astype(np.float32)
    slope_base[155:165, 80:120] = rng.uniform(22, 38, size=(10, 40))
    slope_base[185:195, 80:120] = rng.uniform(20, 35, size=(10, 40))
    slope = np.clip(smooth_field(slope_base, sigma=2), 0.0, 45.0)

    # 5. Earth Communication Visibility (% line of sight)
    comm_base = rng.uniform(10, 95, size=(ROWS, COLS)).astype(np.float32)
    comm_base[170:, :] = np.clip(comm_base[170:, :] - 30, 0, 100)
    comm = np.clip(smooth_field(comm_base, sigma=6), 0.0, 100.0)

    return {
        "ice.tif": ice,
        "illumination.tif": illum,
        "radiation.tif": radiation,
        "slope.tif": slope,
        "comm.tif": comm,
    }


def save_geotiffs(layers):
    try:
        import rasterio
        from rasterio.transform import from_bounds

        transform = from_bounds(LON_MIN, LAT_MIN, LON_MAX, LAT_MAX, COLS, ROWS)
        crs = "EPSG:4326"

        for filename, data in layers.items():
            filepath = DATA_RAW_DIR / filename
            with rasterio.open(
                filepath,
                "w",
                driver="GTiff",
                height=ROWS,
                width=COLS,
                count=1,
                dtype=rasterio.float32,
                crs=crs,
                transform=transform,
                nodata=-9999.0,
            ) as dst:
                dst.write(data.astype(np.float32), 1)
            print(f"[OK] Saved GeoTIFF: {filepath} ({ROWS}x{COLS}, CRS: {crs})")

    except ImportError:
        print("[INFO] rasterio not present; saving high-performance NumPy arrays...")
        for filename, data in layers.items():
            base_name = filename.replace(".tif", ".npy")
            filepath = DATA_RAW_DIR / base_name
            np.save(filepath, data)
            print(f"[OK] Saved raster layer: {filepath}")


if __name__ == "__main__":
    print(f"Generating realistic Lunar South Pole dataset ({ROWS}x{COLS})...")
    layers = generate_layers()
    save_geotiffs(layers)
    print("[SUCCESS] Dataset generated in backend/data/raw/")
