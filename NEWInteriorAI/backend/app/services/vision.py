"""
Vision Service
Sends the floor plan image to Claude Vision and returns structured spatial data.
"""
import base64
import json
from typing import Optional

import anthropic
import httpx

from ..config import settings

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


async def fetch_image_bytes(url: str) -> bytes:
    async with httpx.AsyncClient() as client:
        r = await client.get(url, timeout=30)
        r.raise_for_status()
        return r.content


async def analyze_floor_plan_image(
    floor_plan_url: Optional[str],
    rooms_hint: list[str],
    lifestyle: dict,
) -> dict:
    """
    Step 3 — Vision Service.
    Returns structured JSON describing rooms, dimensions, openings, and light.
    """
    if floor_plan_url:
        image_bytes = await fetch_image_bytes(floor_plan_url)
        image_b64 = base64.standard_b64encode(image_bytes).decode()
        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_b64,
                },
            },
            {"type": "text", "text": _build_vision_prompt(rooms_hint, lifestyle)},
        ]
    else:
        content = [
            {
                "type": "text",
                "text": (
                    f"No floor plan image was provided.\n"
                    f"Rooms listed by user: {rooms_hint}\n"
                    f"Lifestyle context: {json.dumps(lifestyle)}\n\n"
                    + _build_vision_prompt(rooms_hint, lifestyle)
                ),
            }
        ]

    message = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": content}],
    )

    raw = message.content[0].text

    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        return json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        return {"raw_analysis": raw, "rooms": [], "confidence": "low"}


def _build_vision_prompt(rooms_hint: list[str], lifestyle: dict) -> str:
    return f"""
You are a professional architectural vision AI.
Analyze this floor plan and return ONLY valid JSON — no markdown, no explanation.

Rooms the user expects: {rooms_hint}
Lifestyle context: {json.dumps(lifestyle)}

Return this exact JSON structure:
{{
  "overall": {{
    "total_sqm": <number or null>,
    "floor_count": <number>,
    "confidence": "high|medium|low"
  }},
  "rooms": [
    {{
      "name": "Living Room",
      "room_type": "living",
      "estimated_sqm": <number or null>,
      "width_m": <number or null>,
      "length_m": <number or null>,
      "ceiling_height_m": <number or null>,
      "window_count": <integer>,
      "door_count": <integer>,
      "natural_light": "low|medium|high",
      "adjacencies": ["kitchen", "hallway"],
      "features": ["open plan", "bay window"],
      "constraints": ["structural column at NE corner"]
    }}
  ],
  "circulation": {{
    "main_entrance": "hallway",
    "primary_path": ["entrance", "hallway", "living room", "kitchen"],
    "bottlenecks": []
  }},
  "observations": "Brief expert notes on the overall layout."
}}
"""
