from __future__ import annotations

import logging
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from agents.orchestrator import DEFAULT_PROMPT, run_pipeline
from config import settings
from database import get_db, init_db
from platform_registry import AGENT_REGISTRY, MCP_REGISTRY
from trace import get_metrics, get_trace

logger = logging.getLogger(__name__)

# Rate limiter — keyed by remote IP
limiter = Limiter(key_func=get_remote_address, default_limits=[])

app = FastAPI(
    title="XingAI Enterprise Agent Platform",
    description="Phase 1 MVP Validation — Multi-Agent POC",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — restricted to configured origins; not "*" in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"


class DemoRunRequest(BaseModel):
    user_input: str = Field(default="", description="Demo prompt", max_length=2000)
    goal: str = Field(default="product_ideation", description="Goal type")

    @field_validator("user_input")
    @classmethod
    def strip_input(cls, v: str) -> str:
        return v.strip()


@app.on_event("startup")
def startup() -> None:
    init_db()
    logger.info(
        "XingAI Multi-Agent Lab started — env=%s openai=%s",
        settings.app_env,
        settings.openai_configured,
    )


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health", tags=["ops"])
def health() -> dict:
    return {
        "status": "ok",
        "openai_configured": settings.openai_configured,
        "model": settings.openai_model,
        "env": settings.app_env,
    }


@app.get("/demo/metrics", tags=["demo"])
def demo_metrics(db: Session = Depends(get_db)) -> dict:
    return get_metrics(db)


@app.get("/demo/agents", tags=["demo"])
def demo_agents() -> dict:
    return {"agents": AGENT_REGISTRY, "mcp": MCP_REGISTRY}


@app.post("/demo/run", tags=["demo"])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
def demo_run(
    request: Request,
    body: DemoRunRequest,
    db: Session = Depends(get_db),
) -> dict:
    prompt = body.user_input or DEFAULT_PROMPT
    logger.info("POST /demo/run — goal=%s input_len=%d", body.goal, len(prompt))
    return run_pipeline(db, prompt)


@app.get("/demo/trace/{request_id}", tags=["demo"])
def demo_trace(request_id: str, db: Session = Depends(get_db)) -> dict:
    if not request_id or len(request_id) > 36:
        raise HTTPException(status_code=400, detail="Invalid request_id")
    trace = get_trace(db, request_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace
