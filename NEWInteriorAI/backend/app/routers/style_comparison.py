"""
Style Comparison Router
Generates Modern, Scandinavian, and Luxury variants for a room in one call.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..db import get_db
from ..models.models import Project, StyleComparison, DesignResult, User
from ..routers.auth import get_current_user
from ..services.claude import generate_style_comparison

router = APIRouter()


class StyleCompareRequest(BaseModel):
    project_id: str
    room: str


class StyleCompareResponse(BaseModel):
    room: str
    modern: str
    scandinavian: str
    luxury: str


@router.post("", response_model=StyleCompareResponse)
async def compare_styles(
    body: StyleCompareRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(
        Project.id == body.project_id,
        Project.user_id == user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    spatial_result = db.query(DesignResult).filter(
        DesignResult.project_id == project.id,
        DesignResult.step == 4,
    ).first()
    spatial = spatial_result.content if spatial_result else ""

    variants = await generate_style_comparison(
        room=body.room,
        lifestyle=project.lifestyle or {},
        spatial=spatial,
        user_id=str(user.id),
    )

    # Persist
    existing = db.query(StyleComparison).filter(
        StyleComparison.project_id == project.id,
        StyleComparison.room == body.room,
    ).first()
    if existing:
        existing.modern_content = variants["modern"]
        existing.scandi_content = variants["scandinavian"]
        existing.luxury_content = variants["luxury"]
    else:
        db.add(StyleComparison(
            project_id=project.id,
            room=body.room,
            modern_content=variants["modern"],
            scandi_content=variants["scandinavian"],
            luxury_content=variants["luxury"],
        ))
    db.commit()

    return StyleCompareResponse(
        room=body.room,
        modern=variants["modern"],
        scandinavian=variants["scandinavian"],
        luxury=variants["luxury"],
    )


@router.get("/{project_id}", response_model=list[StyleCompareResponse])
def list_comparisons(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    comparisons = db.query(StyleComparison).filter(
        StyleComparison.project_id == project_id
    ).all()
    return [
        StyleCompareResponse(
            room=c.room or "",
            modern=c.modern_content or "",
            scandinavian=c.scandi_content or "",
            luxury=c.luxury_content or "",
        ) for c in comparisons
    ]
