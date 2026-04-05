"""
dataset.py — File upload endpoint.

Handles: POST /upload-dataset

What happens when a user uploads a CSV/Excel file:
  1. Generate a unique dataset ID (UUID)
  2. Create a directory for this dataset
  3. Save the uploaded file
  4. Read it with pandas to extract metadata
  5. Return preview info (shape, columns, first 5 rows)

Multipart form data is the HTTP standard for file uploads.
FastAPI handles parsing it via the `UploadFile` type.
"""

import uuid
import shutil
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException

from config import STORAGE_DIR, MAX_UPLOAD_SIZE_MB

router = APIRouter()


@router.post("/upload-dataset")
async def upload_dataset(file: UploadFile = File(...)):
    """
    Upload a CSV or Excel file.

    Flow:
    1. Validate file type (must be .csv, .xlsx, or .xls)
    2. Save the file to storage/projects/{dataset_id}/
    3. Read it with pandas
    4. Return metadata + preview

    The `File(...)` parameter tells FastAPI this is a required file upload.
    `UploadFile` gives us the file name, content type, and a file-like object.
    """

    # --- Validate file extension ---
    filename = file.filename or "unknown"
    suffix = Path(filename).suffix.lower()

    if suffix not in (".csv", ".xlsx", ".xls"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Use CSV or Excel files."
        )

    # --- Create project directory ---
    # UUID = universally unique identifier (like a random ID)
    dataset_id = str(uuid.uuid4())
    project_dir = STORAGE_DIR / dataset_id
    project_dir.mkdir(parents=True, exist_ok=True)

    # --- Save the uploaded file ---
    file_path = project_dir / filename
    with open(file_path, "wb") as f:
        # Read the uploaded file in chunks (handles large files without loading all into RAM)
        shutil.copyfileobj(file.file, f)

    # --- Check file size ---
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    if file_size_mb > MAX_UPLOAD_SIZE_MB:
        # Clean up and reject
        shutil.rmtree(project_dir)
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({file_size_mb:.1f}MB). Max is {MAX_UPLOAD_SIZE_MB}MB."
        )

    # --- Read with pandas ---
    try:
        if suffix == ".csv":
            df = pd.read_csv(file_path)
        else:
            # openpyxl is the engine that reads .xlsx files
            df = pd.read_excel(file_path, engine="openpyxl")
    except Exception as e:
        shutil.rmtree(project_dir)
        raise HTTPException(status_code=400, detail=f"Could not read file: {str(e)}")

    # Also save as CSV for consistency (the pipeline always works with CSV)
    csv_path = project_dir / "raw_data.csv"
    df.to_csv(csv_path, index=False)

    # --- Return metadata ---
    return {
        "dataset_id": dataset_id,
        "file_path": str(csv_path),
        "shape": list(df.shape),                    # [rows, columns]
        "columns": list(df.columns),                # column names
        "dtypes": df.dtypes.astype(str).to_dict(),  # column data types
        "preview": df.head(5).to_dict(orient="records"),  # first 5 rows as list of dicts
    }
