"""
Interactive REPL — the surface a user sees when they type `datapilot`.

Each turn:
  1. Read user input (prompt_toolkit gives history + line editing).
  2. Send it through the session — get back {explanation, code, source}.
  3. Print the explanation.
  4. If there's code, syntax-highlight it and ask y/N/edit.
  5. On y → run in the kernel, print stdout/stderr/result.

REPL commands (typed at the prompt):
  /upload <path>   load a CSV into the kernel as `df`
  /columns         list the loaded columns
  /clear           clear the screen
  /history         dump the chat transcript
  /exit, /quit     leave (Ctrl-D also works)
"""

from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
from pathlib import Path

from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel
from rich.text import Text

from cli import config as cfg_mod
from cli.session import CliSession


HISTORY_PATH = Path.home() / ".datapilot_history"


def _build_prompt_session():
    """
    Try to build a prompt_toolkit PromptSession. Returns None on terminals
    it can't drive (MinTTY, non-tty stdin, Cygwin without compiled Python).
    The REPL falls back to plain input() in that case.
    """
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import FileHistory
        return PromptSession(history=FileHistory(str(HISTORY_PATH)))
    except Exception:
        return None


class Repl:
    def __init__(self, session: CliSession, console: Console | None = None) -> None:
        self.session = session
        self.console = console or Console()
        self.prompt_session = _build_prompt_session()

    # --- Entry point ---

    def loop(self) -> int:
        self._print_banner()
        try:
            while True:
                try:
                    text = self._prompt("> ")
                except (EOFError, KeyboardInterrupt):
                    self.console.print()
                    break

                text = text.strip()
                if not text:
                    continue
                if text.startswith("/"):
                    if not self._handle_command(text):
                        break
                    continue

                self._handle_turn(text)
        finally:
            self.session.close()
        return 0

    # --- Slash commands ---

    def _handle_command(self, text: str) -> bool:
        """Return False to exit the REPL."""
        parts = shlex.split(text)
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd in ("/exit", "/quit", "/q"):
            return False

        if cmd == "/clear":
            self.console.clear()
            return True

        if cmd == "/upload":
            if not args:
                self.console.print("[red]usage:[/red] /upload <path-to-csv>")
                return True
            self._upload(Path(args[0]))
            return True

        if cmd == "/provider":
            existing = cfg_mod.load_from_file()
            new_cfg = cfg_mod.interactive_setup(default=existing)
            cfg_mod.save_to_file(new_cfg)
            cfg_mod.apply_to_env(new_cfg)
            self.console.print(f"[green]switched to[/green] {new_cfg.provider}/{new_cfg.model}")
            return True

        if cmd == "/columns":
            if not self.session.columns:
                self.console.print("[dim]no data loaded — try /upload <file.csv>[/dim]")
            else:
                self.console.print(", ".join(self.session.columns))
            return True

        if cmd == "/history":
            for turn in self.session.chat_history:
                role = turn["role"]
                color = "cyan" if role == "user" else "white"
                self.console.print(f"[{color}]{role}:[/{color}] {turn['content'][:200]}")
            return True

        if cmd in ("/help", "/?"):
            self._print_banner()
            return True

        self.console.print(f"[red]unknown command:[/red] {cmd}")
        return True

    def _upload(self, path: Path) -> None:
        if not path.exists():
            self.console.print(f"[red]file not found:[/red] {path}")
            return
        try:
            info = self.session.load_csv(path)
        except Exception as e:
            self.console.print(f"[red]load failed:[/red] {e}")
            return
        cols_preview = ", ".join(info["columns"][:8])
        if len(info["columns"]) > 8:
            cols_preview += f", … ({len(info['columns']) - 8} more)"
        self.console.print(
            f"[green]loaded[/green] {info['rows']:,} rows x {len(info['columns'])} cols  "
            f"[dim]({cols_preview})[/dim]"
        )

    # --- Chat turn ---

    def _handle_turn(self, text: str) -> None:
        try:
            result = self.session.ask(text)
        except Exception as e:
            self.console.print(f"[red]agent error:[/red] {e}")
            return

        # Tag the source so the user can see when the LLM was involved.
        badge = {
            "template": "[dim]template[/dim]",
            "codegen": "[yellow]llm-codegen[/yellow]",
            "qa": "[blue]llm-qa[/blue]",
        }.get(result.source, result.source)

        if result.code is None:
            # QA path: text-only.
            self.console.print(Panel(
                result.explanation,
                title=badge,
                border_style="blue",
                padding=(0, 1),
            ))
            return

        self.console.print(f"  {badge}  {result.explanation}")
        self.console.print(Syntax(result.code, "python", theme="monokai", line_numbers=False))

        choice = self._ask_run_choice()
        if choice == "n":
            return

        code = result.code
        if choice == "e":
            edited = self._edit(code)
            if edited is None:
                self.console.print("[dim]cancelled[/dim]")
                return
            code = edited

        self._run(code)

    def _ask_run_choice(self) -> str:
        try:
            answer = self._prompt("run? [Y/n/e] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return "n"
        if answer in ("n", "no"):
            return "n"
        if answer in ("e", "edit"):
            return "e"
        return "y"

    def _prompt(self, label: str) -> str:
        if self.prompt_session is not None:
            from prompt_toolkit.formatted_text import HTML
            colored = label.replace("> ", "<ansigreen>></ansigreen> ")
            colored = colored.replace("run? [Y/n/e] ", "<ansiyellow>run? [Y/n/e]</ansiyellow> ")
            return self.prompt_session.prompt(HTML(colored))
        return input(label)

    def _edit(self, code: str) -> str | None:
        editor = os.environ.get("EDITOR") or ("notepad" if os.name == "nt" else "vi")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            path = f.name
        try:
            subprocess.run([editor, path], check=False)
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    def _run(self, code: str) -> None:
        try:
            res = self.session.run_code(code)
        except Exception as e:
            self.console.print(f"[red]kernel error:[/red] {e}")
            return

        if res.stdout:
            self.console.print(res.stdout.rstrip())
        if res.result:
            self.console.print(Text(res.result.rstrip(), style="white"))
        if res.stderr:
            self.console.print(Text(res.stderr.rstrip(), style="yellow"))
        if res.error:
            self.console.print(Panel(res.error, border_style="red", title="error"))
        if res.images:
            self.console.print(f"[dim]({len(res.images)} image output(s) — not rendered in terminal)[/dim]")

    # --- Cosmetic ---

    def _print_banner(self) -> None:
        self.console.print(Panel.fit(
            "[bold]DataPilot[/bold] [dim]- data science copilot[/dim]\n"
            "[dim]/upload <file.csv>  /provider  /columns  /history  /exit[/dim]",
            border_style="green",
        ))
