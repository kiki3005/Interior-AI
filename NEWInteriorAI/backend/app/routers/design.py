from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import asyncio

from ..db import get_db
from ..models.models import Project, DesignResult, User
from ..routers.auth import get_current_user
from ..services.claude import (
    analyze_floor_plan,
    generate_spatial_intelligence,
    generate_room_design,
    generate_style_variant,
    generate_inspiration,
    generate_shopping_list,
    generate_visualization_prompts,
    generate_before_after,
)

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class StepRequest(BaseModel):
    project_id: str
    room: Optional[str] = None
    style: Optional[str] = None


class DesignResultResponse(BaseModel):
    id: str
    step: int
    room: Optional[str]
    style: Optional[str]
    content: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_project(project_id: str, user_id, db: Session) -> Project:
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == user_id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _get_or_create_result(
    db: Session, project_id, step: int, room=None, style=None
) -> DesignResult:
    q = db.query(DesignResult).filter(
        DesignResult.project_id == project_id,
        DesignResult.step == step,
    )
    if room:
        q = q.filter(DesignResult.room == room)
    if style:
        q = q.filter(DesignResult.style == style)
    return q.first()


def _save_result(db, project_id, step, content, room=None, style=None) -> DesignResult:
    existing = _get_or_create_result(db, project_id, step, room, style)
    if existing:
        existing.content = content
        db.commit()
        db.refresh(existing)
        return existing
    result = DesignResult(
        project_id=project_id,
        step=step,
        room=room,
        style=style,
        content=content,
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


# ── Get all results for a project ─────────────────────────────────────────────

@router.get("/{project_id}/results", response_model=list[DesignResultResponse])
def get_results(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_project(project_id, user.id, db)
    results = db.query(DesignResult).filter(
        DesignResult.project_id == project_id
    ).all()
    return [
        DesignResultResponse(
            id=str(r.id), step=r.step, room=r.room,
            style=r.style, content=r.content
        ) for r in results
    ]


# ── Step 3: Floor plan analysis ───────────────────────────────────────────────

@router.post("/step3-analyze")
async def step3_analyze(
    body: StepRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _get_project(body.project_id, user.id, db)
    content = await analyze_floor_plan(
        floor_plan_url=project.floor_plan_url,
        lifestyle=project.lifestyle,
        rooms=project.rooms,
    )
    result = _save_result(db, project.id, step=3, content=content)
    return DesignResultResponse(
        id=str(result.id), step=3, room=None, style=None, content=content
    )


# ── Step 4: Spatial intelligence ─────────────────────────────────────────────

@router.post("/step4-spatial")
async def step4_spatial(
    body: StepRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _get_project(body.project_id, user.id, db)
    analysis = _get_or_create_result(db, project.id, step=3)
    content = await generate_spatial_intelligence(
        rooms=project.rooms,
        lifestyle=project.lifestyle,
        analysis=analysis.content if analysis else "",
    )
    result = _save_result(db, project.id, step=4, content=content)
    return DesignResultResponse(
        id=str(result.id), step=4, room=None, style=None, content=content
    )


# ── Step 5: Room design ───────────────────────────────────────────────────────

@router.post("/step5-design")
async def step5_design(
    body: StepRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not body.room:
        raise HTTPException(status_code=400, detail="room is required")
    project = _get_project(body.project_id, user.id, db)
    spatial = _get_or_create_result(db, project.id, step=4)
    content = await generate_room_design(
        room=body.room,
        lifestyle=project.lifestyle,
        project_name=project.name,
        spatial=spatial.content if spatial else "",
    )
    result = _save_result(db, project.id, step=5, content=content, room=body.room)
    return DesignResultResponse(
        id=str(result.id), step=5, room=body.room, style=None, content=content
    )


# ── Step 6: Style variants ────────────────────────────────────────────────────

@router.post("/step6-style")
async def step6_style(
    body: StepRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not body.style:
        raise HTTPException(status_code=400, detail="style is required")
    project = _get_project(body.project_id, user.id, db)
    content = await generate_style_variant(
        style=body.style,
        rooms=project.rooms,
        lifestyle=project.lifestyle,
    )
    result = _save_result(db, project.id, step=6, content=content, style=body.style)
    return DesignResultResponse(
        id=str(result.id), step=6, room=None, style=body.style, content=content
    )


# ── Step 7: Pinterest inspiration ─────────────────────────────────────────────

@router.post("/step7-inspiration")
async def step7_inspiration(
    body: StepRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _get_project(body.project_id, user.id, db)
    content = await generate_inspiration(
        rooms=project.rooms,
        lifestyle=project.lifestyle,
    )
    result = _save_result(db, project.id, step=7, content=content)
    return DesignResultResponse(
        id=str(result.id), step=7, room=None, style=None, content=content
    )


# ── Step 8: Shopping list ─────────────────────────────────────────────────────

@router.post("/step8-shopping")
async def step8_shopping(
    body: StepRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _get_project(body.project_id, user.id, db)
    content = await generate_shopping_list(
        rooms=project.rooms,
        lifestyle=project.lifestyle,
    )
    result = _save_result(db, project.id, step=8, content=content)
    return DesignResultResponse(
        id=str(result.id), step=8, room=None, style=None, content=content
    )


# ── Step 9: Visualization prompts ─────────────────────────────────────────────

@router.post("/step9-visualize")
async def step9_visualize(
    body: StepRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _get_project(body.project_id, user.id, db)
    content = await generate_visualization_prompts(
        rooms=project.rooms,
        lifestyle=project.lifestyle,
    )
    result = _save_result(db, project.id, step=9, content=content)
    return DesignResultResponse(
        id=str(result.id), step=9, room=None, style=None, content=content
    )


# ── Step 10: Before / After ───────────────────────────────────────────────────

@router.post("/step10-before-after")
async def step10_before_after(
    body: StepRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _get_project(body.project_id, user.id, db)
    content = await generate_before_after(
        rooms=project.rooms,
        lifestyle=project.lifestyle,
        project_name=project.name,
    )
    result = _save_result(db, project.id, step=10, content=content)
    return DesignResultResponse(
        id=str(result.id), step=10, room=None, style=None, content=content
    )
