"""
main.py — FastAPI application entry point.

This is the Python server that VS Code spawns as a child process.
It provides REST API endpoints for:
  - Uploading datasets
  - Creating projects and running the ML pipeline
  - Getting results
  - Running predictions

How it works:
  1. VS Code extension starts this server: `python -m uvicorn main:app --port {port}`
  2. The extension makes HTTP calls to these endpoints
  3. The /analyze endpoint streams pipeline events via SSE (Server-Sent Events)

FastAPI is chosen because:
  - Automatic API documentation (visit /docs in browser)
  - Built-in request validation via Pydantic models
  - Async support for long-running ML tasks
  - Very fast (built on Starlette)
"""

import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import dataset, project, predict


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler — runs code on startup and shutdown.

    On startup: create the storage directory for projects.
    On shutdown: cleanup (nothing needed for now).
    """
    # Create storage directory if it doesn't exist
    storage_dir = Path(__file__).parent / "storage" / "projects"
    storage_dir.mkdir(parents=True, exist_ok=True)
    yield
    # Shutdown cleanup (if needed in the future)


app = FastAPI(
    title="DataPilot Sidecar",
    description="AI Data Science Copilot — ML Pipeline Backend",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware — allows the VS Code webview to make requests
# In production you'd restrict this, but for a local sidecar, allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers (each router handles a group of related endpoints)
app.include_router(dataset.router, tags=["Dataset"])
app.include_router(project.router, tags=["Project"])
app.include_router(predict.router, tags=["Predict"])


@app.get("/health")
def health():
    """
    Health check endpoint.

    The VS Code extension polls this endpoint after spawning the server
    to know when it's ready to accept requests. Returns {"status": "ok"}
    when the server is fully started.
    """
    return {"status": "ok"}
