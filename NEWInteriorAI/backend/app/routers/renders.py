"""
Render Jobs Router
POST /renders/generate — dispatch a DALL-E 3 render job via Celery.
GET  /renders/{project_id} — list all render jobs and their status/URLs.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from ..db import get_db
from ..models.models import Project, RenderJob, User
from ..routers.auth import get_current_user

router = APIRouter()


class RenderRequest(BaseModel):
    project_id: str
    room: str
    style: str
    prompt: str


class RenderJobResponse(BaseModel):
    id: str
    room_id: Optional[str]
    style: Optional[str]
    status: str
    image_url: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]


@router.post("/generate", status_code=202)
def dispatch_render(
    body: RenderRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(
        Project.id == body.project_id,
        Project.user_id == user.id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    job = RenderJob(
        project_id=project.id,
        style=body.style,
        prompt=body.prompt,
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Dispatch to Celery
    from ..worker import run_render_jobs
    task = run_render_jobs.delay(body.project_id, str(user.id))
    job.celery_task_id = task.id
    db.commit()

    return {"job_id": str(job.id), "task_id": task.id, "status": "queued"}


@router.get("/{project_id}", response_model=list[RenderJobResponse])
def list_renders(
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

    jobs = db.query(RenderJob).filter(RenderJob.project_id == project_id).all()
    return [
        RenderJobResponse(
            id=str(j.id),
            room_id=str(j.room_id) if j.room_id else None,
            style=j.style,
            status=j.status,
            image_url=j.image_url,
            created_at=j.created_at,
            completed_at=j.completed_at,
        ) for j in jobs
    ]
