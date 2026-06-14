from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from agents.orchestrator import DEFAULT_PROMPT, run_pipeline
from config import settings
from database import get_db, init_db
from platform_registry import AGENT_REGISTRY, MCP_REGISTRY
from trace import get_metrics, get_trace

app = FastAPI(
    title="XingAI Enterprise Agent Platform",
    description="Phase 1 MVP Validation — Multi-Agent POC",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"


class DemoRunRequest(BaseModel):
    user_input: str = Field(default="", description="Demo prompt")
    goal: str = Field(default="product_ideation", description="Goal type")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "openai_configured": settings.openai_configured,
        "model": settings.openai_model,
    }


@app.get("/demo/metrics")
def demo_metrics(db: Session = Depends(get_db)) -> dict:
    return get_metrics(db)


@app.get("/demo/agents")
def demo_agents() -> dict:
    return {"agents": AGENT_REGISTRY, "mcp": MCP_REGISTRY}


@app.post("/demo/run")
def demo_run(body: DemoRunRequest, db: Session = Depends(get_db)) -> dict:
    return run_pipeline(db, body.user_input or DEFAULT_PROMPT)


@app.get("/demo/trace/{request_id}")
def demo_trace(request_id: str, db: Session = Depends(get_db)) -> dict:
    trace = get_trace(db, request_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace
