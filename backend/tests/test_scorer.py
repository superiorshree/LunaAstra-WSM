"""
test_scorer.py — Unit tests for the core scoring pipeline

Tests the deterministic scoring engine end-to-end with mock data.
Run with: pytest backend/tests/ -v
"""

import pytest
import numpy as np
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.normalizer import normalize_layer, normalize_all_layers
from app.core.scorer import compute_scores, WeightConfig, ScoredSite
from app.core.explainer import (
    risk_profile, ice_confidence, format_contributions,
    build_site_xai_report, scenario_diff
)
from app.config import FACTOR_HIGHER_IS_BETTER


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def small_grid():
    """5×5 deterministic mock grid for all 5 factors."""
    rng = np.random.default_rng(seed=0)
    return {
        "ice":          rng.uniform(0, 5,    size=(5, 5)).astype(np.float32),
        "illumination": rng.uniform(0, 100,  size=(5, 5)).astype(np.float32),
        "radiation":    rng.uniform(0.5, 10, size=(5, 5)).astype(np.float32),
        "slope":        rng.uniform(0, 30,   size=(5, 5)).astype(np.float32),
        "comm":         rng.uniform(20, 100, size=(5, 5)).astype(np.float32),
    }


@pytest.fixture
def normalized_grid(small_grid):
    return normalize_all_layers(small_grid)


@pytest.fixture
def equal_weights():
    return WeightConfig(ice=0.2, illumination=0.2, radiation=0.2, slope=0.2, comm=0.2)


# ─── Normalization Tests ───────────────────────────────────────────────────────

class TestNormalizer:
    def test_output_range(self, small_grid):
        """All normalized values must be in [0, 1]."""
        normalized = normalize_all_layers(small_grid)
        for factor, arr in normalized.items():
            valid = arr[~np.isnan(arr)]
            assert valid.min() >= 0.0 - 1e-6, f"{factor}: min below 0"
            assert valid.max() <= 1.0 + 1e-6, f"{factor}: max above 1"

    def test_inversion_for_lower_is_better(self):
        """Slope and radiation should be inverted (lower raw = higher score)."""
        data = np.array([[1.0, 5.0, 10.0]], dtype=np.float32)
        normed = normalize_layer(data, higher_is_better=False)
        # Lowest raw value should have highest normalized score
        assert normed[0, 0] > normed[0, 2], "Lowest raw should map to highest score"

    def test_nan_preservation(self):
        """NaN pixels must remain NaN after normalization."""
        data = np.array([[1.0, np.nan, 3.0]], dtype=np.float32)
        normed = normalize_layer(data, higher_is_better=True)
        assert np.isnan(normed[0, 1]), "NaN should be preserved"
        assert not np.isnan(normed[0, 0])
        assert not np.isnan(normed[0, 2])

    def test_all_factors_normalized(self, small_grid):
        """All 5 factors should be present in normalized output."""
        normalized = normalize_all_layers(small_grid)
        assert set(normalized.keys()) == {"ice", "illumination", "radiation", "slope", "comm"}


# ─── Scorer Tests ──────────────────────────────────────────────────────────────

