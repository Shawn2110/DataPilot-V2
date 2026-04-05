"""
session.py — Session management for chat copilot.

Each user session tracks:
  - Chat history (what the user asked, what the agent responded)
  - Kernel ID (the Jupyter kernel running their code)
  - Notebook path (the .ipynb file being worked on)
  - Data context (what DataFrames are loaded, their schemas)
  - Uploaded files

Sessions are stored in-memory (dict) for MVP.
"""

import uuid
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Session:
    session_id: str
    kernel_id: str | None = None
    notebook_path: str | None = None
    uploaded_files: list[str] = field(default_factory=list)
    data_context: dict = field(default_factory=dict)
    # data_context example:
    # {
    #   "df": {
    #     "columns": ["age", "income", "city"],
    #     "dtypes": {"age": "int64", "income": "float64", "city": "object"},
    #     "shape": [1000, 3],
    #     "head": [{"age": 25, "income": 50000, "city": "Mumbai"}, ...]
    #   }
    # }
    chat_history: list[dict] = field(default_factory=list)
    # chat_history: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]


# In-memory session store
_sessions: dict[str, Session] = {}


def create_session() -> Session:
    """Create a new session with a unique ID."""
    session_id = str(uuid.uuid4())[:8]
    session = Session(session_id=session_id)
    _sessions[session_id] = session
    return session


def get_session(session_id: str) -> Session | None:
    """Get an existing session by ID."""
    return _sessions.get(session_id)


def delete_session(session_id: str) -> None:
    """Remove a session."""
    _sessions.pop(session_id, None)
