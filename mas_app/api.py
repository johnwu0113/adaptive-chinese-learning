import os
from typing import Any, Dict, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .agents import MASWorkflow

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
HTML_PATH = os.path.join(BASE_DIR, "language-agent-prototype.html")

app = FastAPI(title="MAS Learning Agent Backend", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
workflow = MASWorkflow()


class PipelineRequest(BaseModel):
    turn1: str = Field(..., min_length=1)
    turn2: str = Field(..., min_length=1)


class AdvisoryRequest(BaseModel):
    diagnosis: Dict[str, Any]
    teacher_input: Optional[str] = None


@app.get("/")
def get_index() -> FileResponse:
    return FileResponse(HTML_PATH)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/run-pipeline")
def run_pipeline(payload: PipelineRequest) -> Dict[str, Any]:
    result = workflow.run(payload.turn1, payload.turn2)
    return result


@app.post("/api/plan")
def generate_plan(payload: AdvisoryRequest) -> Dict[str, Any]:
    return workflow.planning_agent.generate(payload.diagnosis, payload.teacher_input)