class TestScorer:
    def test_score_grid_shape(self, normalized_grid, small_grid, equal_weights):
        """Score grid must match input shape."""
        result = compute_scores(normalized_grid, small_grid, equal_weights)
        assert result.grid_rows == 5
        assert result.grid_cols == 5
        assert len(result.score_grid) == 5
        assert len(result.score_grid[0]) == 5

    def test_scores_in_range(self, normalized_grid, small_grid, equal_weights):
        """All valid scores must be in [0, 1]."""
        result = compute_scores(normalized_grid, small_grid, equal_weights)
        for row in result.score_grid:
            for val in row:
                if val is not None:
                    assert 0.0 <= val <= 1.0, f"Score out of range: {val}"

    def test_weights_sum_to_one(self):
        """WeightConfig.normalize() must produce weights summing to 1."""
        w = WeightConfig(ice=0.5, illumination=0.5, radiation=0.5, slope=0.5, comm=0.5)
        normalized = w.normalize()
        total = sum(normalized.as_dict().values())
        assert abs(total - 1.0) < 1e-6

    def test_top_n_count(self, normalized_grid, small_grid, equal_weights):
        """Should return exactly top_n sites (or fewer if not enough valid pixels)."""
        result = compute_scores(normalized_grid, small_grid, equal_weights, top_n=3)
        assert len(result.top_sites) == 3

    def test_sites_ranked_descending(self, normalized_grid, small_grid, equal_weights):
        """Top sites must be in descending score order."""
        result = compute_scores(normalized_grid, small_grid, equal_weights, top_n=5)
        scores = [s.total_score for s in result.top_sites]
        assert scores == sorted(scores, reverse=True)

    def test_hard_constraint_masks_steep_pixels(self, normalized_grid, small_grid):
        """Setting max_slope_deg=0 should mask all pixels."""
        w = WeightConfig().normalize()
        result = compute_scores(
            normalized_grid, small_grid, w,
            max_slope_deg=0.0,   # impossibly strict
            top_n=5,
        )
        # With slope=0 constraint, all pixels should be masked
        assert result.valid_pixel_count == 0 or len(result.top_sites) == 0

    def test_contribution_breakdown_sums_to_total(self, normalized_grid, small_grid, equal_weights):
        """Sum of contributions must equal total_score (within floating point)."""
        result = compute_scores(normalized_grid, small_grid, equal_weights, top_n=1)
        site = result.top_sites[0]
        contrib_sum = sum(site.contributions.values())
        assert abs(contrib_sum - site.total_score) < 1e-4, (
            f"Contributions sum {contrib_sum} != total score {site.total_score}"
        )

    def test_space_weather_penalty_reduces_score(self, normalized_grid, small_grid, equal_weights):
        """HIGH space weather alert should reduce scores compared to NORMAL."""
        result_normal = compute_scores(
            normalized_grid, small_grid, equal_weights,
            space_weather_alert="NORMAL"
        )
        result_high = compute_scores(
            normalized_grid, small_grid, equal_weights,
            space_weather_alert="HIGH"
        )
        # Top site score should be equal or lower under HIGH alert
        if result_normal.top_sites and result_high.top_sites:
            assert result_high.top_sites[0].total_score <= result_normal.top_sites[0].total_score + 1e-6


# ─── XAI Tests ────────────────────────────────────────────────────────────────

class TestExplainer:
    @pytest.fixture
    def sample_site(self, normalized_grid, small_grid, equal_weights):
        result = compute_scores(normalized_grid, small_grid, equal_weights, top_n=1)
        return result.top_sites[0]

    def test_risk_profile_all_factors(self, sample_site):
        """Risk profile must cover all 5 factors."""
        profile = risk_profile(sample_site)
        assert set(profile.keys()) == {"ice", "illumination", "radiation", "slope", "comm"}

    def test_risk_levels_valid(self, sample_site):
        """All risk levels must be LOW, MEDIUM, or HIGH."""
        profile = risk_profile(sample_site)
        for factor, fr in profile.items():
            assert fr.risk_level in {"LOW", "MEDIUM", "HIGH"}, \
                f"Invalid risk level for {factor}: {fr.risk_level}"

    def test_radiation_overridden_on_high_alert(self, sample_site):
        """Radiation should be HIGH risk during HIGH solar weather."""
        profile = risk_profile(sample_site, space_weather_alert="HIGH")
        assert profile["radiation"].risk_level == "HIGH"
        assert profile["radiation"].note is not None

    def test_ice_confidence_range(self, sample_site):
        """Ice confidence must be 0–100."""
        conf = ice_confidence(sample_site)
        assert 0.0 <= conf["confidence_pct"] <= 100.0

    def test_contribution_percentages_sum_to_100(self, sample_site):
        """Contribution percentages should sum to ~100%."""
        contribs = format_contributions(sample_site)
        total_pct = sum(c["percentage"] for c in contribs)
        assert abs(total_pct - 100.0) < 0.5

    def test_build_site_xai_report_keys(self, sample_site):
        """Full XAI report must have all expected top-level keys."""
        report = build_site_xai_report(sample_site)
        assert "contributions" in report
        assert "risk_profile" in report
        assert "ice_confidence" in report
        assert "site_id" in report
        assert "total_score" in report
