"""
notebook_manager.py — Read and write Jupyter notebooks using nbformat.

nbformat is the Python library for manipulating .ipynb files.
A notebook is just a JSON file with this structure:
  {
    "cells": [
      {"cell_type": "code", "source": "import pandas as pd", "outputs": [...]},
      {"cell_type": "markdown", "source": "# Analysis", "outputs": []}
    ],
    "metadata": {"kernelspec": {...}},
    "nbformat": 4
  }

This module lets us:
  - Create blank notebooks
  - Add code/markdown cells
  - Read all cells (for agent context)
  - Summarize notebook state
"""

from pathlib import Path

import nbformat
from nbformat.v4 import new_notebook, new_code_cell, new_markdown_cell


def create_blank_notebook(path: str) -> str:
    """Create a new empty .ipynb file. Returns the path."""
    nb = new_notebook()
    # Add a welcome cell
    nb.cells.append(new_markdown_cell("# DataPilot Workspace\n*Upload data and start chatting!*"))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)
    return path


def add_code_cell(path: str, code: str, position: int = -1) -> int:
    """
    Add a code cell to the notebook.

    Args:
        path: path to .ipynb file
        code: Python code to insert
        position: where to insert (-1 = end)

    Returns:
        The index of the inserted cell
    """
    nb = _read(path)
    cell = new_code_cell(code)
    if position == -1:
        nb.cells.append(cell)
        idx = len(nb.cells) - 1
    else:
        nb.cells.insert(position, cell)
        idx = position
    _write(path, nb)
    return idx


def add_markdown_cell(path: str, text: str, position: int = -1) -> int:
    """Add a markdown cell to the notebook."""
    nb = _read(path)
    cell = new_markdown_cell(text)
    if position == -1:
        nb.cells.append(cell)
        idx = len(nb.cells) - 1
    else:
        nb.cells.insert(position, cell)
        idx = position
    _write(path, nb)
    return idx


def get_all_cells(path: str) -> list[dict]:
    """
    Read all cells from the notebook.

    Returns a list of dicts: [{"type": "code"|"markdown", "source": "...", "outputs": "..."}]
    """
    nb = _read(path)
    cells = []
    for cell in nb.cells:
        cell_data = {
            "type": cell.cell_type,
            "source": cell.source,
        }
        if cell.cell_type == "code" and cell.outputs:
            # Extract text output from cell outputs
            output_text = []
            for output in cell.outputs:
                if hasattr(output, "text"):
                    output_text.append(output.text)
                elif hasattr(output, "data"):
                    if "text/plain" in output.data:
                        output_text.append(output.data["text/plain"])
            cell_data["outputs"] = "\n".join(output_text)
        cells.append(cell_data)
    return cells


def get_notebook_summary(path: str, max_cells: int = 10) -> str:
    """
    Get a text summary of the notebook for the agent's context.

    The agent needs to know what code has already been run so it
    doesn't repeat imports or redefine variables.
    """
    cells = get_all_cells(path)
    if not cells:
        return "Notebook is empty."

    summary_parts = []
    code_cells = [c for c in cells if c["type"] == "code"]

    # Show last N code cells
    recent = code_cells[-max_cells:]
    for i, cell in enumerate(recent):
        source = cell["source"][:200]  # Truncate long cells
        summary_parts.append(f"Cell {i+1}:\n```python\n{source}\n```")

    return "\n\n".join(summary_parts)


def _read(path: str) -> nbformat.NotebookNode:
    with open(path, "r", encoding="utf-8") as f:
        return nbformat.read(f, as_version=4)


def _write(path: str, nb: nbformat.NotebookNode):
    with open(path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)
