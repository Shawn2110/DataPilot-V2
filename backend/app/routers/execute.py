"""
execute.py — Code execution endpoint.

Runs Python code in an isolated subprocess and returns stdout/stderr.
No Jupyter kernel needed — just subprocess + exec.
"""

import sys
import subprocess
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ExecuteRequest(BaseModel):
    session_id: str
    code: str


@router.post("/execute")
async def execute_code(req: ExecuteRequest):
    """
    Execute Python code and return output.

    Uses subprocess to run code in an isolated Python process.
    Captures stdout, stderr, and any exceptions.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-c", req.code],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=None,
        )

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "error": result.stderr if result.returncode != 0 else None,
            "result": result.stdout if result.returncode == 0 else None,
        }

    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "", "error": "Execution timed out (30s limit)", "result": None}
    except Exception as e:
        return {"stdout": "", "stderr": "", "error": str(e), "result": None}
