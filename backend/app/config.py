"""
config.py — v2 configuration.

Two external services:
  - Ollama: local LLM server (free)
  - Jupyter Server: runs kernels and notebooks (for web app path)
"""

import os
from pathlib import Path

# --- Paths ---
BASE_DIR = Path(__file__).parent.parent
STORAGE_DIR = BASE_DIR / "storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"
NOTEBOOKS_DIR = STORAGE_DIR / "notebooks"

# --- Ollama (FREE local LLM) ---
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
LLM_TEMPERATURE = 0

# --- Jupyter Server (for web app path) ---
JUPYTER_SERVER_URL = os.getenv("JUPYTER_SERVER_URL", "http://localhost:8888")
JUPYTER_TOKEN = os.getenv("JUPYTER_TOKEN", "datapilot-dev-token")
