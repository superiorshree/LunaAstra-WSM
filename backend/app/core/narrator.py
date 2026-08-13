"""
narrator.py — Claude-Powered XAI Narration Engine

Generates natural language explanations using the Claude API.
This module is the ONLY place in the backend where AI is used for generation.

Functions:
  - generate_site_briefing()        → 3-sentence mission briefing per site
  - generate_scenario_narration()   → What-if diff explanation
  - generate_anomaly_flags()        → Unusual pattern descriptions

Architecture note:
  Claude is used here ONLY as a language renderer — it describes
  pre-computed scores in plain English. It does NOT make any scoring
  decisions. All numbers passed to Claude came from deterministic
  arithmetic in scorer.py and explainer.py.
"""

import logging
import json
from typing import Dict, Optional

from app.config import CLAUDE_API_KEY, CLAUDE_MODEL, FACTOR_DISPLAY_NAMES
from app.core.scorer import ScoredSite, ScoreResult
from app.core.explainer import ScenarioDiff

logger = logging.getLogger(__name__)


# ─── Claude Client ────────────────────────────────────────────────────────────

def _get_claude_client():
    """Lazy-initialize the Anthropic client."""
    if not CLAUDE_API_KEY:
        raise ValueError(
            "CLAUDE_API_KEY is not set. Add it to backend/.env to enable "
            "AI narration features."
        )
    try:
        import anthropic
        return anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    except ImportError:
        raise ImportError("anthropic package not installed. pip install anthropic")


def _call_claude(system_prompt: str, user_message: str, max_tokens: int = 500) -> str:
    """
    Make a single Claude API call with structured system + user prompts.

    Args:
        system_prompt:  Defines Claude's role and output format.
        user_message:   The specific data/request for this call.
        max_tokens:     Max tokens in response.

    Returns:
        Claude's response text.
    """
    client = _get_claude_client()
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text.strip()


# ─── Site Briefing ────────────────────────────────────────────────────────────

SITE_BRIEFING_SYSTEM_PROMPT = """
You are a lunar mission planning AI assistant for the LunaAstra Habitat 
Decision Support System (hackathon problem SW02).

Given structured data about a candidate lunar habitat site (scores, risk levels,
and ice detection confidence), write a concise 3-sentence mission briefing.

Rules:
- Write exactly 3 sentences.
- Be specific — reference actual numbers from the data provided.
- Focus on: (1) why this site scored highest, (2) its primary advantage,
  (3) any risk or caveat to be aware of.
- Use scientific but accessible language suitable for a mission planning team.
- Do NOT invent any data not provided to you.
- Do NOT mention that you are an AI or that this is simulated data.
- Output only the 3-sentence briefing. No preamble, no headers.
"""


def generate_site_briefing(
    site: ScoredSite,
    risk_profile: Dict,
    ice_conf: Dict,
    space_weather_alert: str = "NORMAL",
) -> str:
    """
    Generate a 3-sentence mission briefing for a candidate site.

    Args:
        site:                 Scored site from scorer.py
        risk_profile:         Risk profile dict from explainer.risk_profile()
        ice_conf:             Ice confidence dict from explainer.ice_confidence()
        space_weather_alert:  Current alert level

    Returns:
        3-sentence natural language briefing string.
    """
    # Build structured context for Claude
    factor_lines = []
    for factor, score in site.normalized_scores.items():
        risk_info = risk_profile.get(factor, {})
        factor_lines.append(
            f"  - {FACTOR_DISPLAY_NAMES.get(factor, factor)}: "
            f"score={score:.2f}, risk={risk_info.get('risk_level', 'N/A')}, "
            f"contribution={site.contributions.get(factor, 0):.3f}"
        )

    user_message = f"""
Site: {site.site_id} (Rank #{site.rank})
Location: {site.lat:.2f}°, {site.lon:.2f}°
Total Suitability Score: {site.total_score:.4f} (0.0 = worst, 1.0 = best)
Space Weather Alert: {space_weather_alert}

Factor Breakdown:
{chr(10).join(factor_lines)}

Ice Detection: {ice_conf.get('confidence_pct', 0):.1f}% confidence — {ice_conf.get('label', 'N/A')}

Raw Values:
{json.dumps(site.raw_values, indent=2)}
"""

    try:
        briefing = _call_claude(
            system_prompt=SITE_BRIEFING_SYSTEM_PROMPT,
            user_message=user_message,
            max_tokens=300,
        )
        logger.info(f"Generated site briefing for {site.site_id}")
        return briefing
    except Exception as e:
        logger.error(f"Claude API error for site briefing: {e}")
        return _fallback_site_briefing(site, ice_conf, space_weather_alert)


