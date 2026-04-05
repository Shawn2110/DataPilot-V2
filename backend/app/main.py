"""
main.py — DataPilot v2 FastAPI application.

v2 is a chat-driven copilot. Users type instructions in a chat sidebar,
and the AI agent generates Python code that gets inserted into Jupyter
notebook cells.

Two clients use this backend:
  1. VS Code extension (chat sidebar next to Jupyter notebook)
  2. Next.js web app (Kaggle-like workspace with embedded JupyterLab)
"""

from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import STORAGE_DIR, UPLOADS_DIR, NOTEBOOKS_DIR
from app.routers import chat, upload, kernel


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create storage directories on startup."""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    NOTEBOOKS_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="DataPilot v2",
    description="Chat-driven AI Data Science Copilot",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(kernel.router, prefix="/api", tags=["Kernel"])


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}
