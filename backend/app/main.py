from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.deps import verify_supabase_jwt
from app.routers import analyses, health, webhooks


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


app = FastAPI(
    title="Dependency Map API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(webhooks.router)
app.include_router(analyses.router)


@app.get("/v1/dashboard")
def dashboard(user: dict = Depends(verify_supabase_jwt)) -> dict:
    return {
        "user_id": user["sub"],
        "email": user.get("email"),
        "organizations": [],
        "message": "Wire organizations query to Supabase in Phase 1+.",
    }
