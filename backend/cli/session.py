"""
Session — pairs the agent pipeline with a live LocalKernel.

Holds:
  - The kernel (one per CLI invocation, started lazily on first run).
  - The currently-loaded DataFrame's column list (for the router).
  - Chat history (so QA turns can reference prior turns).

The kernel persists across turns: upload a CSV once, refer to `df` forever.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from app.agent.intents import IntentResult
from app.agent.pipeline import run as pipeline_run
from cli.kernel import LocalKernel, ExecutionResult


@dataclass
class CliSession:
    df_name: str = "df"
    columns: list[str] = field(default_factory=list)
    chat_history: list[dict] = field(default_factory=list)
    kernel: LocalKernel = field(default_factory=LocalKernel)

    def ensure_kernel(self) -> None:
        self.kernel.start()

    def close(self) -> None:
        self.kernel.stop()

    # --- High-level operations ---

    def load_csv(self, path: Path) -> dict:
        """Load a CSV into the kernel as `df`. Returns schema info."""
        self.ensure_kernel()
        path = Path(path).resolve()
        df = pd.read_csv(path)
        self.columns = list(df.columns)

        # Make the DataFrame available in the kernel.
        load_code = (
            "import pandas as pd\n"
            f"{self.df_name} = pd.read_csv(r'{path}')\n"
            f"print(f'Loaded {{{self.df_name}.shape[0]:,}} rows, {{{self.df_name}.shape[1]}} columns')"
        )
        self.kernel.execute(load_code)
        return {
            "rows": df.shape[0],
            "columns": list(df.columns),
            "dtypes": df.dtypes.astype(str).to_dict(),
        }

    def ask(self, text: str) -> IntentResult:
        """Route the user's text through the agent pipeline."""
        self.chat_history.append({"role": "user", "content": text})
        result = pipeline_run(
            text=text,
            columns=self.columns,
            chat_history=self.chat_history,
            df_name=self.df_name,
        )
        record = result.explanation
        if result.code:
            record += f"\n\n```python\n{result.code}\n```"
        self.chat_history.append({"role": "assistant", "content": record})
        return result

    def run_code(self, code: str, timeout: float = 60.0) -> ExecutionResult:
        """Execute code in the persistent kernel."""
        self.ensure_kernel()
        return self.kernel.execute(code, timeout=timeout)
