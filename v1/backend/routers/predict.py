"""
predict.py — Prediction endpoint.

Handles: POST /projects/{id}/predict

After the pipeline trains a model, users can send new data to get predictions.
This endpoint:
  1. Loads the saved preprocessing pipeline (.joblib)
  2. Loads the saved best model (.joblib)
  3. Preprocesses the input data the same way training data was processed
  4. Runs the model to get predictions
  5. Returns predictions

Why do we need the preprocessing pipeline?
  The model was trained on preprocessed data (scaled, encoded, etc.).
  If we feed raw data directly, the model would give garbage results.
  So we save the EXACT same preprocessing steps and replay them on new data.
"""

from pathlib import Path

import pandas as pd
import joblib
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import STORAGE_DIR

router = APIRouter()


class PredictRequest(BaseModel):
    instances: list[dict]  # List of {feature_name: value} dicts


@router.post("/projects/{project_id}/predict")
async def predict(project_id: str, req: PredictRequest):
    """
    Run prediction using the trained model.

    Example input:
    {
      "instances": [
        {"age": 25, "income": 50000, "city": "Mumbai"},
        {"age": 30, "income": 75000, "city": "Delhi"}
      ]
    }

    Example output:
    {
      "predictions": [0, 1],
      "labels": ["No", "Yes"]  // if classification
    }
    """
    project_dir = STORAGE_DIR / project_id

    # Load saved artifacts
    model_path = project_dir / "best_model.joblib"
    pipeline_path = project_dir / "preprocessing_pipeline.joblib"

    if not model_path.exists():
        raise HTTPException(status_code=404, detail="No trained model found. Run analysis first.")

    if not pipeline_path.exists():
        raise HTTPException(status_code=404, detail="No preprocessing pipeline found.")

    # Load the model and preprocessing pipeline from disk
    # joblib is like pickle but optimized for numpy arrays and scikit-learn objects
    model = joblib.load(model_path)
    preprocessing_pipeline = joblib.load(pipeline_path)

    # Convert input to DataFrame (same format as training data)
    input_df = pd.DataFrame(req.instances)

    # Preprocess using the SAME pipeline that was used during training
    # This ensures the same scaling, encoding, etc.
    try:
        processed = preprocessing_pipeline.transform(input_df)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Preprocessing failed. Ensure input matches training features. Error: {str(e)}"
        )

    # Run prediction
    predictions = model.predict(processed).tolist()

    result = {"predictions": predictions}

    # If the model has predict_proba (classification), include probabilities
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(processed).tolist()
        result["probabilities"] = probabilities

    return result
