# InteriorAI — Production Backend v2.0

AI-powered interior design platform. Full 10-step pipeline with Vision, Spatial Reasoning, Qdrant RAG, Style Comparison, and Async Rendering.

## Quick Start

```bash
cp .env.example .env
# Fill in your API keys in .env

docker-compose up -d
# API:    http://localhost:8000
# Docs:   http://localhost:8000/docs
# Qdrant: http://localhost:6333/dashboard
```

## Architecture

```
Upload → Vision (Claude) → Spatial Reasoning → Lifestyle Analysis
      → Design Generation (RAG + Qdrant) → Style Comparison (3 variants)
      → Shopping Recommendations → Rendering (DALL-E 3) → Before/After
```

## Key Services

| Service | File | Purpose |
|---|---|---|
| Vision Service | `services/vision.py` | Floor plan image → structured JSON |
| Spatial Engine | `services/spatial.py` | Room graph, traffic flow, zones |
| Vector Store | `services/vector_store.py` | Qdrant: preferences + knowledge RAG |
| Design Knowledge | `knowledge/design_rules.py` | 30+ indexed interior design rules |
| Claude Service | `services/claude.py` | All LLM generation with RAG injection |
| Image Gen | `services/image_gen.py` | DALL-E 3 renders → Cloudinary |
| Celery Worker | `worker.py` | Async pipeline orchestration |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | /auth/register | Create account |
| POST | /auth/login | Get JWT token |
| POST | /projects | Create project |
| POST | /projects/{id}/upload-floor-plan | Upload floor plan image |
| POST | /vision/analyze | Run Vision Service |
| POST | /design/step4-spatial | Spatial reasoning |
| POST | /design/step5-design | Room design brief |
| POST | /style-comparison | Modern + Scandi + Luxury in one call |
| POST | /design/step7-inspiration | Pinterest mood boards |
| POST | /design/step8-shopping | Shopping list |
| POST | /design/step9-visualize | DALL-E prompts |
| POST | /design/step10-before-after | Transformation report |
| POST | /renders/generate | Dispatch render job |
| GET  | /renders/{project_id} | Poll render status |
| POST | /preferences | Save design preference |
| POST | /billing/create-checkout | Stripe checkout |
| POST | /billing/webhook | Stripe webhook |

## Deploy

Push to `main` — GitHub Actions builds, pushes to ECR, and redeploys ECS automatically.
Frontend deploys to Vercel on every push.
