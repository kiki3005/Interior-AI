"""
User Preferences Router
Stores and retrieves design preferences — mirrored into Qdrant for RAG.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..db import get_db
from ..models.models import UserPreference, User
from ..routers.auth import get_current_user
from ..services.vector_store import upsert_user_preference, get_user_preferences

router = APIRouter()


class PreferenceIn(BaseModel):
    preference_type: str   # style | color | material | furniture | budget
    value: str
    weight: float = 1.0


class PreferenceOut(BaseModel):
    id: str
    preference_type: str
    value: str
    weight: float


@router.post("", response_model=PreferenceOut, status_code=201)
def add_preference(
    body: PreferenceIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Check if already exists — if so, increase weight
    existing = db.query(UserPreference).filter(
        UserPreference.user_id == user.id,
        UserPreference.preference_type == body.preference_type,
        UserPreference.value == body.value,
    ).first()

    if existing:
        existing.weight = min(existing.weight + 0.5, 5.0)  # cap at 5
        db.commit()
        return PreferenceOut(
            id=str(existing.id),
            preference_type=existing.preference_type,
            value=existing.value,
            weight=existing.weight,
        )

    # Upsert into Qdrant
    try:
        vector_id = upsert_user_preference(
            user_id=str(user.id),
            preference_type=body.preference_type,
            value=body.value,
            weight=body.weight,
        )
    except Exception:
        vector_id = None

    pref = UserPreference(
        user_id=user.id,
        preference_type=body.preference_type,
        value=body.value,
        weight=body.weight,
        qdrant_vector_id=vector_id,
    )
    db.add(pref)
    db.commit()
    db.refresh(pref)

    return PreferenceOut(
        id=str(pref.id),
        preference_type=pref.preference_type,
        value=pref.value,
        weight=pref.weight,
    )


@router.get("", response_model=list[PreferenceOut])
def list_preferences(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    prefs = db.query(UserPreference).filter(
        UserPreference.user_id == user.id
    ).order_by(UserPreference.weight.desc()).all()
    return [
        PreferenceOut(
            id=str(p.id),
            preference_type=p.preference_type,
            value=p.value,
            weight=p.weight,
        ) for p in prefs
    ]


@router.delete("/{pref_id}", status_code=204)
def delete_preference(
    pref_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pref = db.query(UserPreference).filter(
        UserPreference.id == pref_id,
        UserPreference.user_id == user.id,
    ).first()
    if not pref:
        raise HTTPException(status_code=404, detail="Preference not found")
    db.delete(pref)
    db.commit()
