"""
`datapilot` entry point.

Usage:
    datapilot                    # interactive REPL
    datapilot upload <file.csv>  # REPL with df preloaded from file
    datapilot --version
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console

from cli.repl import Repl
from cli.session import CliSession


__version__ = "2.0.0"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="datapilot",
        description="DataPilot — chat-driven data science in your terminal.",
    )
    parser.add_argument("--version", action="store_true", help="print version and exit")

    sub = parser.add_subparsers(dest="cmd")

    upload_p = sub.add_parser("upload", help="open the REPL with a CSV preloaded as df")
    upload_p.add_argument("file", type=Path, help="path to a CSV file")

    args = parser.parse_args(argv)

    if args.version:
        print(f"datapilot {__version__}")
        return 0

    console = Console()
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
            f"[green]loaded[/green] {info['rows']:,} rows × {len(info['columns'])} cols"
        )

    return Repl(session, console=console).loop()


if __name__ == "__main__":
    sys.exit(main())
