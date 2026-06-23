"""
Claude AI Service
All LLM generation calls for the 10-step design pipeline.
Each function retrieves relevant design rules from Qdrant (RAG) before prompting.
"""
import json
import anthropic

from ..config import settings
from .vector_store import retrieve_design_knowledge, find_similar_preferences

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _rag_rules(query: str, category: str = None, top_k: int = 4) -> str:
    """Retrieve relevant design rules and format them for injection into a prompt."""
    try:
        rules = retrieve_design_knowledge(query, category=category, top_k=top_k)
        if rules:
            return "Relevant design rules to apply:\n" + "\n".join(f"• {r}" for r in rules)
    except Exception:
        pass
    return ""


def _user_prefs(user_id: str, query: str) -> str:
    """Retrieve relevant user preferences for RAG personalisation."""
    try:
        prefs = find_similar_preferences(user_id, query, top_k=5)
        if prefs:
            lines = [f"• {p['preference_type']}: {p['value']} (weight {p['weight']})" for p in prefs]
            return "Known client preferences:\n" + "\n".join(lines)
    except Exception:
        pass
    return ""


def _call(prompt: str, max_tokens: int = 2000) -> str:
    message = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


# ── Step 3: Floor plan analysis (text summary of vision JSON) ─────────────────

async def analyze_floor_plan(
    floor_plan_url,
    lifestyle: dict,
    rooms: list[str],
    user_id: str = "",
) -> str:
    rules = _rag_rules("floor plan analysis room inventory", "space_planning")
    prompt = f"""You are a professional interior design AI.
{rules}

Rooms: {rooms}
Lifestyle: {json.dumps(lifestyle)}

Provide a structured floor plan analysis:
1. ROOM INVENTORY — all rooms, estimated square footage, key dimensions
2. SPATIAL OBSERVATIONS — doors, windows, natural light, ceiling height
3. ROOM ADJACENCY — connections and functional relationships
4. KEY CONSTRAINTS — structural elements, awkward proportions
5. DESIGN OPPORTUNITIES — focal points, storage potential, light maximisation
6. CONFIDENCE NOTES — what would change with measured drawings

Be specific and professional."""
    return _call(prompt)


# ── Step 4: Spatial intelligence ─────────────────────────────────────────────

async def generate_spatial_intelligence(
    rooms: list[str],
    lifestyle: dict,
    analysis: str,
    user_id: str = "",
) -> str:
    rules = _rag_rules("traffic flow circulation privacy zones", "space_planning")
    prompt = f"""You are a spatial intelligence AI for interior design.
{rules}

Floor plan analysis:
{analysis}

Rooms: {rooms}
Lifestyle: {json.dumps(lifestyle)}

Create a spatial intelligence report:
1. ROOM RELATIONSHIP GRAPH — how rooms connect (text representation)
2. TRAFFIC FLOW — primary paths, secondary paths, bottlenecks
3. PRIVACY GRADIENT — public → semi-public → private zones
4. NATURAL LIGHT MAP — morning, afternoon, and evening light distribution
5. FUNCTIONAL ZONES — social, work, rest, service areas
6. LIFESTYLE CONFLICTS — where the current layout clashes with how they live
7. OPTIMISATION RECOMMENDATIONS — specific, actionable improvements"""
    return _call(prompt)


# ── Step 5: Room design ───────────────────────────────────────────────────────

async def generate_room_design(
    room: str,
    lifestyle: dict,
    project_name: str,
    spatial: str,
    user_id: str = "",
) -> str:
    rules = _rag_rules(f"{room} furniture layout lighting", top_k=5)
    prefs = _user_prefs(user_id, f"{room} design") if user_id else ""
    prompt = f"""You are a world-class interior designer.
{rules}
{prefs}

Project: {project_name}
Room: {room}
Spatial context: {spatial[:800] if spatial else "not available"}
Lifestyle: {json.dumps(lifestyle)}

Create a complete design brief for the {room}:
1. DESIGN CONCEPT — core idea (2-3 sentences)
2. COLOR PALETTE — 4-5 specific colors with hex codes
3. FURNITURE PLAN — every piece, dimensions, placement rationale
4. LAYOUT STRATEGY — traffic flow, focal point, conversation zones
5. LIGHTING PLAN — ambient, task, and accent layers with product types
6. MATERIALS & TEXTURES — floors, walls, soft furnishings, surfaces
7. DECOR & ACCESSORIES — art, plants, objects
8. STORAGE SOLUTIONS — built-in and freestanding
9. LIFESTYLE ADAPTATIONS — how this design serves their specific life
10. SPACE OPTIMISATION — techniques to enhance perceived space"""
    return _call(prompt, max_tokens=2500)


# ── Step 6: Style variants ────────────────────────────────────────────────────

async def generate_style_variant(
    style: str,
    rooms: list[str],
    lifestyle: dict,
    user_id: str = "",
) -> str:
    category_map = {
        "Modern": "style_modern",
        "Scandinavian": "style_scandinavian",
        "Luxury": "style_luxury",
    }
    rules = _rag_rules(f"{style} interior design", category_map.get(style, "style_modern"))
    prompt = f"""You are an expert interior designer specialising in {style} design.
{rules}

Rooms: {rooms}
Lifestyle: {json.dumps(lifestyle)}

Create a complete {style} style direction:
1. {style.upper()} PHILOSOPHY — the 3 core principles
2. SIGNATURE ELEMENTS — 5 must-have design moves
3. COLOR STORY — specific palette with hex codes
4. KEY FURNITURE — defining shapes, materials, and scale
5. MATERIAL PALETTE — characteristic textures and finishes
6. LIGHTING CHARACTER — what makes lighting feel {style}
7. LIFESTYLE FIT — how {style} suits this client
8. WHAT TO AVOID — the 3 most common mistakes in this style
9. ROOM-BY-ROOM APPLICATION — one paragraph per room"""
    return _call(prompt, max_tokens=2500)


