from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import settings
from .db import engine
from .models.models import Base
from .routers import auth, projects, design, billing, vision, style_comparison, preferences, renders


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    try:
        from .services.vector_store import ensure_collections
        ensure_collections()
        from .knowledge.design_rules import seed_knowledge_base
        count = seed_knowledge_base()
        print(f"[InteriorAI] Qdrant ready. {count} design rules indexed.")
    except Exception as e:
        print(f"[InteriorAI] Qdrant/knowledge init skipped: {e}")
    yield


app = FastAPI(
    title="InteriorAI API",
    version="2.0.0",
    description="Production-grade AI interior design platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,             prefix="/auth",             tags=["auth"])
app.include_router(projects.router,         prefix="/projects",         tags=["projects"])
app.include_router(vision.router,           prefix="/vision",           tags=["vision"])
app.include_router(design.router,           prefix="/design",           tags=["design"])
app.include_router(style_comparison.router, prefix="/style-comparison", tags=["styles"])
app.include_router(preferences.router,      prefix="/preferences",      tags=["preferences"])
app.include_router(renders.router,          prefix="/renders",          tags=["renders"])
app.include_router(billing.router,          prefix="/billing",          tags=["billing"])


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "version": "2.0.0", "env": settings.environment}
