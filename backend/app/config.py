"""
config.py — v2 configuration.

LLM Provider hierarchy:
  1. Cerebras (default) — fastest, free, best code accuracy
  2. Groq (fallback)    — fast, free, more model variety
  3. Ollama (offline)   — local, free, needs RAM

Users set their provider + API key via environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file FIRST so all os.getenv() calls below pick up the values
load_dotenv(Path(__file__).parent.parent / ".env")

# --- Paths ---
BASE_DIR = Path(__file__).parent.parent
STORAGE_DIR = BASE_DIR / "storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"
NOTEBOOKS_DIR = STORAGE_DIR / "notebooks"

# --- LLM Provider ---
# Options: "cerebras" (default), "groq", "ollama"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "cerebras")

# Cerebras (default — free, 2500 tok/s, best code accuracy)
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")
CEREBRAS_MODEL = os.getenv("CEREBRAS_MODEL", "llama3.1-8b")

# Groq (fallback — free, 500 tok/s, more model variety)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Ollama (offline — local, no API key needed)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")

LLM_TEMPERATURE = 0

# --- Jupyter Server (for web app path) ---
JUPYTER_SERVER_URL = os.getenv("JUPYTER_SERVER_URL", "http://localhost:8888")
JUPYTER_TOKEN = os.getenv("JUPYTER_TOKEN", "datapilot-dev-token")
