"""
kernel.py — Kernel lifecycle endpoints.

Used by the WEB APP to start/stop Jupyter kernels.
The VS Code extension doesn't use these — it uses VS Code's own Jupyter kernel.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import JUPYTER_SERVER_URL, JUPYTER_TOKEN, NOTEBOOKS_DIR
from app.jupyter.client import JupyterClient
from app.jupyter.notebook_manager import create_blank_notebook
from app.services.session import create_session, get_session, delete_session

router = APIRouter()
jupyter = JupyterClient(JUPYTER_SERVER_URL, JUPYTER_TOKEN)


class StartKernelResponse(BaseModel):
    session_id: str
    kernel_id: str
    notebook_path: str


@router.post("/kernel/start")
async def start_kernel() -> StartKernelResponse:
    """
    Start a new Jupyter kernel and create a blank notebook.

    This creates a complete workspace:
    1. New session (tracks chat history, data, etc.)
    2. New Jupyter kernel (Python process for code execution)
    3. New blank notebook (.ipynb file)
    """
    session = create_session()

    try:
        kernel_id = await jupyter.start_kernel()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not start Jupyter kernel: {e}")

    # Create blank notebook
    notebook_path = str(NOTEBOOKS_DIR / f"{session.session_id}.ipynb")
    create_blank_notebook(notebook_path)

    # Update session
    session.kernel_id = kernel_id
    session.notebook_path = notebook_path

    return StartKernelResponse(
        session_id=session.session_id,
        kernel_id=kernel_id,
        notebook_path=notebook_path,
    )


@router.post("/kernel/stop/{session_id}")
async def stop_kernel(session_id: str):
    """Stop a kernel and clean up the session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.kernel_id:
        try:
            await jupyter.stop_kernel(session.kernel_id)
        except Exception:
            pass  # Kernel might already be stopped

    delete_session(session_id)
    return {"status": "stopped"}


@router.get("/kernel/status/{session_id}")
async def kernel_status(session_id: str):
    """Check if a session's kernel is alive."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "kernel_id": session.kernel_id,
        "has_data": bool(session.data_context),
        "notebook_path": session.notebook_path,
    }