# ── Step 6b: Style Comparison Engine (auto-generates all 3) ──────────────────

async def generate_style_comparison(
    room: str,
    lifestyle: dict,
    spatial: str,
    user_id: str = "",
) -> dict:
    """Auto-generates Modern, Scandinavian, and Luxury variants in parallel."""
    import asyncio

    async def _variant(style: str) -> str:
        rules = _rag_rules(f"{style} {room}", top_k=3)
        prompt = f"""You are an interior designer. Create a concise {style} design brief for a {room}.
{rules}
Lifestyle: {json.dumps(lifestyle)}

Include: concept sentence, color palette (hex), 5 key furniture pieces, 2 lighting choices, signature material.
Keep it under 300 words."""
        return _call(prompt, max_tokens=500)

    modern, scandi, luxury = await asyncio.gather(
        _variant("Modern"),
        _variant("Scandinavian"),
        _variant("Luxury"),
    )
    return {"modern": modern, "scandinavian": scandi, "luxury": luxury}


# ── Step 7: Pinterest inspiration ────────────────────────────────────────────

async def generate_inspiration(
    rooms: list[str],
    lifestyle: dict,
    user_id: str = "",
) -> str:
    prefs = _user_prefs(user_id, "design inspiration mood board") if user_id else ""
    prompt = f"""You are a creative director and interior design curator.
{prefs}

Rooms: {rooms}
Lifestyle: {json.dumps(lifestyle)}

Create a Pinterest-style inspiration guide. For each room:
— SEARCH KEYWORDS: 8-10 specific terms for Pinterest/Instagram
— MOOD DESCRIPTION: the feeling and atmosphere
— COLOR STORY: exact shades and combinations
— TEXTURE COMBINATIONS: layered materials
— LIGHTING MOOD: quality and character of light
— 3 REFERENCE CONCEPTS: specific, visualisable scenes in one sentence each

Be evocative, specific, and inspiring."""
    return _call(prompt, max_tokens=2500)


# ── Step 8: Shopping / Recommendation Engine ─────────────────────────────────

async def generate_shopping_list(
    rooms: list[str],
    lifestyle: dict,
    user_id: str = "",
) -> str:
    rules = _rag_rules("furniture selection budget scale", "furniture")
    prefs = _user_prefs(user_id, "furniture materials shopping") if user_id else ""
    budget = lifestyle.get("budget", "mid")
    budget_labels = {"low": "under £500/item", "mid": "£500–2000/item",
                     "premium": "£2000–8000/item", "luxury": "£8000+/item"}
    prompt = f"""You are an interior design shopping expert.
{rules}
{prefs}

Rooms: {rooms}
Budget: {budget} ({budget_labels.get(budget, "mid range")})
Lifestyle: {json.dumps(lifestyle)}

For each room create a full shopping list:
ITEM | Category | Material | Color | Price range | Priority (Essential/Nice-to-have) | Where to source

Categories: seating, storage, lighting, soft furnishings, rugs, art, accessories, plants

End with:
- ROOM BUDGET ESTIMATE (min–max)
- TOTAL PROJECT BUDGET ESTIMATE
- TOP 3 SPLURGE-WORTHY PIECES (where to invest)
- TOP 3 SAVE OPPORTUNITIES (where to economise)"""
    return _call(prompt, max_tokens=2500)


# ── Step 9: Visualisation prompts ────────────────────────────────────────────

async def generate_visualization_prompts(
    rooms: list[str],
    lifestyle: dict,
    user_id: str = "",
) -> str:
    styles = lifestyle.get("styles", ["Modern"])
    style_str = styles[0] if styles else "Modern"
    prompt = f"""You are an AI image generation prompt engineer specialising in architectural visualisation.

Rooms: {rooms}
Primary style: {style_str}
Lifestyle: {json.dumps(lifestyle)}

Write a DALL-E 3 / Midjourney optimised prompt for EACH room.

Each prompt must:
- Start with "Professional interior photography,"
- Specify the exact room type
- Name key furniture and their materials/colors
- Describe lighting quality (golden hour / diffused daylight / warm evening)
- Include camera: wide-angle, eye-level, 35mm lens
- End with: --ar 16:9 --style raw --q 2

Format:
[ROOM NAME]
[Full prompt on one line]

Make these detailed enough to produce photorealistic, magazine-quality renders."""
    return _call(prompt, max_tokens=2000)


# ── Step 10: Before / After ───────────────────────────────────────────────────

async def generate_before_after(
    rooms: list[str],
    lifestyle: dict,
    project_name: str,
    user_id: str = "",
) -> str:
    prompt = f"""You are a senior interior designer presenting a transformation to a client.

Project: {project_name}
Rooms redesigned: {rooms}
Client lifestyle: {json.dumps(lifestyle)}

Write a compelling Before vs After transformation report:

BEFORE — THE CURRENT SITUATION
- Typical pain points of an un-designed version of these spaces
- Missed opportunities (light, storage, flow, aesthetics)

AFTER — THE TRANSFORMATION
- How each pain point is resolved
- Functional improvements (quantify where possible: "40% more storage")
- Emotional and lifestyle impact

IMPROVEMENT SCORECARD
Score each out of 10 (before → after):
• Functionality  • Storage  • Natural light  • Aesthetics  • Space efficiency  • Lifestyle fit

THE 3 DECISIONS THAT CHANGED EVERYTHING
Brief explanation of the highest-impact design choices.

NEXT STEPS
How to get started, what to prioritise, realistic timeline.

Write this warmly, professionally, as if presenting in person."""
    return _call(prompt, max_tokens=2500)
