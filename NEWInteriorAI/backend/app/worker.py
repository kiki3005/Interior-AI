"""
Celery Worker
Async task queue for long-running AI pipeline jobs.
Each step of the 10-step pipeline can be dispatched as a background task.
"""
import asyncio
from datetime import datetime

from celery import Celery
from sqlalchemy.orm import Session

from .config import settings
from .db import SessionLocal
from .models.models import Project, Room, DesignResult, RenderJob, StyleComparison

celery_app = Celery(
    "interiorai",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)


def _run(coro):
    """Run an async coroutine from a sync Celery task."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ── Full pipeline ─────────────────────────────────────────────────────────────

@celery_app.task(bind=True, name="run_full_pipeline")
def run_full_pipeline(self, project_id: str, user_id: str):
    """
    Orchestrates all pipeline steps in sequence:
    Vision → Spatial → Lifestyle → Design (per room) → Recommendations → Rendering
    """
    db: Session = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"error": "Project not found"}

        project.status = "processing"
        db.commit()

        # Step 3: Vision analysis
        self.update_state(state="PROGRESS", meta={"step": 3, "label": "Analysing floor plan"})
        run_vision_analysis.delay(project_id, user_id)

    except Exception as e:
        db.query(Project).filter(Project.id == project_id).update({"status": "failed"})
        db.commit()
        raise
    finally:
        db.close()


# ── Step 3: Vision ────────────────────────────────────────────────────────────

@celery_app.task(bind=True, name="run_vision_analysis")
def run_vision_analysis(self, project_id: str, user_id: str):
    from .services.vision import analyze_floor_plan_image

    db: Session = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        lifestyle = project.lifestyle or {}
        rooms_hint = [r.name for r in project.rooms] if project.rooms else []

        vision_data = _run(analyze_floor_plan_image(
            floor_plan_url=project.floor_plan_url,
            rooms_hint=rooms_hint,
            lifestyle=lifestyle,
        ))

        # Upsert Room rows from vision data
        for room_data in vision_data.get("rooms", []):
            existing = db.query(Room).filter(
                Room.project_id == project_id,
                Room.name == room_data.get("name"),
            ).first()
            if existing:
                existing.vision_data = room_data
                existing.estimated_sqm = room_data.get("estimated_sqm")
                existing.natural_light = room_data.get("natural_light")
                existing.window_count = room_data.get("window_count", 0)
            else:
                room = Room(
                    project_id=project_id,
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
        _save_result(db, project_id, step=3, content=json.dumps(vision_data))
        db.commit()

        # Chain to spatial reasoning
        run_spatial_reasoning_task.delay(project_id, user_id)
        return {"status": "done", "step": 3}
    finally:
        db.close()


# ── Step 4: Spatial ───────────────────────────────────────────────────────────

@celery_app.task(bind=True, name="run_spatial_reasoning_task")
def run_spatial_reasoning_task(self, project_id: str, user_id: str):
    from .services.spatial import run_spatial_reasoning

    db: Session = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        vision_result = db.query(DesignResult).filter(
            DesignResult.project_id == project_id,
            DesignResult.step == 3,
        ).first()

        import json
        vision_data = json.loads(vision_result.content) if vision_result else {}
        spatial_data = _run(run_spatial_reasoning(vision_data, project.lifestyle or {}))

        # Update all rooms with spatial data
        for room in project.rooms:
            room.spatial_data = spatial_data
        _save_result(db, project_id, step=4, content=json.dumps(spatial_data))
        db.commit()

        # Chain to design generation
        run_design_all_rooms.delay(project_id, user_id)
        return {"status": "done", "step": 4}
    finally:
        db.close()


# ── Step 5: Design all rooms ──────────────────────────────────────────────────

@celery_app.task(bind=True, name="run_design_all_rooms")
def run_design_all_rooms(self, project_id: str, user_id: str):
    from .services.claude import generate_room_design

    db: Session = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        spatial_result = db.query(DesignResult).filter(
            DesignResult.project_id == project_id,
            DesignResult.step == 4,
        ).first()
        spatial = spatial_result.content if spatial_result else ""

        for room in project.rooms:
            content = _run(generate_room_design(
                room=room.name,
                lifestyle=project.lifestyle or {},
                project_name=project.name,
                spatial=spatial,
                user_id=user_id,
            ))
            room.design_brief = content
            _save_result(db, project_id, step=5, content=content, room=room.name)

        db.commit()

        # Chain to style comparison
        run_style_comparison_task.delay(project_id, user_id)
        return {"status": "done", "step": 5}
    finally:
        db.close()


# ── Step 6: Style comparison ──────────────────────────────────────────────────

@celery_app.task(bind=True, name="run_style_comparison_task")
def run_style_comparison_task(self, project_id: str, user_id: str):
    from .services.claude import generate_style_comparison

    db: Session = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        spatial_result = db.query(DesignResult).filter(
            DesignResult.project_id == project_id,
            DesignResult.step == 4,
        ).first()
        spatial = spatial_result.content if spatial_result else ""

        for room in project.rooms:
            variants = _run(generate_style_comparison(
                room=room.name,
                lifestyle=project.lifestyle or {},
                spatial=spatial,
                user_id=user_id,
            ))
            comparison = StyleComparison(
                project_id=project_id,
                room=room.name,
                modern_content=variants.get("modern"),
                scandi_content=variants.get("scandinavian"),
                luxury_content=variants.get("luxury"),
            )
            db.add(comparison)

        db.commit()

        # Chain to rendering
        run_render_jobs.delay(project_id, user_id)
        return {"status": "done", "step": 6}
    finally:
        db.close()


# ── Step 9: Render jobs ───────────────────────────────────────────────────────

@celery_app.task(bind=True, name="run_render_jobs")
def run_render_jobs(self, project_id: str, user_id: str):
    from .services.claude import generate_visualization_prompts
    from .services.image_gen import generate_room_render

    db: Session = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        rooms = [r.name for r in project.rooms]

        # Generate prompts for all rooms
        prompts_text = _run(generate_visualization_prompts(rooms, project.lifestyle or {}))

        for room in project.rooms:
            # Create a render job per room
            job = RenderJob(
                project_id=project_id,
                room_id=room.id,
                style=project.lifestyle.get("styles", ["Modern"])[0] if project.lifestyle else "Modern",
                prompt=f"Professional interior photography, {room.name}, modern style, wide-angle, photorealistic",
                status="running",
            )
            db.add(job)
            db.flush()

            try:
                image_url = _run(generate_room_render(
                    prompt=job.prompt,
                    project_id=project_id,
                    room=room.name,
                    style=job.style or "modern",
                ))
                job.image_url = image_url
                job.status = "done"
                job.completed_at = datetime.utcnow()
            except Exception as e:
                job.status = "failed"
                job.error = str(e)

        project.status = "complete"
        db.commit()
        return {"status": "done", "step": 9}
    finally:
        db.close()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _save_result(db, project_id, step, content, room=None, style=None):
    existing = db.query(DesignResult).filter(
        DesignResult.project_id == project_id,
        DesignResult.step == step,
        DesignResult.room == room,
        DesignResult.style == style,
    ).first()
    if existing:
        existing.content = content
    else:
        db.add(DesignResult(
            project_id=project_id,
            step=step,
            content=content,
            room=room,
            style=style,
        ))
