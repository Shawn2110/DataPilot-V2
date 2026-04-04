"""
config.py — Application configuration.

Centralizes all configuration values.

We use Ollama for the LLM — it's completely FREE and runs locally.
No API keys, no cloud costs. You just install Ollama and pull a model.

Setup (one-time):
  1. Install Ollama: https://ollama.com/download
  2. Pull a model: ollama pull llama3.1
  3. Ollama runs a local server at http://localhost:11434

LangChain talks to Ollama via langchain-ollama integration.
"""

import os
from pathlib import Path


# --- Paths ---
BASE_DIR = Path(__file__).parent
STORAGE_DIR = BASE_DIR / "storage" / "projects"

# --- LLM Settings (Ollama — FREE, local) ---
# Ollama runs a local server at this URL
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Model to use — options (all free):
#   "llama3.1"      — Meta's Llama 3.1 8B (good balance of speed + quality)
#   "llama3.1:70b"  — Larger, smarter, needs more RAM (~40GB)
#   "mistral"       — Mistral 7B (fast, good reasoning)
#   "codellama"     — Optimized for code tasks
#   "qwen2.5"       — Alibaba's model (strong at structured tasks)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")

# Temperature 0 = deterministic (same input → same output, no randomness)
LLM_TEMPERATURE = 0

# --- ML Settings ---
CV_FOLDS = 5            # Number of cross-validation folds
TEST_SIZE = 0.2         # 20% of data held out for testing
RANDOM_STATE = 42       # For reproducibility
MAX_SHAP_SAMPLES = 100  # SHAP is slow — sample this many rows max
MAX_UPLOAD_SIZE_MB = 100  # Reject uploads larger than this
