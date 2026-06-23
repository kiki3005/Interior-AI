"""
Design Knowledge Base
Interior design and architectural rules indexed into Qdrant at startup.
Add new rules here — they are automatically embedded and retrieved via RAG.
"""

DESIGN_RULES: list[dict] = [

    # ── Space planning ────────────────────────────────────────────────────────
    {"id": "sp-001", "category": "space_planning",
     "text": "Primary circulation paths must be at least 90cm wide. For wheelchairs, 120cm minimum."},
    {"id": "sp-002", "category": "space_planning",
     "text": "Furniture should never block door swings. Maintain a 90cm clearance arc in front of every door."},
    {"id": "sp-003", "category": "space_planning",
     "text": "In living rooms, allow 45cm between the sofa and coffee table for comfortable reach and movement."},
    {"id": "sp-004", "category": "space_planning",
     "text": "Beds need a minimum 60cm clearance on the sides for dressing. 90cm is preferred on the primary side."},
    {"id": "sp-005", "category": "space_planning",
     "text": "Kitchen work triangle (sink, hob, fridge) should total between 4m and 8m for efficiency."},
    {"id": "sp-006", "category": "space_planning",
     "text": "Dining tables need 90cm clearance on all sides for chairs to pull out and guests to move freely."},

    # ── Lighting ──────────────────────────────────────────────────────────────
    {"id": "lt-001", "category": "lighting",
     "text": "Every room needs three lighting layers: ambient (general), task (functional), and accent (decorative)."},
    {"id": "lt-002", "category": "lighting",
     "text": "Avoid single overhead lights — they create flat, unflattering light. Use multiple lower sources."},
    {"id": "lt-003", "category": "lighting",
     "text": "Kelvin temperature guide: 2700K (warm/cozy) for bedrooms and living rooms; 4000K (cool/bright) for kitchens and offices."},
    {"id": "lt-004", "category": "lighting",
     "text": "Mirror a window on the opposite wall with a well-placed lamp to double perceived natural light."},
    {"id": "lt-005", "category": "lighting",
     "text": "Under-cabinet lighting in kitchens eliminates shadows on work surfaces and is considered essential in premium designs."},

    # ── Color theory ──────────────────────────────────────────────────────────
    {"id": "ct-001", "category": "color",
     "text": "The 60-30-10 rule: 60% dominant color (walls/floors), 30% secondary (large furniture), 10% accent (accessories)."},
    {"id": "ct-002", "category": "color",
     "text": "Cool colors (blues, greens, grays) make spaces feel larger and calmer. Warm colors (terracottas, ochres) make spaces feel intimate."},
    {"id": "ct-003", "category": "color",
     "text": "Paint a single feature wall a deeper tone of the room's main color to add depth without overwhelming the space."},
    {"id": "ct-004", "category": "color",
     "text": "For small rooms: keep walls and large furniture in the same tonal family to blur boundaries and maximise perceived space."},
    {"id": "ct-005", "category": "color",
     "text": "Natural materials (oak, linen, stone) act as neutrals and work with any color palette."},

    # ── Furniture selection ───────────────────────────────────────────────────
    {"id": "fs-001", "category": "furniture",
     "text": "In small rooms, choose furniture with legs rather than floor-sitting pieces. Visible floor space makes rooms feel larger."},
    {"id": "fs-002", "category": "furniture",
     "text": "Scale matters: oversized furniture in a small room is a common mistake. Max sofa length = room width minus 60cm."},
    {"id": "fs-003", "category": "furniture",
     "text": "Rugs should be large enough for all front legs of seating furniture to sit on them. A too-small rug is worse than no rug."},
    {"id": "fs-004", "category": "furniture",
     "text": "Mix material weights: pair heavy (stone, dark wood) with light (linen, glass, pale oak) for visual balance."},
    {"id": "fs-005", "category": "furniture",
     "text": "Multifunctional furniture is essential for spaces under 50sqm: storage ottomans, extendable dining tables, sofa beds."},

    # ── Style — Modern ────────────────────────────────────────────────────────
    {"id": "st-mod-001", "category": "style_modern",
     "text": "Modern style: clean lines, minimal ornamentation, neutral palette with bold accent, hidden storage, flat-front cabinetry."},
    {"id": "st-mod-002", "category": "style_modern",
     "text": "Modern material palette: concrete, brushed steel, matte lacquer, smoked glass, engineered wood floors."},

    # ── Style — Scandinavian ──────────────────────────────────────────────────
    {"id": "st-sca-001", "category": "style_scandinavian",
     "text": "Scandinavian style: functionality first, natural materials, white or light grey walls, raw oak, hygge warmth through textiles."},
    {"id": "st-sca-002", "category": "style_scandinavian",
     "text": "Scandi palette: white, off-white, light grey, dusty sage, warm caramel, black accents. Natural linen, wool, and sheepskin textures."},

    # ── Style — Luxury ────────────────────────────────────────────────────────
    {"id": "st-lux-001", "category": "style_luxury",
     "text": "Luxury interiors: layered textures, statement lighting, bespoke joinery, rich materials (marble, velvet, brass, walnut)."},
    {"id": "st-lux-002", "category": "style_luxury",
     "text": "In luxury design, empty space is intentional. Do not fill every surface. Negative space signals quality."},

    # ── Storage ───────────────────────────────────────────────────────────────
    {"id": "str-001", "category": "storage",
     "text": "Dead zones above doors and windows are often wasted. Custom joinery to ceiling maximises storage without floor impact."},
    {"id": "str-002", "category": "storage",
     "text": "Built-in storage always beats freestanding in small spaces — it uses every centimetre and reads as architecture, not clutter."},

    # ── Biophilic design ──────────────────────────────────────────────────────
    {"id": "bio-001", "category": "biophilic",
     "text": "Plants improve air quality and wellbeing. One large statement plant per room is more impactful than many small ones."},
    {"id": "bio-002", "category": "biophilic",
     "text": "Natural materials (wood, stone, rattan, jute) ground a space and reduce the clinical feeling of modern interiors."},
]


def seed_knowledge_base():
    """Index all design rules into Qdrant. Safe to call multiple times (upsert)."""
    from ..services.vector_store import index_knowledge
    for rule in DESIGN_RULES:
        index_knowledge(
            rule_id=rule["id"],
            category=rule["category"],
            text=rule["text"],
        )
    return len(DESIGN_RULES)
