# DataPilot Architecture

## System Overview

DataPilot is a VS Code extension with three layers that communicate via HTTP and message passing:

```
+-----------------------------------------------------------------------+
|                         VS Code Window                                 |
|                                                                        |
|  +---------------------------+    +--------------------------------+   |
|  |   Extension Host (Node)   |    |   Webview Panel (Browser)      |   |
|  |                           |    |                                |   |
|  |  extension.ts             |    |   React App (Vite + Tailwind)  |   |
|  |    |                      |    |                                |   |
|  |    +-- SidecarManager ----|----+-> spawns Python process        |   |
|  |    |     (lifecycle)      |    |                                |   |
|  |    |                      |    |   UploadPanel                  |   |
|  |    +-- SidecarClient -----|----+-> PipelineProgress             |   |
|  |    |     (HTTP calls)     |    |   DataProfileView              |   |
|  |    |                      |    |   EDACharts                    |   |
|  |    +-- WebviewProvider ---|<-->|   ModelComparison              |   |
|  |    |     (panel mgmt)     |    |   ShapExplainer                |   |
|  |    |                      |    |   AgentLog                     |   |
|  |    +-- MessageHandler ----|<-->|                                |   |
|  |          (bridge)         |    |   postMessage() <-> onMessage  |   |
|  +---------------------------+    +--------------------------------+   |
|              |                                                         |
|              | HTTP / SSE (localhost:{dynamic_port})                    |
|              |                                                         |
|  +-----------v-------------------------------------------------+       |
|  |           Python Sidecar (FastAPI + Uvicorn)                |       |
|  |                                                             |       |
|  |  main.py ── FastAPI app                                     |       |
|  |    |                                                        |       |
|  |    +-- /health              GET  (health check)             |       |
|  |    +-- /upload-dataset      POST (file upload)              |       |
|  |    +-- /projects/create     POST (create project)           |       |
|  |    +-- /projects/{id}/analyze  POST (SSE stream)            |       |
|  |    +-- /projects/{id}/results  GET  (final results)         |       |
|  |    +-- /projects/{id}/predict  POST (inference)             |       |
|  |                                                             |       |
|  |  agent/react_agent.py ── LangGraph ReAct Agent              |       |
|  |    |                                                        |       |
|  |    +-- ChatOllama (Llama 3.1 via Ollama, FREE)              |       |
|  |    |                                                        |       |
|  |    +-- 8 Pipeline Tools (shared PipelineState)              |       |
|  |         |                                                   |       |
|  |         +-- detect_problem                                  |       |
|  |         +-- profile_data                                    |       |
|  |         +-- run_eda                                         |       |
|  |         +-- preprocess_data                                 |       |
|  |         +-- engineer_features                               |       |
|  |         +-- train_models                                    |       |
|  |         +-- evaluate_model                                  |       |
|  |         +-- explain_model                                   |       |
|  +---------------------------------------------------------+   |       |
|                          |                                     |       |
|                          v                                     |       |
|  +-------------------+  +------------------+  +------------+   |       |
|  | Ollama Server     |  | storage/projects |  | .joblib    |   |       |
|  | localhost:11434   |  | (datasets, CSV)  |  | (models)   |   |       |
|  | Llama 3.1 (FREE) |  +------------------+  +------------+   |       |
|  +-------------------+                                         |       |
+-----------------------------------------------------------------------+
```

## Data Flow

### 1. Upload Flow
```
User clicks "Upload" in React UI
  -> React: vscode.postMessage({type: 'upload:request'})
    -> Extension: MessageHandler receives message
      -> Extension: opens VS Code file picker dialog
        -> User selects CSV/Excel file
          -> Extension: SidecarClient.uploadDataset(filePath)
            -> Python: POST /upload-dataset (saves file, returns preview)
              -> Extension: webview.postMessage({type: 'upload:complete', data})
                -> React: renders data preview table
```

