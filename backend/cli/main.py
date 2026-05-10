"""
`datapilot` entry point.

Usage:
    datapilot                                 # interactive REPL
    datapilot upload <file.csv>               # REPL with df preloaded
    datapilot --provider groq --api-key sk... # one-off override
    datapilot config                          # rerun the setup prompt
    datapilot --version
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console

from cli import config as cfg_mod


__version__ = "2.0.0"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="datapilot",
        description="DataPilot — chat-driven data science in your terminal.",
    )
    parser.add_argument("--version", action="store_true", help="print version and exit")

    # Provider overrides (apply for this run; saved config untouched unless `config` cmd).
    parser.add_argument("--provider", choices=cfg_mod.PROVIDERS, help="override LLM provider")
    parser.add_argument("--model", help="override model name")
    parser.add_argument("--api-key", help="override API key (use env var or `config` for persistence)")
    parser.add_argument("--api-base", help="override base URL (Ollama)")

    sub = parser.add_subparsers(dest="cmd")

    upload_p = sub.add_parser("upload", help="open the REPL with a CSV preloaded as df")
    upload_p.add_argument("file", type=Path, help="path to a CSV file")

    sub.add_parser("config", help="rerun the interactive provider/key setup")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(f"datapilot {__version__}")
        return 0

    console = Console()

    # `config` subcommand: force interactive setup, save, exit.
    if args.cmd == "config":
        existing = cfg_mod.load_from_file()
        new_cfg = cfg_mod.interactive_setup(default=existing)
        cfg_mod.save_to_file(new_cfg)
        console.print(f"[green]saved[/green] to {cfg_mod.CONFIG_PATH}")
        return 0

    # Resolve provider/key for this run.
    try:
        resolved = cfg_mod.resolve(
            cli_provider=args.provider,
            cli_model=args.model,
            cli_api_key=args.api_key,
            cli_api_base=args.api_base,
        )
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        return 2

    if resolved.provider != "ollama" and not resolved.api_key:
        console.print(
            "[red]no API key available[/red]\n"
            f"set [cyan]{cfg_mod.KEY_ENV_VAR.get(resolved.provider, '<KEY>')}[/cyan], "
            "pass [cyan]--api-key[/cyan], or run [cyan]datapilot config[/cyan]"
        )
        return 2

    cfg_mod.apply_to_env(resolved)
    console.print(f"[dim]provider:[/dim] {resolved.provider}  [dim]model:[/dim] {resolved.model}")

    # Imports that read env vars must happen AFTER apply_to_env.
    from cli.repl import Repl
    from cli.session import CliSession

    session = CliSession()

    if args.cmd == "upload":
        try:
            info = session.load_csv(args.file)
        except FileNotFoundError:
            console.print(f"[red]file not found:[/red] {args.file}")
            return 1
        except Exception as e:
            console.print(f"[red]load failed:[/red] {e}")
            return 1
        console.print(
            f"[green]loaded[/green] {info['rows']:,} rows x {len(info['columns'])} cols"
        )

    return Repl(session, console=console).loop()


if __name__ == "__main__":
    sys.exit(main())
