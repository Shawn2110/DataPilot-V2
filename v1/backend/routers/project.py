"""
project.py — Project creation and analysis endpoints.

Handles:
  POST /projects/create    — Create a project and configure the pipeline
  POST /projects/{id}/analyze — Run the AI agent pipeline (SSE stream)
  GET  /projects/{id}/results — Get final results

SSE (Server-Sent Events) explained:
  Normal HTTP: client sends request → server sends ONE response → done.
  SSE: client sends request → server sends MANY events over time → done.

  Each event looks like:
    data: {"step": "eda", "status": "running"}\n\n

  The client reads these line-by-line as they arrive. This gives us
  real-time progress updates without WebSockets (which are more complex).

  SSE is one-directional (server → client), which is perfect for us
  because we only need to send pipeline progress TO the UI.
"""

import json
import asyncio
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from config import STORAGE_DIR
from pipeline.state import PipelineState
from agent.react_agent import run_pipeline

router = APIRouter()


# --- Request/Response models ---
# Pydantic models validate incoming JSON automatically.
# If someone sends {"task_type": "invalid"}, FastAPI returns a 422 error.

class CreateProjectRequest(BaseModel):
    dataset_path: str
    target_column: str | None = None
    task_type: str | None = None  # "classification" or "regression"


class CreateProjectResponse(BaseModel):
    project_id: str
    status: str


# --- In-memory store for pipeline results ---
# For MVP, we store results in memory. A production app would use a database.
# Key = project_id, Value = PipelineState
pipeline_states: dict[str, PipelineState] = {}


@router.post("/projects/create")
async def create_project(req: CreateProjectRequest) -> CreateProjectResponse:
    """
    Create a project from an uploaded dataset.

    This just stores the configuration — it doesn't run the pipeline yet.
    The user triggers analysis separately via /analyze.

    Why separate create and analyze?
    So the user can preview the data, pick a target column, and choose
    the task type BEFORE running the expensive ML pipeline.
    """
    dataset_path = Path(req.dataset_path)
    if not dataset_path.exists():
        raise HTTPException(status_code=404, detail="Dataset not found")

    # The project_id is the directory name from the upload step
    project_id = dataset_path.parent.name

    # Load the dataset into a PipelineState object
    df = pd.read_csv(dataset_path)

    state = PipelineState(
        project_id=project_id,
        project_dir=dataset_path.parent,
        raw_df=df,
        target_column=req.target_column,
        task_type=req.task_type,
    )

    pipeline_states[project_id] = state

    return CreateProjectResponse(project_id=project_id, status="created")


@router.post("/projects/{project_id}/analyze")
async def analyze_project(project_id: str):
    """
    Run the full ML pipeline and stream progress via SSE.

    How SSE streaming works here:
    1. We create an asyncio.Queue (a thread-safe message queue)
    2. The pipeline runs in a background task, pushing events to the queue
    3. The event_generator reads from the queue and yields SSE events
    4. EventSourceResponse sends each yielded event to the client

    asyncio.Queue is like a conveyor belt:
      - Producer (pipeline) puts items on the belt
      - Consumer (SSE response) takes items off the belt
      - If the belt is empty, the consumer waits
    """
    if project_id not in pipeline_states:
        raise HTTPException(status_code=404, detail="Project not found")

    state = pipeline_states[project_id]
    queue: asyncio.Queue = asyncio.Queue()

    async def on_event(event: dict):
        """Callback that the agent calls whenever something happens."""
        await queue.put(event)

    async def run_in_background():
        """Run the pipeline in a background task."""
        try:
            await run_pipeline(state, on_event)
            await queue.put(None)  # Sentinel value = "we're done"
        except Exception as e:
            await queue.put({"type": "error", "message": str(e)})
            await queue.put(None)

    # Start the pipeline in the background
    # asyncio.create_task is like spawning a thread, but for async code
    asyncio.create_task(run_in_background())

    async def event_generator():
        """
        Generator that yields SSE events.

        This function runs in a loop, waiting for events from the queue.
        Each event is serialized to JSON and sent as an SSE "data:" line.
        When it receives None (sentinel), it stops.
        """
        while True:
            event = await queue.get()
            if event is None:
                break
            yield {
                "event": "pipeline",
                "data": json.dumps(event, default=str),
            }

    return EventSourceResponse(event_generator())


@router.get("/projects/{project_id}/results")
async def get_results(project_id: str):
    """
    Get the final pipeline results.

    Called after the SSE stream ends. Returns all the accumulated results
    from the pipeline run — metrics, charts, SHAP values, etc.
    """
    if project_id not in pipeline_states:
        raise HTTPException(status_code=404, detail="Project not found")

    state = pipeline_states[project_id]

    return {
        "status": state.status,
        "task_type": state.task_type,
        "target_column": state.target_column,
        "profile": state.profile,
        "eda": state.eda_results,
        "preprocessing": state.preprocessing_summary,
        "model_comparison": state.cv_results,
        "best_model": state.best_model_name,
        "evaluation": state.test_metrics,
        "explainability": state.feature_importance,
        "report_path": str(state.report_path) if state.report_path else None,
        "model_path": str(state.model_path) if state.model_path else None,
    }