### 2. Analysis Flow (SSE Streaming)
```
User clicks "Analyze" in React UI
  -> React: vscode.postMessage({type: 'analyze:start', config})
    -> Extension: MessageHandler.handleAnalyze()
      -> HTTP POST /projects/create (creates project)
      -> HTTP POST /projects/{id}/analyze (returns SSE stream)
        -> Python: spawns ReAct agent in background task
          -> Agent: THINK -> "I should detect the problem type"
          -> Agent: ACT -> calls detect_problem tool
          -> Python: pushes event to asyncio.Queue
            -> SSE: yields {type: "tool_start", tool: "detect_problem"}
              -> Extension: reads SSE line, forwards to webview
                -> React: updates PipelineProgress (step 1 = running)
          -> Agent: OBSERVE -> "Classification, target=Survived"
          -> Agent: THINK -> "Now I should profile the data"
          -> Agent: ACT -> calls profile_data tool
          -> ... (repeats for all 8 tools) ...
          -> Agent: FINAL ANSWER -> summary
            -> SSE: yields {type: "pipeline_complete"}
              -> React: fetches final results, renders charts
```

### 3. Prediction Flow
```
User sends feature values
  -> React: vscode.postMessage({type: 'predict:request', features})
    -> Extension: SidecarClient.predict(projectId, features)
      -> Python: loads .joblib model + preprocessing pipeline
        -> Preprocesses input with saved pipeline
        -> Runs model.predict()
        -> Returns prediction + probabilities
```

## ReAct Agent Loop

The agent follows the ReAct (Reason + Act) pattern powered by LangGraph:

```
                    +-------------------+
                    |   System Prompt   |
                    | "You are DataPilot |
                    |  an expert AI..." |
                    +--------+----------+
                             |
                             v
                    +--------+----------+
            +------>|   LLM (Ollama)    |
            |       |   Llama 3.1       |
            |       +--------+----------+
            |                |
            |         +------+------+
            |         |             |
            |    Tool Call?    Final Answer?
            |         |             |
            |         v             v
            |   +-----+-----+   +--+--+
            |   | Execute    |   | Done |
            |   | Tool       |   +-----+
            |   +-----+------+
            |         |
            |    Observation
            |    (tool result)
            |         |
            +----<----+
         (add to message history)
```

## Pipeline State (Shared Data)

All 8 tools read from and write to a single `PipelineState` dataclass:

```
PipelineState
  |
  +-- project_id, project_dir, status
  |
  +-- raw_df (original uploaded DataFrame)
  |
  +-- [Tool 1] target_column, task_type
  +-- [Tool 2] profile (shape, dtypes, missing, stats)
  +-- [Tool 3] eda_results (distributions, correlations, outliers)
  +-- [Tool 4] clean_df, preprocessing_pipeline, X_train, X_test, y_train, y_test
  +-- [Tool 5] engineered_features
  +-- [Tool 6] models, cv_results, best_model_name, best_model
  +-- [Tool 7] test_metrics (accuracy/F1/RMSE/R2)
  +-- [Tool 8] shap_values, feature_importance
  |
  +-- report_path, model_path (output artifacts)
```

## File Structure

