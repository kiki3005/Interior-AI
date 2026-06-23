"""
Vector Store Service (Qdrant)
Manages two collections:
  - user_preferences: per-user design taste memory
  - design_knowledge: interior design rules and architectural knowledge base
"""
import uuid
import json
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue,
)
import anthropic

from ..config import settings

_qdrant = QdrantClient(
    url=settings.qdrant_url,
    api_key=settings.qdrant_api_key or None,
)
_anthropic = anthropic.Anthropic(api_key=settings.anthropic_api_key)

VECTOR_SIZE = 1536   # OpenAI ada-002 / Claude embed dimensions
PREF_COLLECTION = settings.qdrant_collection_preferences
KNOW_COLLECTION = settings.qdrant_collection_knowledge


# ── Collection bootstrapping ──────────────────────────────────────────────────

def ensure_collections():
    """Call once at startup to create collections if they don't exist."""
    for name in [PREF_COLLECTION, KNOW_COLLECTION]:
        existing = [c.name for c in _qdrant.get_collections().collections]
        if name not in existing:
            _qdrant.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )


# ── Embedding helper ──────────────────────────────────────────────────────────

def _embed(text: str) -> list[float]:
    """
    Uses OpenAI embeddings (text-embedding-3-small).
    Swap for any other embedding model here.
    """
    import openai
    openai.api_key = settings.openai_api_key
    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )
    return response.data[0].embedding


# ── User preference memory ────────────────────────────────────────────────────

def upsert_user_preference(
    user_id: str,
    preference_type: str,
    value: str,
    weight: float = 1.0,
) -> str:
    """Store or update a user design preference vector. Returns the vector ID."""
    text = f"{preference_type}: {value}"
    vector = _embed(text)
    point_id = str(uuid.uuid4())

    _qdrant.upsert(
        collection_name=PREF_COLLECTION,
        points=[
            PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "user_id": user_id,
                    "preference_type": preference_type,
                    "value": value,
                    "weight": weight,
                },
            )
        ],
    )
    return point_id


def get_user_preferences(user_id: str, top_k: int = 20) -> list[dict]:
    """Retrieve all stored preferences for a user."""
    results = _qdrant.scroll(
        collection_name=PREF_COLLECTION,
        scroll_filter=Filter(
            must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
        ),
        limit=top_k,
        with_payload=True,
        with_vectors=False,
    )
    return [r.payload for r in results[0]]


def find_similar_preferences(
    user_id: str,
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """Find the user's preferences most similar to a query (RAG retrieval)."""
    vector = _embed(query)
    results = _qdrant.search(
        collection_name=PREF_COLLECTION,
        query_vector=vector,
        query_filter=Filter(
            must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
        ),
        limit=top_k,
        with_payload=True,
    )
    return [{"score": r.score, **r.payload} for r in results]


# ── Design knowledge base ─────────────────────────────────────────────────────

def index_knowledge(rule_id: str, category: str, text: str):
    """Index a design rule or knowledge chunk into Qdrant."""
    vector = _embed(text)
    _qdrant.upsert(
        collection_name=KNOW_COLLECTION,
        points=[
            PointStruct(
                id=rule_id,
                vector=vector,
                payload={"category": category, "text": text},
            )
        ],
    )


def retrieve_design_knowledge(query: str, category: Optional[str] = None, top_k: int = 5) -> list[str]:
    """RAG: retrieve relevant design rules for a query."""
    vector = _embed(query)

    query_filter = None
    if category:
        query_filter = Filter(
            must=[FieldCondition(key="category", match=MatchValue(value=category))]
        )

    results = _qdrant.search(
        collection_name=KNOW_COLLECTION,
        query_vector=vector,
        query_filter=query_filter,
        limit=top_k,
        with_payload=True,
    )
    return [r.payload["text"] for r in results]
