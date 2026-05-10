# DataPilot

**A chat-driven data science copilot.** Type what you want in plain English, get the right Python code in your notebook — generated deterministically when possible, and only falling back to an LLM when the request is novel.

DataPilot ships in two forms:

- **`datapilot` CLI** — terminal REPL with a stateful Jupyter kernel. Upload a CSV, ask questions, run code, export the whole transcript as a `.ipynb` (uploadable to Kaggle / Colab / Jupyter).
- **VS Code extension** — chat sidebar that drops generated code into the notebook you already have open.

Both share the same agent. Bring your own API key — Cerebras (recommended, free, fast), Groq, or local Ollama — and your key never leaves your machine.

---

## How it works

```
User: "plot age vs salary"
        |
        v
[IntentRouter — pure Python, no LLM]
   matches `plot X vs Y` pattern, validates columns
        |
        v
[Template: scatter] -> deterministic Python snippet
        |
        v
[Kernel.execute]    -> live output in your terminal / notebook
```

There are three tiers:

| Tier      | When it runs                            | LLM tokens |
|-----------|-----------------------------------------|------------|
| `template` | ~17 common DS verbs (head, shape, describe, missing, plot X, plot X vs Y, train classifier, encode, scale, …) | **0** |
| `qa`       | Questions ending in `?`, "what / why / how / explain" | 1 call (text only) |
| `codegen`  | Anything the templates don't cover      | 1 call (code + explanation) |

Most sessions cost zero tokens. The LLM is reserved for the hard parts.

---

## Install — CLI

```bash
pip install git+https://github.com/Shawn2110/DataPilot-V2.git#subdirectory=backend
```

That installs the `datapilot` command on your PATH plus everything it needs (FastAPI, LangChain, jupyter-client, pandas, scikit-learn, plotly, rich, prompt-toolkit).

First run will prompt for a provider + API key:

```bash
datapilot
```

```
DataPilot — first-run configuration
Pick an LLM provider:
  1) cerebras  · cloud, free, very fast (recommended)
  2) groq      · cloud, free, more model variety
  3) ollama    · local, no key, needs RAM and a running Ollama server

choice [1/2/3] (default cerebras):
```

Your choice is saved to `~/.datapilot/config.json` (0600 on POSIX). Skip the prompt later by passing flags:

```bash
datapilot --provider cerebras --api-key csk-... --model llama3.1-8b
datapilot config              # rerun the prompt to change provider
datapilot upload data.csv     # open REPL with df preloaded
```

Get a free Cerebras key at https://cloud.cerebras.ai (no credit card).

### Inside the REPL

```
> /upload sales.csv
loaded 12,847 rows x 18 cols  (Date, Region, Product, Price, Quantity, ...)

> show missing values
  template  Count missing values per column in `df`, sorted from worst to best.
  _missing = df.isnull().sum().sort_values(ascending=False)
  _missing[_missing > 0]
run? [Y/n/e] y
  Discount     1247
  CustomerID    312
  dtype: int64

> what does sort_values(ascending=False) do?
[qa] Sorts the values from largest to smallest. Used here so the columns
with the most missing data appear at the top, making it easy to spot the
worst offenders first.

> /save analysis.ipynb
saved C:\Users\you\analysis.ipynb
```

Slash commands:

| Command | What it does |
|---|---|
| `/upload <path>` | Read a CSV into the kernel as `df` |
| `/save [path]` | Export the session as a Jupyter notebook |
| `/provider` | Switch provider/key mid-session |
| `/columns` | List the loaded DataFrame's columns |
| `/history` | Dump the chat transcript |
| `/clear` | Clear the terminal |
| `/exit` | Quit (prompts to save first) |

---

## Install — VS Code extension

The extension isn't on the Marketplace yet. Install from the `.vsix`:

```bash
git clone https://github.com/Shawn2110/DataPilot-V2.git
cd DataPilot-V2/extension
npm install
npx vsce package --allow-missing-repository
code --install-extension datapilot-2.0.0.vsix
```

(Or build the .vsix on one machine and send it around — it's ~27 KB.)

You also need the backend running:

```bash
cd backend
pip install -e .                              # one-time
python -m uvicorn app.main:app --port 8000    # leave this running
```

Then in VS Code:

1. Open any `.ipynb` (the extension only activates on Jupyter notebooks)
2. The DataPilot icon appears in the activity bar — click it to open the chat
3. First time: VS Code's command palette shows **DataPilot: Configure Provider / API Key** — pick provider, paste key
4. Type prompts in the sidebar; generated code lands in your notebook cells

The API key is stored in **VS Code SecretStorage** (OS keychain — Credential Manager on Windows, Keychain on macOS). It is never written to settings, never logged, and only sent to your local backend over `X-Datapilot-Api-Key`.

---

## Provider matrix

| Provider | Cost | Speed | Setup | Default model |
|---|---|---|---|---|
| **Cerebras** | Free tier | Fastest (~2500 tok/s) | API key from https://cloud.cerebras.ai | `llama3.1-8b` |
| **Groq** | Free tier | Fast | API key from https://console.groq.com | `llama-3.3-70b-versatile` |
| **Ollama** | Free, local | Depends on RAM | `ollama pull llama3.2:1b` + run `ollama serve` | `llama3.2:1b` |

Switch any time via `datapilot config`, `/provider` in the REPL, or `DataPilot: Configure Provider / API Key` in VS Code.

---

## Project layout

```
DataPilot-V2/
├── backend/
│   ├── app/
│   │   ├── agent/          # IntentRouter, templates, codegen, qa, pipeline
│   │   ├── routers/        # FastAPI endpoints (chat, upload, kernel, execute)
│   │   ├── services/       # Session state
│   │   └── jupyter/        # Jupyter Server bridge (used by web app variant)
│   ├── cli/                # `datapilot` REPL — config, kernel, repl, notebook
│   ├── reference/          # Archived v1 code (LangGraph agent, ML tool catalog)
│   ├── pyproject.toml      # `pip install -e .` lives here
│   └── requirements.txt
└── extension/
    ├── src/
    │   ├── extension.ts    # activate(), command registration
    │   ├── config.ts       # SecretStorage + QuickPick + InputBox
    │   ├── chat/           # Webview chat sidebar
    │   ├── notebook/       # Insert generated code into the open .ipynb
    │   └── backend/        # HTTP client, sends X-Datapilot-* headers
    ├── package.json        # Manifest, commands, configuration schema
    └── esbuild.js          # Bundles src/extension.ts to dist/
```

---

## Development

### Backend

```bash
cd backend
pip install -e .
python -m uvicorn app.main:app --reload --port 8000
curl http://127.0.0.1:8000/health
```

### Extension

```bash
cd extension
npm install
node esbuild.js --watch          # build, then rebuild on change
```

Press **F5** in VS Code with `extension/` open to launch an Extension Development Host.

### Run the test session

```bash
printf '/upload test.csv\nshape\nshow head\n/save /tmp/demo.ipynb\n/exit\nn\n' | datapilot
```

---

## Security

- API keys are loaded from (in order): CLI flags → environment variables → `~/.datapilot/config.json` → interactive prompt
- The CLI uses `getpass` for key entry (no echo)
- The extension uses **SecretStorage** which delegates to the OS keychain
- Keys are sent to the backend only as `X-Datapilot-Api-Key` headers, used for one request, never logged or persisted server-side
- `.env`, `~/.datapilot/`, `*.vsix`, and `datapilot_session_*.ipynb` are all `.gitignore`d

---

## License

MIT

Built by [Shawn2110](https://github.com/Shawn2110).
