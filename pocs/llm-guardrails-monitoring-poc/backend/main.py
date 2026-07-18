from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from pipeline import PHASES, STEP_META, result_to_dict, run_pipeline

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="XingAI LLM Guardrails & Monitoring POC",
    description="12-step Plan→Build→Validate→Operate demo with XingAI corrections",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class DemoRunRequest(BaseModel):
    user_input: str = Field(
        default="What is the premium refund policy?",
        max_length=2000,
        description="User question or attack probe",
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "poc": "llm-guardrails-monitoring-poc", "steps": 12}


@app.get("/demo/steps")
def list_steps() -> dict:
    return {
        "phases": list(PHASES),
        "steps": [
            {"step": n, "phase": phase, "name": name}
            for n, (phase, name) in STEP_META.items()
        ],
    }


@app.post("/demo/run")
def demo_run(body: DemoRunRequest) -> dict:
    result = run_pipeline(body.user_input)
    return result_to_dict(result)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
