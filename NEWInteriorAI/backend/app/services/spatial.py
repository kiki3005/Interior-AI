"""
Spatial Reasoning Engine
Takes vision output and derives room relationships, flow, zones, and opportunities.
"""
import json
import anthropic

from ..config import settings

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


async def run_spatial_reasoning(
    vision_data: dict,
    lifestyle: dict,
) -> dict:
    """
    Step 4 — Spatial Reasoning Engine.
    Builds room relationship graph, privacy gradient, light map, and zone plan.
    """
    prompt = f"""
You are an expert spatial reasoning AI for interior design.

Vision analysis of the floor plan:
{json.dumps(vision_data, indent=2)}

Client lifestyle:
{json.dumps(lifestyle, indent=2)}

Return ONLY valid JSON — no markdown, no explanation.

{{
  "room_graph": {{
    "nodes": [
      {{"id": "living_room", "label": "Living Room", "zone": "social", "privacy": "public"}}
    ],
    "edges": [
      {{"from": "living_room", "to": "kitchen", "connection_type": "open_plan|doorway|archway"}}
    ]
  }},
  "traffic_flow": {{
    "primary_paths": [["entrance", "hallway", "living_room"]],
    "secondary_paths": [],
    "bottlenecks": [],
    "recommendations": []
  }},
  "privacy_gradient": [
    {{"room": "living_room", "level": "public", "score": 1}},
    {{"room": "master_bedroom", "level": "private", "score": 5}}
  ],
  "natural_light_map": {{
    "morning": ["kitchen", "east_bedroom"],
    "afternoon": ["living_room"],
    "evening": ["west_bedroom"],
    "notes": ""
  }},
  "functional_zones": {{
    "social": ["living_room", "dining_room"],
    "work": ["home_office"],
    "rest": ["bedroom", "master_bedroom"],
    "service": ["kitchen", "laundry", "bathroom"]
  }},
  "lifestyle_conflicts": [],
  "optimization_opportunities": [
    "Consider removing partition between kitchen and dining for open-plan flow."
  ]
}}
"""

    message = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text

    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        return json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        return {"raw": raw, "room_graph": {}, "functional_zones": {}}
