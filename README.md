# DataPilot

**AI-Powered Data Science Copilot for VS Code**

DataPilot automates the full machine learning workflow inside VS Code. Upload a CSV, and an AI agent runs a complete ML pipeline — from data profiling to model training to SHAP explainability — with real-time progress streaming.

Built with a custom **ReAct agent** (LangGraph + Ollama), it reasons through each step, adapts to your data, and explains its decisions in plain language. **Completely free** — runs locally using Llama 3.1 via Ollama.

---

## What It Does

```
Upload CSV/Excel
      |
      v
  +---+---+---+---+---+---+---+---+
  | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |  <- AI Agent runs 8 steps automatically
  +---+---+---+---+---+---+---+---+
    |   |   |   |   |   |   |   |
    |   |   |   |   |   |   |   +-- SHAP Explainability
    |   |   |   |   |   |   +------ Model Evaluation
    |   |   |   |   |   +---------- Model Training (4 models, 5-fold CV)
    |   |   |   |   +-------------- Feature Engineering
    |   |   |   +------------------ Preprocessing (impute, scale, encode)
    |   |   +---------------------- EDA (distributions, outliers, correlations)
    |   +-------------------------- Data Profiling (quality report)
    +------------------------------ Problem Detection (classification vs regression)
      |
      v
  Downloadable: HTML Report + Trained Model (.joblib)
```

## Features

- **Automatic ML Pipeline** — 8-step pipeline from raw data to explainable model
- **AI Reasoning** — Agent thinks at each step, adapts to data quality issues
- **Real-time Progress** — SSE streaming shows pipeline steps as they happen
- **Interactive Charts** — EDA distributions, correlation heatmaps, model comparison
- **SHAP Explainability** — Understand why the model makes each prediction
- **Free & Local** — Llama 3.1 via Ollama, no API keys, no cloud costs
- **Downloadable Outputs** — HTML report, trained model (.joblib), preprocessing pipeline

## Models Trained

| Task | Models |
|------|--------|
| Classification | Logistic Regression, Random Forest, XGBoost, LightGBM |
| Regression | Linear Regression, Random Forest, XGBoost, LightGBM |

All models evaluated with **5-fold cross-validation**. Best model selected automatically.

---

## Prerequisites

