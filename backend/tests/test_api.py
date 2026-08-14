"""
test_api.py — Integration tests for all FastAPI endpoints

Tests:
  - GET /health
  - POST /score
  - POST /explain/site
  - POST /explain/compare
  - GET /explain/report/{site_id}
  - GET /space-weather
  - POST /assistant (with mock fallback)
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["data_loaded"] is True
    assert "ice" in data["layers"]


def test_score_endpoint_default(client):
    payload = {
        "weights": {
            "ice": 0.3,
            "illumination": 0.3,
            "radiation": 0.2,
            "slope": 0.1,
            "comm": 0.1,
        },
        "max_slope_deg": 15.0,
        "top_n": 5,
        "include_xai": True,
    }
    response = client.post("/score", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["grid_rows"] > 0
    assert data["grid_cols"] > 0
    assert len(data["top_sites"]) == 5

    top_site = data["top_sites"][0]
    assert top_site["rank"] == 1
    assert "contributions" in top_site
    assert "risk_profile" in top_site
    assert "ice_confidence" in top_site
    assert 0.0 <= top_site["total_score"] <= 1.0


def test_explain_site_endpoint(client):
    # First trigger scoring
    score_resp = client.post("/score", json={"top_n": 5})
    assert score_resp.status_code == 200
    site_id = score_resp.json()["top_sites"][0]["site_id"]

    # Now explain that site
    response = client.post("/explain/site", json={"site_id": site_id, "include_briefing": True})
    assert response.status_code == 200
    data = response.json()
    assert data["site_id"] == site_id
    assert "risk_profile" in data
    assert "ice_confidence" in data
    assert "contributions" in data
    assert data["mission_briefing"] is not None


def test_explain_compare_endpoint(client):
    payload = {
        "scenario_a": {
            "label": "Water Priority",
            "weights": {"ice": 0.5, "illumination": 0.1, "radiation": 0.2, "slope": 0.1, "comm": 0.1},
            "max_slope_deg": 15.0,
        },
        "scenario_b": {
            "label": "Solar Priority",
            "weights": {"ice": 0.1, "illumination": 0.5, "radiation": 0.2, "slope": 0.1, "comm": 0.1},
            "max_slope_deg": 15.0,
        },
        "top_n": 5,
    }
    response = client.post("/explain/compare", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["scenario_a_label"] == "Water Priority"
    assert data["scenario_b_label"] == "Solar Priority"
    assert "weight_changes" in data
    assert data["narration"] is not None


def test_site_report_endpoint(client):
    score_resp = client.post("/score", json={"top_n": 5})
    site_id = score_resp.json()["top_sites"][0]["site_id"]

    response = client.get(f"/explain/report/{site_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["site_id"] == site_id
    assert "score_percentile" in data
    assert "risk_profile" in data
    assert "ice_confidence" in data


def test_space_weather_endpoint(client):
    response = client.get("/space-weather")
    assert response.status_code == 200
    data = response.json()
    assert data["level"] in ["NORMAL", "ELEVATED", "HIGH"]
    assert "alert_message" in data
    assert "alert_color" in data


def test_assistant_endpoint(client):
    payload = {"text": "prioritize water ice and radiation safety, slope is secondary"}
    response = client.post("/assistant", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "weights" in data
    assert set(data["weights"].keys()) == {"ice", "illumination", "radiation", "slope", "comm"}
