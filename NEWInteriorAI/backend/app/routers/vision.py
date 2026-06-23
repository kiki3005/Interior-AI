"""
Vision Router
POST /vision/analyze — run Vision Service on a project's floor plan.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..db import get_db
from ..models.models import Project, Room, DesignResult, User
from ..routers.auth import get_current_user
from ..services.vision import analyze_floor_plan_image

router = APIRouter()


class VisionRequest(BaseModel):
    project_id: str


@router.post("/analyze")
async def analyze(
    body: VisionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(
        Project.id == body.project_id,
        Project.user_id == user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    rooms_hint = [r.name for r in project.rooms] if project.rooms else []
    vision_data = await analyze_floor_plan_image(
        floor_plan_url=project.floor_plan_url,
        rooms_hint=rooms_hint,
        lifestyle=project.lifestyle or {},
    )

    # Upsert Room rows
    for room_data in vision_data.get("rooms", []):
        existing = db.query(Room).filter(
            Room.project_id == project.id,
            Room.name == room_data.get("name"),
        ).first()
        if existing:
            existing.vision_data = room_data
            existing.estimated_sqm = room_data.get("estimated_sqm")
            existing.natural_light = room_data.get("natural_light")
        else:
            room = Room(
                project_id=project.id,
                name=room_data.get("name", "Room"),
                room_type=room_data.get("room_type"),
                estimated_sqm=room_data.get("estimated_sqm"),
                width_m=room_data.get("width_m"),
                length_m=room_data.get("length_m"),
                ceiling_height_m=room_data.get("ceiling_height_m"),
                window_count=room_data.get("window_count", 0),
                door_count=room_data.get("door_count", 0),
                natural_light=room_data.get("natural_light"),
                adjacencies=room_data.get("adjacencies", []),
                vision_data=room_data,
            )
            db.add(room)

    import json
    # Save raw result
    existing_result = db.query(DesignResult).filter(
        DesignResult.project_id == project.id,
        DesignResult.step == 3,
    ).first()
    if existing_result:
        existing_result.content = json.dumps(vision_data)
    else:
        db.add(DesignResult(project_id=project.id, step=3, content=json.dumps(vision_data)))

    db.commit()
    return {"status": "ok", "vision_data": vision_data}