- **VS Code** 1.85+
- **Python** 3.10+
- **Node.js** 18+
- **Ollama** — [Download here](https://ollama.com/download)

## Quick Start

### 1. Install Ollama and pull a model

```bash
# Install Ollama from https://ollama.com/download
# Then pull Llama 3.1 (4.9 GB download, runs on 8GB+ RAM):
ollama pull llama3.1
```

### 2. Clone and install

```bash
git clone https://github.com/Shawn2110/DataPilot.git
cd DataPilot

# Install extension dependencies
npm install

# Install Python dependencies
pip install -r backend/requirements.txt

# Install webview dependencies
cd webview-ui && npm install && cd ..
```

### 3. Build

```bash
# Build the VS Code extension
npm run build:ext

# Build the React webview
npm run build:webview
```

### 4. Run

1. Open the `DataPilot` folder in VS Code
2. Press **F5** to launch the extension in debug mode
3. Click the **DataPilot icon** in the left sidebar
4. Click **Upload Dataset** and select a CSV file
5. Choose a target column (or let the agent detect it)
6. Click **Analyze** and watch the AI pipeline run

---

## Architecture

DataPilot has three layers:

```
[React Webview]  <--postMessage-->  [VS Code Extension]  <--HTTP/SSE-->  [Python FastAPI]
     (UI)              (bridge)             (ML + AI Agent)
```

| Layer | Technology | Role |
|-------|-----------|------|
| **Extension** | TypeScript + VS Code API | Spawns Python server, manages webview, bridges communication |
| **Webview** | React + Tailwind + Recharts | Interactive UI with charts, progress tracker, agent log |
| **Backend** | FastAPI + LangGraph + Ollama | ML pipeline, ReAct agent, SHAP analysis, report generation |

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full technical deep-dive.

## Project Structure

```
DataPilot/
+-- src/                          # VS Code Extension (TypeScript)
|   +-- extension.ts              # Entry point
|   +-- sidecar/                  # Python process management
|   +-- webview/                  # Webview panel + message handler
|
+-- webview-ui/                   # React Frontend
|   +-- src/components/           # UI components (Upload, Charts, SHAP, etc.)
|
+-- backend/                      # Python Backend
|   +-- agent/                    # LangGraph ReAct agent
|   +-- tools/                    # 8 pipeline tools
|   +-- routers/                  # FastAPI endpoints
|   +-- pipeline/                 # Shared state
|   +-- report/                   # HTML report generator
|
+-- package.json                  # Extension manifest
```

---

## Configuration

DataPilot settings are available in VS Code Settings (Ctrl+,):

| Setting | Default | Description |
|---------|---------|-------------|
| `datapilot.pythonPath` | `python` | Path to Python interpreter |
| `datapilot.ollamaModel` | `llama3.1` | Ollama model to use |
| `datapilot.ollamaUrl` | `http://localhost:11434` | Ollama server URL |

### Alternative models (all free via Ollama)

```bash
ollama pull mistral        # Mistral 7B — fast, good reasoning
ollama pull qwen2.5        # Alibaba Qwen 2.5 — strong at structured tasks
ollama pull llama3.1:70b   # Llama 3.1 70B — smarter, needs ~40GB RAM
```

Then set `datapilot.ollamaModel` to the model name.

---

## API Endpoints

The Python sidecar exposes these endpoints (internal, used by the extension):

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check (extension polls this on startup) |
| `POST` | `/upload-dataset` | Upload CSV/Excel, returns preview |
| `POST` | `/projects/create` | Create project, configure pipeline |
| `POST` | `/projects/{id}/analyze` | Run pipeline, returns SSE event stream |
| `GET` | `/projects/{id}/results` | Get final pipeline results |
| `POST` | `/projects/{id}/predict` | Run inference with trained model |

---

## How the AI Agent Works

DataPilot uses the **ReAct pattern** (Reason + Act):

```
Agent: "I need to detect the problem type first."          <- THINK
Agent: calls detect_problem tool                            <- ACT
Tool:  returns {target: "Survived", task: "classification"} <- OBSERVE
Agent: "This is binary classification. 38% survived,        <- THINK
        62% did not. The classes are imbalanced.
        Now I should profile the data quality."
Agent: calls profile_data tool                              <- ACT
Tool:  returns {missing: {Age: 19.8%}, duplicates: 0}       <- OBSERVE
Agent: "Age has 19.8% missing values. I'll impute with      <- THINK
        median since it's robust to outliers..."
...continues for all 8 tools...
```

The agent **adapts** based on what it finds. High missing values trigger different imputation strategies. Imbalanced classes affect model evaluation. The LLM reasons at every step instead of blindly running a fixed pipeline.

---

## Development

### Debug the Extension
```bash
# In VS Code, press F5 to launch Extension Development Host
# Check "Output > DataPilot" for Python server logs
```

### Debug the Python Backend (standalone)
```bash
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8765 --reload

# Test health check
curl http://127.0.0.1:8765/health

# Test upload
curl -X POST http://127.0.0.1:8765/upload-dataset -F "file=@test.csv"
```

### Dev mode for webview
```bash
cd webview-ui
npm run dev    # Vite dev server with hot reload (outside VS Code)
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Extension | TypeScript, VS Code Extension API, esbuild |
| Frontend | React 18, Vite 5, Tailwind CSS, Recharts |
| Backend | Python, FastAPI, Uvicorn, SSE-Starlette |
| AI Agent | LangGraph, LangChain, Ollama |
| LLM | Llama 3.1 8B (via Ollama, free & local) |
| ML | scikit-learn, XGBoost, LightGBM |
| Explainability | SHAP |
| Reports | Jinja2, Matplotlib, Seaborn |

## License

MIT

---

Built by [Shawn2110](https://github.com/Shawn2110)
