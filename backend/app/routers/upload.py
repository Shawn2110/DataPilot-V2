"""
upload.py — File upload endpoint.

When a user uploads a CSV/Excel file:
1. Save it to storage/uploads/
2. Read it with pandas to get schema info
3. Update the session's data_context
4. Return preview data to the chat UI
"""

import uuid
import shutil
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException, Form

from app.config import UPLOADS_DIR
from app.services.session import get_session, create_session

router = APIRouter()


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: str | None = Form(None),
):
    """
    Upload a CSV or Excel file.

    Returns schema info (columns, dtypes, shape, preview) and updates
    the session's data_context so the agent knows what data is available.
    """
    filename = file.filename or "data.csv"
    suffix = Path(filename).suffix.lower()

    if suffix not in (".csv", ".xlsx", ".xls"):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files supported.")

    # Get or create session
    if session_id:
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = create_session()

    # Save file
    file_id = str(uuid.uuid4())[:8]
    file_dir = UPLOADS_DIR / session.session_id
    file_dir.mkdir(parents=True, exist_ok=True)
    file_path = file_dir / filename

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Read with pandas
    try:
        if suffix == ".csv":
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path, engine="openpyxl")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read file: {e}")

    # Build data context
    data_info = {
        "variable_name": "df",
        "file_path": str(file_path),
        "file_name": filename,
        "columns": list(df.columns),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "shape": list(df.shape),
        "head": df.head(5).to_dict(orient="records"),
        "missing": df.isnull().sum().to_dict(),
    }

    # Update session
    session.data_context = {"df": data_info}
    session.uploaded_files.append(str(file_path))

    # Create notebook for this session in JupyterLab's working directory
    # JupyterLab serves from backend/storage/, so notebooks go in storage/work/
    from app.jupyter.notebook_manager import create_blank_notebook
    jupyter_nb_dir = UPLOADS_DIR.parent / "work"
    jupyter_nb_dir.mkdir(parents=True, exist_ok=True)
    notebook_path = str(jupyter_nb_dir / f"{session.session_id}.ipynb")
    create_blank_notebook(notebook_path)
    session.notebook_path = notebook_path

    # Generate the load code that will be inserted into the notebook
    load_code = f"""import pandas as pd

df = pd.read_csv('{file_path.as_posix()}')
print(f"Loaded {{df.shape[0]}} rows, {{df.shape[1]}} columns")
df.head()"""

    return {
        "session_id": session.session_id,
        "file_path": str(file_path),
        "data_info": data_info,
        "load_code": load_code,
    }
