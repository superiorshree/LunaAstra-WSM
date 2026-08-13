"""
explainer.py — XAI Explainability Layer

Transforms raw scoring arithmetic into human-readable intelligence.
Every function here is fully deterministic — NO AI/ML involved.
Claude narration is handled separately in narrator.py.

Functions:
  - risk_profile()          → LOW/MEDIUM/HIGH labels per factor per site
  - ice_confidence()        → Detection confidence score (0–100%)
  - format_contributions()  → Percentage breakdown of score contributions
  - scenario_diff()         → Delta analysis between two ScoreResults
  - build_site_xai_report() → Full XAI package for a single site
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.config import (
    RISK_THRESHOLDS,
    ICE_CONFIDENCE_WEIGHTS,
    FACTOR_DISPLAY_NAMES,
    FACTOR_UNITS,
    SPACE_WEATHER_RADIATION_PENALTY,
)
from app.core.scorer import ScoredSite, ScoreResult

logger = logging.getLogger(__name__)


# ─── Risk Profile ─────────────────────────────────────────────────────────────

RISK_COLORS = {
    "LOW":    "#22c55e",    # green
    "MEDIUM": "#f59e0b",    # amber
    "HIGH":   "#ef4444",    # red
}

RISK_EMOJI = {
    "LOW":    "🟢",
    "MEDIUM": "🟡",
    "HIGH":   "🔴",
}


@dataclass
class FactorRisk:
    """Risk assessment for a single factor at a single site."""
    factor: str
    display_name: str
    normalized_score: float
    raw_value: float
    unit: str
    risk_level: str          # "LOW" | "MEDIUM" | "HIGH"
    color: str               # hex color for UI
    emoji: str
    note: Optional[str] = None   # e.g., "Overridden by solar storm"


def risk_profile(
    site: ScoredSite,
    space_weather_alert: str = "NORMAL",
) -> Dict[str, FactorRisk]:
    """
    Assign LOW/MEDIUM/HIGH risk labels to each factor for a given site.

    Thresholds (from config.py):
      normalized_score >= 0.70 → LOW RISK
      normalized_score >= 0.40 → MEDIUM RISK
      normalized_score <  0.40 → HIGH RISK

    Special override: radiation is forced to HIGH RISK during "HIGH" solar events,
    regardless of normalized score.

    Args:
        site:                 A ScoredSite from scorer.py
        space_weather_alert:  "NORMAL" | "ELEVATED" | "HIGH"

    Returns:
        Dict of {factor: FactorRisk} with labeled risk levels.
    """
    profile = {}

    for factor, norm_score in site.normalized_scores.items():
        # Determine base risk level from score
        if norm_score >= RISK_THRESHOLDS["LOW"]:
            risk_level = "LOW"
        elif norm_score >= RISK_THRESHOLDS["MEDIUM"]:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        note = None

        # Override: radiation risk during high solar activity
        if factor == "radiation" and space_weather_alert == "HIGH":
            risk_level = "HIGH"
            note = f"Overridden: Active solar storm detected (alert={space_weather_alert})"
        elif factor == "radiation" and space_weather_alert == "ELEVATED":
            if risk_level == "LOW":
                risk_level = "MEDIUM"
                note = f"Elevated due to solar activity (alert={space_weather_alert})"

        profile[factor] = FactorRisk(
            factor=factor,
            display_name=FACTOR_DISPLAY_NAMES.get(factor, factor),
            normalized_score=round(norm_score, 4),
            raw_value=site.raw_values.get(factor, 0.0),
            unit=FACTOR_UNITS.get(factor, ""),
            risk_level=risk_level,
            color=RISK_COLORS[risk_level],
            emoji=RISK_EMOJI[risk_level],
            note=note,
        )

    return profile


# ─── Ice Detection Confidence ─────────────────────────────────────────────────

def ice_confidence(site: ScoredSite) -> Dict:
    """
    Compute a rule-based ice detection confidence score (0–100%).

    Combines two proxy signals:
      - Primary (60%):   normalized ice score (LEND neutron flux proxy)
      - Secondary (40%): inverse of illumination score (colder permanent shadow
                         regions correlate with ice preservation)

    The result is presented as a confidence percentage in the UI,
    making the system appear as a detection tool rather than a simple lookup.

    Args:
        site:  A ScoredSite from scorer.py

    Returns:
        Dict with confidence score, signal breakdown, and interpretation label.
    """
    ice_score  = site.normalized_scores.get("ice", 0.0)

    # Cold, permanently shadowed regions (low illumination) favor ice
    illum_score = site.normalized_scores.get("illumination", 0.5)
    shadow_proxy = 1.0 - illum_score   # low illumination = higher shadow confidence

    w_ice  = ICE_CONFIDENCE_WEIGHTS["ice_score"]
    w_temp = ICE_CONFIDENCE_WEIGHTS["temp_score"]

    confidence_raw = (w_ice * ice_score) + (w_temp * shadow_proxy)
    confidence_pct = round(confidence_raw * 100, 1)

    # Interpretation label
    if confidence_pct >= 75:
        label = "HIGH CONFIDENCE"
        color = "#22c55e"
    elif confidence_pct >= 45:
        label = "MODERATE CONFIDENCE"
        color = "#f59e0b"
    else:
        label = "LOW CONFIDENCE"
        color = "#ef4444"

    return {
        "confidence_pct":  confidence_pct,
        "label":           label,
        "color":           color,
        "signals": {
            "neutron_flux_proxy":   round(ice_score * 100, 1),
            "shadow_proxy":         round(shadow_proxy * 100, 1),
        },
        "weights_used": {
            "neutron_flux_proxy":   w_ice,
            "shadow_proxy":         w_temp,
        },
        "note": (
            "Confidence based on LEND neutron flux proxy (60%) "
            "and permanent shadow proxy from illumination data (40%)."
        ),
    }


# ─── Contribution Formatting ──────────────────────────────────────────────────

def format_contributions(site: ScoredSite) -> List[Dict]:
    """
    Format the contribution breakdown for chart rendering.

    Returns a list of dicts compatible with Recharts BarChart:
      [
        { "factor": "ice", "display_name": "Water Ice Availability",
          "contribution": 0.142, "percentage": 28.4,
          "weight": 0.2, "normalized_score": 0.71 },
        ...
      ]

    Args:
        site:  A ScoredSite from scorer.py

    Returns:
        List of contribution dicts, sorted by contribution descending.
    """
    result = []
    total = site.total_score if site.total_score > 0 else 1.0   # avoid /0

    for factor, contribution in site.contributions.items():
        norm_score = site.normalized_scores.get(factor, 0.0)

        # Back-calculate weight: contribution = weight × normalized_score
        weight = (contribution / norm_score) if norm_score > 0 else 0.0

        result.append({
            "factor":           factor,
            "display_name":     FACTOR_DISPLAY_NAMES.get(factor, factor),
            "contribution":     round(contribution, 4),
            "percentage":       round((contribution / total) * 100, 1),
            "weight":           round(weight, 4),
            "normalized_score": round(norm_score, 4),
            "raw_value":        site.raw_values.get(factor, None),
            "unit":             FACTOR_UNITS.get(factor, ""),
        })

    return sorted(result, key=lambda x: x["contribution"], reverse=True)


# ─── Scenario Comparison ──────────────────────────────────────────────────────

@dataclass
class ScenarioDiff:
    """Comparison between two scoring configurations."""
    scenario_a_label: str
    scenario_b_label: str

    # Weight deltas: {factor: (weight_a, weight_b, delta)}
    weight_changes: Dict[str, Dict] = field(default_factory=dict)

    # Top site changes
    top_site_a: Optional[Dict] = None
    top_site_b: Optional[Dict] = None

    # Score delta for the top site
    score_delta: float = 0.0

    # Factor that drove the biggest change
    dominant_factor_change: Optional[str] = None

    # Formatted for Claude narration input
    narration_context: str = ""


def scenario_diff(
    result_a: ScoreResult,
    result_b: ScoreResult,
    label_a: str = "Scenario A",
    label_b: str = "Scenario B",
) -> ScenarioDiff:
    """
    Compute the delta between two scoring runs.

    Used to power the What-If comparison feature.
    The output is also passed to Claude in narrator.py to generate
    a natural language description of what changed and why.

    Args:
        result_a:  First ScoreResult (from /score)
        result_b:  Second ScoreResult (from /score)
        label_a:   Human-readable name for scenario A
        label_b:   Human-readable name for scenario B

    Returns:
        ScenarioDiff with deltas and narration context.
    """
    weights_a = result_a.weights_applied
    weights_b = result_b.weights_applied

    weight_changes = {}
    max_delta_factor = None
    max_delta_val = 0.0

    for factor in weights_a:
        w_a = weights_a.get(factor, 0.0)
        w_b = weights_b.get(factor, 0.0)
        delta = w_b - w_a
        weight_changes[factor] = {
            "weight_a":    round(w_a, 4),
            "weight_b":    round(w_b, 4),
            "delta":       round(delta, 4),
            "changed":     abs(delta) > 0.001,
            "display_name": FACTOR_DISPLAY_NAMES.get(factor, factor),
        }
        if abs(delta) > abs(max_delta_val):
            max_delta_val = delta
            max_delta_factor = factor

    top_a = result_a.top_sites[0] if result_a.top_sites else None
    top_b = result_b.top_sites[0] if result_b.top_sites else None
    score_delta = 0.0

    if top_a and top_b:
        score_delta = round(top_b.total_score - top_a.total_score, 4)

    # Build structured narration context for Claude
    narration_context = _build_narration_context(
        label_a=label_a,
        label_b=label_b,
        weight_changes=weight_changes,
        top_a=top_a,
        top_b=top_b,
        score_delta=score_delta,
    )

    return ScenarioDiff(
        scenario_a_label=label_a,
        scenario_b_label=label_b,
        weight_changes=weight_changes,
        top_site_a=_site_summary(top_a) if top_a else None,
        top_site_b=_site_summary(top_b) if top_b else None,
        score_delta=score_delta,
        dominant_factor_change=max_delta_factor,
        narration_context=narration_context,
    )


def _site_summary(site: ScoredSite) -> Dict:
    return {
        "site_id":     site.site_id,
        "lat":         site.lat,
        "lon":         site.lon,
        "total_score": site.total_score,
        "contributions": site.contributions,
    }


def _build_narration_context(
    label_a: str,
    label_b: str,
    weight_changes: Dict,
    top_a: Optional[ScoredSite],
    top_b: Optional[ScoredSite],
    score_delta: float,
) -> str:
    """Build a structured text block to send to Claude for narration."""
    lines = [
        f"Comparison: '{label_a}' vs '{label_b}'",
        "",
        "Weight Changes:",
    ]
    for factor, info in weight_changes.items():
        if info["changed"]:
            direction = "increased" if info["delta"] > 0 else "decreased"
            lines.append(
                f"  - {info['display_name']}: {info['weight_a']:.2f} → "
                f"{info['weight_b']:.2f} ({direction} by {abs(info['delta']):.2f})"
            )

    if top_a and top_b:
        lines += [
            "",
            f"Top Site in {label_a}: {top_a.site_id} at "
            f"({top_a.lat}°, {top_a.lon}°), score={top_a.total_score:.4f}",
            f"Top Site in {label_b}: {top_b.site_id} at "
            f"({top_b.lat}°, {top_b.lon}°), score={top_b.total_score:.4f}",
            f"Score delta: {score_delta:+.4f}",
            "",
            f"Contribution breakdown for {label_a} top site:",
        ]
        for factor, contrib in top_a.contributions.items():
            lines.append(
                f"  - {FACTOR_DISPLAY_NAMES.get(factor, factor)}: {contrib:.4f}"
            )
        lines += ["", f"Contribution breakdown for {label_b} top site:"]
        for factor, contrib in top_b.contributions.items():
            lines.append(
                f"  - {FACTOR_DISPLAY_NAMES.get(factor, factor)}: {contrib:.4f}"
            )

    return "\n".join(lines)


# ─── Full XAI Report Builder ──────────────────────────────────────────────────

def build_site_xai_report(
    site: ScoredSite,
    space_weather_alert: str = "NORMAL",
    include_contributions: bool = True,
    include_risk_profile: bool = True,
    include_ice_confidence: bool = True,
) -> Dict:
    """
    Build the complete XAI report package for a single site.

    This is the data payload sent to the frontend for the
    MissionBriefing + RiskProfile + ContributionChart components.
    Claude narration is added separately by the /explain/site router.

    Returns:
        Full dict ready for JSON serialization.
    """
    report = {
        "site_id":     site.site_id,
        "rank":        site.rank,
        "lat":         site.lat,
        "lon":         site.lon,
        "total_score": site.total_score,
        "raw_values":  site.raw_values,
    }

    if include_contributions:
        report["contributions"] = format_contributions(site)

    if include_risk_profile:
        rp = risk_profile(site, space_weather_alert=space_weather_alert)
        report["risk_profile"] = {
            factor: {
                "display_name":     fr.display_name,
                "risk_level":       fr.risk_level,
                "color":            fr.color,
                "emoji":            fr.emoji,
                "normalized_score": fr.normalized_score,
                "raw_value":        fr.raw_value,
                "unit":             fr.unit,
                "note":             fr.note,
            }
            for factor, fr in rp.items()
        }

    if include_ice_confidence:
        report["ice_confidence"] = ice_confidence(site)

    return report
