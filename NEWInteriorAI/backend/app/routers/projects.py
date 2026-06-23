from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import uuid

from ..db import get_db
from ..models.models import Project, User
from ..routers.auth import get_current_user
from ..services.storage import upload_floor_plan

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class LifestyleProfile(BaseModel):
    residents: int = 1
    children: int = 0
    pets: bool = False
    wfh: bool = False
    hobbies: list[str] = []
    styles: list[str] = []
    colors: list[str] = []
    budget: str = "mid"   # low | mid | premium | luxury


class CreateProjectRequest(BaseModel):
    name: str
    rooms: list[str] = []
    lifestyle: LifestyleProfile = LifestyleProfile()


class ProjectResponse(BaseModel):
    id: str
    name: str
    rooms: list[str]
    lifestyle: dict
    floor_plan_url: Optional[str]
    status: str


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(
    body: CreateProjectRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = Project(
        user_id=user.id,
        name=body.name,
        rooms=body.rooms,
        lifestyle=body.lifestyle.model_dump(),
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return _to_response(project)


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    projects = db.query(Project).filter(Project.user_id == user.id).all()
    return [_to_response(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _get_or_404(project_id, user.id, db)
    return _to_response(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    body: CreateProjectRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _get_or_404(project_id, user.id, db)
    project.name = body.name
    project.rooms = body.rooms
    project.lifestyle = body.lifestyle.model_dump()
    db.commit()
    db.refresh(project)
    return _to_response(project)


@router.post("/{project_id}/upload-floor-plan", response_model=ProjectResponse)
async def upload_floor_plan_route(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _get_or_404(project_id, user.id, db)

    contents = await file.read()
    url = upload_floor_plan(
        file_bytes=contents,
        filename=f"{project_id}/{file.filename}",
        content_type=file.content_type,
    )

    project.floor_plan_url = url
    db.commit()
    db.refresh(project)
    return _to_response(project)


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = _get_or_404(project_id, user.id, db)
    db.delete(project)
    db.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_or_404(project_id: str, user_id, db: Session) -> Project:
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == user_id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _to_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        rooms=project.rooms or [],
        lifestyle=project.lifestyle or {},
        floor_plan_url=project.floor_plan_url,
        status=project.status,
    )
