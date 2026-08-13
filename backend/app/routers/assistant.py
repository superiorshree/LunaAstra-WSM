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


@router.post(
    "",
    response_model=AssistantResponse,
    summary="Convert natural language to weight configuration",
    description="Calls Claude API to parse a priority statement into a structured weight JSON. The returned weights are ready to pass directly to POST /score.",
)
async def assistant(request: AssistantRequest) -> AssistantResponse:
    if not request.text.strip():
        raise HTTPException(status_code=422, detail="Input text cannot be empty.")

    if not CLAUDE_API_KEY:
        logger.warning("CLAUDE_API_KEY not set — returning equal default weights")
        return AssistantResponse(
            weights=DEFAULT_WEIGHTS,
            raw_response="[Claude API not configured — default weights returned]",
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

        # Extract JSON robustly (handle if Claude adds any stray text)
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

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error from Claude: {e}")
        raise HTTPException(status_code=500, detail="Claude returned malformed JSON.")
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception(f"Claude API error in /assistant: {e}")
        raise HTTPException(status_code=500, detail=f"Claude API error: {type(e).__name__}")
