"""
Session — pairs the agent pipeline with a live LocalKernel and tracks
every turn so the transcript can be exported as a Jupyter notebook.

The kernel persists across turns: upload a CSV once, refer to `df` forever.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from app.agent.intents import IntentResult
from app.agent.pipeline import run as pipeline_run
from cli.kernel import LocalKernel, ExecutionResult
from cli.notebook import TurnRecord, write_notebook


@dataclass
class CliSession:
    df_name: str = "df"
    columns: list[str] = field(default_factory=list)
    chat_history: list[dict] = field(default_factory=list)
    kernel: LocalKernel = field(default_factory=LocalKernel)
    turns: list[TurnRecord] = field(default_factory=list)
    # Code we ran on the user's behalf during the most recent /upload.
    # Attached to the next recorded turn so the notebook reproduces it.
    _pending_setup_code: str | None = None

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

        load_code = (
            "import pandas as pd\n"
            f"{self.df_name} = pd.read_csv(r'{path}')\n"
            f"print(f'Loaded {{{self.df_name}.shape[0]:,}} rows, {{{self.df_name}.shape[1]}} columns')"
        )
        self.kernel.execute(load_code)
        # Attach to the next turn so the exported notebook is self-contained.
        self._pending_setup_code = load_code
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

    # --- Notebook tracking ---

    def record_turn(
        self,
        user_text: str,
        result: IntentResult,
        executed_code: str | None = None,
        execution: ExecutionResult | None = None,
    ) -> None:
        """Called by the REPL after each turn finishes (run-or-skipped)."""
        turn = TurnRecord(
            user_text=user_text,
            explanation=result.explanation,
            source=result.source,
            code=executed_code if executed_code is not None else result.code,
            executed=execution is not None,
            setup_code=self._pending_setup_code,
        )
        self._pending_setup_code = None  # consume the setup attachment
        if execution is not None:
            turn.stdout = execution.stdout
            turn.stderr = execution.stderr
            turn.result = execution.result
            turn.error = execution.error
            turn.images = list(execution.images)
        self.turns.append(turn)

    def save_notebook(self, path: Path | None = None) -> Path:
        """Write the session transcript to a .ipynb file."""
        from cli.notebook import default_save_path
        target = Path(path).expanduser() if path else default_save_path()
        return write_notebook(self.turns, target, df_name=self.df_name)
