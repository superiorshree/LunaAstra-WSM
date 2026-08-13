# Place your aligned GeoTIFF files here (read-only, never modified by the backend)
#
# Expected files:
#   ice.tif           — Water ice availability (LEND dataset)
#   illumination.tif  — Solar illumination percentage (Diviner/LRO)
#   radiation.tif     — Radiation exposure (CRaTER/LRO)
#   slope.tif         — Terrain slope in degrees (LOLA DEM)
#   comm.tif          — Earth communication visibility (geometric model)
#
# Requirements:
#   - All files must be co-registered (same CRS, same pixel grid, same extent)
#   - All files must use a single band (Band 1)
#   - GeoTIFF format with proper NoData values set for masked regions
#
# During Phase 1 (mock mode), this folder can be empty.
# Set USE_MOCK_DATA=false in backend/.env to switch to real data.