```
DataPilot/
|
+-- src/                              # VS Code Extension (TypeScript)
|   +-- extension.ts                  # Entry point: activate/deactivate
|   +-- sidecar/
|   |   +-- sidecarManager.ts         # Spawn/kill Python, port allocation, health check
|   |   +-- sidecarClient.ts          # Typed HTTP client for all API calls
|   +-- webview/
|       +-- webviewProvider.ts        # Creates webview panel, injects React app
|       +-- messageHandler.ts         # Routes messages: React <-> Python API
|
+-- webview-ui/                       # React Frontend (Vite + Tailwind)
|   +-- src/
|       +-- App.tsx                   # Root component, state management
|       +-- vscode.ts                # acquireVsCodeApi() bridge
|       +-- hooks/useVsCodeMessage.ts # Hook for listening to extension messages
|       +-- types/messages.ts         # TypeScript types for message protocol
|       +-- components/
|           +-- UploadPanel.tsx        # File upload + data preview
|           +-- PipelineProgress.tsx   # 8-step progress tracker
|           +-- DataProfileView.tsx    # Data quality stats
|           +-- EDACharts.tsx          # Distribution/correlation charts
|           +-- ModelComparison.tsx    # CV scores bar chart + metrics
|           +-- ShapExplainer.tsx      # Feature importance visualization
|           +-- AgentLog.tsx           # Real-time agent reasoning stream
|
+-- backend/                          # Python Sidecar (FastAPI)
|   +-- main.py                       # FastAPI app, CORS, /health
|   +-- config.py                     # Ollama URL, model name, ML settings
|   +-- routers/
|   |   +-- dataset.py                # POST /upload-dataset
|   |   +-- project.py                # POST /projects/create, /analyze (SSE), GET /results
|   |   +-- predict.py                # POST /projects/{id}/predict
|   +-- agent/
|   |   +-- react_agent.py            # LangGraph ReAct loop + event streaming
|   |   +-- prompts.py                # System prompt (pipeline instructions)
|   +-- tools/
|   |   +-- base.py                   # PipelineTool base class (extends LangChain BaseTool)
|   |   +-- problem_detection.py      # Tool 1: detect target + task type
|   |   +-- data_profiling.py         # Tool 2: shape, dtypes, missing, stats
|   |   +-- eda.py                    # Tool 3: distributions, outliers, correlations
|   |   +-- preprocessing.py          # Tool 4: impute, encode, scale, split
|   |   +-- feature_engineering.py    # Tool 5: interaction features, variance filter
|   |   +-- model_training.py         # Tool 6: train 4 models, 5-fold CV
|   |   +-- evaluation.py             # Tool 7: test metrics, confusion matrix
|   |   +-- explainability.py         # Tool 8: SHAP values, feature importance
|   +-- pipeline/
|   |   +-- state.py                  # PipelineState dataclass (shared across tools)
|   +-- report/
|       +-- generator.py              # Jinja2 HTML report with embedded charts
|
+-- package.json                      # Extension manifest (commands, views, settings)
+-- tsconfig.json                     # TypeScript config
+-- esbuild.js                        # Extension bundler
```

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Extension | TypeScript + VS Code API | Process lifecycle, commands, webview hosting |
| UI | React + Vite + Tailwind CSS + Recharts | Interactive charts, pipeline progress, SHAP plots |
| Backend | Python + FastAPI + Uvicorn | REST API, SSE streaming, file handling |
| AI Agent | LangGraph + LangChain + Ollama | ReAct reasoning loop, tool orchestration |
| LLM | Llama 3.1 via Ollama | Free local inference, no API key needed |
| ML | scikit-learn + XGBoost + LightGBM | Model training, preprocessing, evaluation |
| Explainability | SHAP | Feature importance, model interpretability |
| Reports | Jinja2 + matplotlib | HTML reports with embedded charts |

## Key Design Decisions

| Decision | Why |
|----------|-----|
| **Sidecar pattern** | Python for ML (scikit-learn ecosystem), TypeScript for VS Code. Each uses its best language. |
| **Dynamic port** | Bind to port 0, OS picks a free port. No conflicts across multiple VS Code windows. |
| **SSE over WebSocket** | One-directional (server -> client) is all we need. Simpler than WebSocket. Works with HTTP fetch. |
| **Shared PipelineState** | All tools read/write one object. No database needed for MVP. State lives in memory during pipeline run. |
| **LangGraph over old AgentExecutor** | LangChain v1.2+ deprecated AgentExecutor. LangGraph is the official replacement with better streaming. |
| **Ollama (local LLM)** | Free, no API key, no cloud costs. Llama 3.1 8B runs on most machines with 8GB+ RAM. |
| **taskkill on Windows** | Node's child_process.kill() doesn't kill process trees on Windows. taskkill /T /F does. |
| **Chart data as JSON** | Backend sends numbers, frontend renders with Recharts. Interactive charts instead of static images. |