def _fallback_site_briefing(
    site: ScoredSite,
    ice_conf: Dict,
    space_weather_alert: str,
) -> str:
    """Deterministic fallback if Claude API is unavailable."""
    top_factor = max(site.contributions, key=site.contributions.get)
    top_name = FACTOR_DISPLAY_NAMES.get(top_factor, top_factor)
    ice_pct = ice_conf.get("confidence_pct", 0)
    weather_note = (
        " Current elevated solar activity warrants real-time shielding review."
        if space_weather_alert != "NORMAL" else ""
    )
    return (
        f"{site.site_id} at ({site.lat:.2f}°, {site.lon:.2f}°) achieved a "
        f"suitability score of {site.total_score:.3f}, ranking first among "
        f"all candidate locations. "
        f"The primary driver of this ranking was {top_name} "
        f"(contribution: {site.contributions.get(top_factor, 0):.3f}), "
        f"indicating strong conditions in this factor. "
        f"Water ice detection confidence is {ice_pct:.0f}%"
        f" — adequate for preliminary ISRU resource planning.{weather_note}"
    )


# ─── Scenario Narration ───────────────────────────────────────────────────────

SCENARIO_NARRATION_SYSTEM_PROMPT = """
You are a lunar mission planning AI assistant for the LunaAstra Habitat 
Decision Support System.

Given a comparison between two scoring configurations (weight presets),
write a 2–3 sentence explanation of what changed and what the operational
implication is for mission planners.

Rules:
- Be specific about which factors changed and in which direction.
- Explain the practical consequence of the change (e.g., "trading power 
  reliability for water resource access").
- Keep language mission-planning focused, not technical/mathematical.
- Output only the narration. No preamble, no headers.
"""


def generate_scenario_narration(diff: ScenarioDiff) -> str:
    """
    Generate a natural language narration of a what-if scenario comparison.

    Args:
        diff:  ScenarioDiff from explainer.scenario_diff()

    Returns:
        2–3 sentence narration string.
    """
    try:
        narration = _call_claude(
            system_prompt=SCENARIO_NARRATION_SYSTEM_PROMPT,
            user_message=diff.narration_context,
            max_tokens=250,
        )
        logger.info("Generated scenario narration")
        return narration
    except Exception as e:
        logger.error(f"Claude API error for scenario narration: {e}")
        return _fallback_scenario_narration(diff)


def _fallback_scenario_narration(diff: ScenarioDiff) -> str:
    """Deterministic fallback if Claude API is unavailable."""
    changed = [
        f"{info['display_name']} "
        f"({'increased' if info['delta'] > 0 else 'decreased'} "
        f"by {abs(info['delta']):.0%})"
        for info in diff.weight_changes.values()
        if info["changed"]
    ]
    if not changed:
        return "No significant weight changes between the two scenarios."

    factors_str = ", ".join(changed)
    delta_str = (
        f"The top site score changed by {diff.score_delta:+.4f}."
        if diff.score_delta != 0 else ""
    )
    return (
        f"Shifting from '{diff.scenario_a_label}' to '{diff.scenario_b_label}' "
        f"modified priorities for: {factors_str}. "
        f"{delta_str} "
        f"Consult the contribution breakdown above for site-level impact."
    )


# ─── Anomaly Flags ────────────────────────────────────────────────────────────

ANOMALY_SYSTEM_PROMPT = """
You are a lunar mission planning AI assistant for the LunaAstra Habitat 
Decision Support System.

Given score statistics for a candidate site, identify and describe any 
anomalous or noteworthy patterns in a single sentence.

Examples of anomalies: unusually high variance in radiation scores,
ice confidence much higher than expected for illumination levels,
terrain slope at the boundary of the hard constraint threshold.

Output only the anomaly note as a single sentence, or output exactly
"No significant anomalies detected." if nothing stands out.
"""


def generate_anomaly_flags(site: ScoredSite) -> str:
    """
    Generate a brief anomaly flag for a site if warranted.

    Args:
        site:  ScoredSite from scorer.py

    Returns:
        Single sentence anomaly note, or "No significant anomalies detected."
    """
    user_message = f"""
Site {site.site_id} score data:
- Normalized scores: {json.dumps(site.normalized_scores, indent=2)}
- Raw values: {json.dumps(site.raw_values, indent=2)}
- Total score: {site.total_score:.4f}

Is anything anomalous or noteworthy about this site's data patterns?
"""
    try:
        return _call_claude(
            system_prompt=ANOMALY_SYSTEM_PROMPT,
            user_message=user_message,
            max_tokens=100,
        )
    except Exception as e:
        logger.error(f"Claude API error for anomaly flags: {e}")
        return "Anomaly detection unavailable (Claude API offline)."
