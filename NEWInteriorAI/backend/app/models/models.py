import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Text, Boolean,
    DateTime, ForeignKey, JSON, ARRAY, Enum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..db import Base


# ── Users ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id                     = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email                  = Column(String, unique=True, nullable=False, index=True)
    hashed_password        = Column(String, nullable=False)
    full_name              = Column(String, nullable=True)
    plan                   = Column(String, default="free")   # free | pro | premium
    stripe_customer_id     = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    is_active              = Column(Boolean, default=True)
    created_at             = Column(DateTime, default=datetime.utcnow)

    projects    = relationship("Project", back_populates="user", cascade="all, delete")
    preferences = relationship("UserPreference", back_populates="user", cascade="all, delete")


# ── Projects ──────────────────────────────────────────────────────────────────

class Project(Base):
    __tablename__ = "projects"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id         = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    name            = Column(String, nullable=False)
    lifestyle       = Column(JSON, default={})
    floor_plan_url  = Column(String, nullable=True)
    status          = Column(String, default="draft")  # draft|processing|complete|failed
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user              = relationship("User", back_populates="projects")
    rooms             = relationship("Room", back_populates="project", cascade="all, delete")
    render_jobs       = relationship("RenderJob", back_populates="project", cascade="all, delete")
    style_comparisons = relationship("StyleComparison", back_populates="project", cascade="all, delete")
    design_results    = relationship("DesignResult", back_populates="project", cascade="all, delete")


# ── Rooms ─────────────────────────────────────────────────────────────────────

class Room(Base):
    __tablename__ = "rooms"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id           = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    name                 = Column(String, nullable=False)          # "Living Room"
    room_type            = Column(String, nullable=True)           # living|bedroom|kitchen|…
    estimated_sqm        = Column(Float, nullable=True)
    width_m              = Column(Float, nullable=True)
    length_m             = Column(Float, nullable=True)
    ceiling_height_m     = Column(Float, nullable=True)
    window_count         = Column(Integer, default=0)
    door_count           = Column(Integer, default=0)
    natural_light        = Column(String, nullable=True)           # low|medium|high
    adjacencies          = Column(ARRAY(String), default=[])       # ["kitchen","hallway"]
    vision_data          = Column(JSON, default={})                # raw vision output
    spatial_data         = Column(JSON, default={})                # spatial reasoning output
    design_brief         = Column(Text, nullable=True)             # step-5 output
    created_at           = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="rooms")


# ── Design Results (steps 3-10) ───────────────────────────────────────────────

class DesignResult(Base):
    __tablename__ = "design_results"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    step       = Column(Integer, nullable=False)
    room       = Column(String, nullable=True)
    style      = Column(String, nullable=True)
    content    = Column(Text, nullable=False)
    meta       = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="design_results")


# ── Render Jobs ───────────────────────────────────────────────────────────────

class RenderJob(Base):
    __tablename__ = "render_jobs"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id     = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    room_id        = Column(UUID(as_uuid=True), ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True)
    style          = Column(String, nullable=True)
    prompt         = Column(Text, nullable=False)
    status         = Column(String, default="pending")  # pending|running|done|failed
    image_url      = Column(String, nullable=True)       # final Cloudinary/S3 URL
    provider       = Column(String, default="dalle3")    # dalle3|sdxl|midjourney
    celery_task_id = Column(String, nullable=True)
    error          = Column(Text, nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)
    completed_at   = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="render_jobs")


# ── Style Comparisons ─────────────────────────────────────────────────────────

class StyleComparison(Base):
    __tablename__ = "style_comparisons"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id      = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    room            = Column(String, nullable=True)
    modern_content  = Column(Text, nullable=True)
    scandi_content  = Column(Text, nullable=True)
    luxury_content  = Column(Text, nullable=True)
    modern_image    = Column(String, nullable=True)   # render URL
    scandi_image    = Column(String, nullable=True)
    luxury_image    = Column(String, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="style_comparisons")


# ── User Preferences (also mirrored into Qdrant) ──────────────────────────────

class UserPreference(Base):
    __tablename__ = "user_preferences"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id          = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    preference_type  = Column(String, nullable=False)  # style|color|material|furniture|budget
    value            = Column(String, nullable=False)
    weight           = Column(Float, default=1.0)      # increases on repeated selection
    qdrant_vector_id = Column(String, nullable=True)   # ID in Qdrant collection
    created_at       = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="preferences")
