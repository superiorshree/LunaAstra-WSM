"""
assistant.py — POST /assistant Router

Natural language to weight JSON converter using Claude API.
User types "prioritize water over sunlight" → returns structured weights.
"""

import logging
import json
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import CLAUDE_API_KEY, CLAUDE_MODEL
from app.config import DEFAULT_WEIGHTS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/assistant", tags=["AI Assistant"])


WEIGHT_EXTRACTION_SYSTEM_PROMPT = """
You are a parameter extraction assistant for the LunaAstra Lunar Habitat 
Decision Support System.

The system scores lunar locations across 5 factors:
  - ice:          Water Ice Availability (higher = more ice deposits)
  - illumination: Solar Illumination (higher = more sunlight for power)
  - radiation:    Radiation Safety (higher score = safer, i.e., less radiation)
  - slope:        Terrain Suitability (higher score = flatter terrain)
  - comm:         Earth Communication Visibility (higher = better Earth contact)

Your task: Given a natural language priority statement from a mission planner,
return ONLY a valid JSON object with exactly these 5 keys and float values
that represent relative priorities. The values do NOT need to sum to 1.0 —
the system will normalize them automatically.

Rules:
- Return ONLY the JSON object. No explanation, no markdown, no preamble.
- All values must be >= 0.0
- A higher number means higher priority for that factor
- If a factor is not mentioned, use a neutral weight of 0.2
- If told to ignore a factor, set it to 0.05 (never 0 to avoid division issues)

Example input: "I want to prioritize water ice and flat terrain, radiation is secondary"
Example output: {"ice": 0.5, "illumination": 0.15, "radiation": 0.25, "slope": 0.45, "comm": 0.15}
"""


class AssistantRequest(BaseModel):
    text: str

    model_config = {"json_schema_extra": {
        "example": {"text": "prioritize water safety over sunlight, terrain flatness is most important"}
    }}


class AssistantResponse(BaseModel):
    weights:       dict
    raw_response:  str
    input_text:    str
    normalized:    bool = True


def _heuristic_extract_weights(text: str) -> dict:
    """
    Intelligent offline NLP keyword heuristic parser.
    Used when Claude API key is absent, offline, or returns auth error.
    """
    lower = text.lower()
    weights = {"ice": 0.20, "illumination": 0.20, "radiation": 0.20, "slope": 0.20, "comm": 0.20}

    # Factor keyword definitions
    keywords = {
        "ice": ["water", "ice", "h2o", "isru", "hydrogen", "cabeus", "shackleton", "volatile"],
        "illumination": ["sun", "solar", "sunlight", "illumination", "power", "energy", "photovoltaic", "light"],
        "radiation": ["radiation", "shielding", "cosmic", "dose", "storm", "crater floor", "hazard", "safety"],
        "slope": ["slope", "flat", "flatness", "terrain", "construction", "roughness", "gradient", "landing"],
        "comm": ["comm", "communication", "earth", "line of sight", "antenna", "signal", "radio", "contact"],
    }

    # High priority indicators
    boost_words = ["prioritize", "priority", "important", "critical", "focus", "need", "essential", "primary", "above all"]
    reduce_words = ["secondary", "ignore", "less", "minor", "minimal", "don't care", "dont care"]

    for factor, factor_words in keywords.items():
        found = any(w in lower for w in factor_words)
        if found:
            # Check if boosted or reduced in proximity
            if any(bw in lower for bw in boost_words):
                weights[factor] += 0.30
            else:
                weights[factor] += 0.15

        if any(rw in lower and any(fw in lower for fw in factor_words) for rw in reduce_words):
            weights[factor] = max(0.05, weights[factor] - 0.10)

    # Normalize to sum 1.0
    total = sum(weights.values())
    return {k: round(v / total, 4) for k, v in weights.items()}


@router.post(
    "",
    response_model=AssistantResponse,
    summary="Convert natural language to weight configuration",
    description="Calls Claude API (with deterministic NLP fallback) to parse a priority statement into structured weight JSON.",
)
async def assistant(request: AssistantRequest) -> AssistantResponse:
    if not request.text.strip():
        raise HTTPException(status_code=422, detail="Input text cannot be empty.")

    # If no key is set or is placeholder
    if not CLAUDE_API_KEY or "your_claude_api_key" in CLAUDE_API_KEY:
        weights = _heuristic_extract_weights(request.text)
        return AssistantResponse(
            weights=weights,
            raw_response="[Heuristic NLP Engine Applied — Offline Mode]",
            input_text=request.text,
        )

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=150,
            system=WEIGHT_EXTRACTION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": request.text}],
        )

        raw_text = response.content[0].text.strip()

        # Extract JSON robustly
        json_match = re.search(r'\{[^}]+\}', raw_text, re.DOTALL)
        if not json_match:
            raise ValueError(f"Claude did not return valid JSON: {raw_text}")

        weights = json.loads(json_match.group())

        # Validate keys
        expected_keys = {"ice", "illumination", "radiation", "slope", "comm"}
        if set(weights.keys()) != expected_keys:
            raise ValueError(
                f"Claude returned unexpected keys: {set(weights.keys())} "
                f"(expected {expected_keys})"
            )

        # Validate values are numeric and non-negative
        for k, v in weights.items():
            if not isinstance(v, (int, float)) or v < 0:
                raise ValueError(f"Invalid weight for '{k}': {v}")

        logger.info(f"Assistant: '{request.text[:60]}...' → {weights}")

        return AssistantResponse(
            weights=weights,
            raw_response=raw_text,
            input_text=request.text,
        )

    except Exception as e:
        logger.warning(f"Claude API offline or auth error ({e}) — activating NLP heuristic fallback.")
        weights = _heuristic_extract_weights(request.text)
        return AssistantResponse(
            weights=weights,
            raw_response=f"[NLP Heuristic Fallback (Reason: {type(e).__name__})]",
            input_text=request.text,
        )
