"""
Notebook export — turn a CliSession transcript into a .ipynb file.

Output is Jupyter nbformat v4, which Kaggle, Colab, JupyterLab, classic
Notebook, and VS Code's Jupyter extension all read. Each user turn
becomes a markdown cell (the prompt + explanation) followed, when the
turn produced code, by a code cell with embedded outputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import nbformat


@dataclass
class TurnRecord:
    user_text: str
    explanation: str
    source: str = "template"
    code: str | None = None
    executed: bool = False
    stdout: str = ""
    stderr: str = ""
    result: str = ""
    error: str | None = None
    images: list[str] = field(default_factory=list)
    # Optional: any helper code we ran on the user's behalf (e.g., the
    # pd.read_csv from /upload). Preserved so the notebook re-runs cleanly.
    setup_code: str | None = None


def build_notebook(turns: list[TurnRecord], df_name: str = "df") -> nbformat.NotebookNode:
    nb = nbformat.v4.new_notebook()
    cells: list = []

    header = (
        f"# DataPilot session\n\n"
        f"_Exported {datetime.now().strftime('%Y-%m-%d %H:%M')}._  "
        f"This notebook is a transcript of an interactive DataPilot session — "
        f"every code cell ran in a live Python kernel. Re-run from top to bottom "
        f"to reproduce the session."
    )
    cells.append(nbformat.v4.new_markdown_cell(header))

    for i, turn in enumerate(turns, start=1):
        # Setup code (e.g., the load from /upload) goes in its own code cell.
        if turn.setup_code:
            setup_cell = nbformat.v4.new_code_cell(turn.setup_code)
            cells.append(setup_cell)

        prompt_md = f"**Q{i}.** {turn.user_text}\n\n{turn.explanation}"
        if turn.source != "template":
            prompt_md += f"\n\n_(generated via `{turn.source}`)_"
        cells.append(nbformat.v4.new_markdown_cell(prompt_md))

        if not turn.code:
            continue

        cell = nbformat.v4.new_code_cell(turn.code)
        if turn.executed:
            cell["execution_count"] = i
        outputs: list = []
        if turn.stdout:
            outputs.append(nbformat.v4.new_output(
                output_type="stream", name="stdout", text=turn.stdout,
            ))
        if turn.result:
            outputs.append(nbformat.v4.new_output(
                output_type="execute_result",
                data={"text/plain": turn.result},
                execution_count=i,
            ))
        for img_b64 in turn.images:
            outputs.append(nbformat.v4.new_output(
                output_type="display_data",
                data={"image/png": img_b64},
            ))
        if turn.stderr:
            outputs.append(nbformat.v4.new_output(
                output_type="stream", name="stderr", text=turn.stderr,
            ))
        if turn.error:
            outputs.append(nbformat.v4.new_output(
                output_type="error",
                ename="ExecutionError",
                evalue="(see traceback)",
                traceback=turn.error.splitlines(),
            ))
        cell["outputs"] = outputs
        cells.append(cell)

    nb["cells"] = cells
    nb["metadata"] = {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python"},
        "datapilot": {"df_name": df_name},
    }
    return nb


def write_notebook(turns: list[TurnRecord], path: Path, df_name: str = "df") -> Path:
    nb = build_notebook(turns, df_name=df_name)
    path = Path(path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, str(path))
    return path


def default_save_path() -> Path:
    """`datapilot_session_<YYYYMMDD-HHMMSS>.ipynb` in the current directory."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path.cwd() / f"datapilot_session_{stamp}.ipynb"
