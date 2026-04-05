import * as vscode from "vscode";

/**
 * NotebookBridge — Insert code cells into the active Jupyter notebook.
 *
 * Uses the VS Code Notebook API to:
 *   1. Insert new code cells with agent-generated Python code
 *   2. Read existing cells (for agent context)
 *   3. Execute cells (optional — user can run manually too)
 *
 * The key insight: we DON'T run a separate Jupyter kernel.
 * The user's VS Code Jupyter extension already has a kernel running.
 * We just insert cells and let the user (or VS Code) execute them.
 */
export class NotebookBridge {
  /**
   * Insert a code cell at the end of the active notebook.
   *
   * This is the main function the chat flow uses.
   * When the agent generates code, it comes here.
   */
  async insertCodeCell(code: string): Promise<boolean> {
    const editor = vscode.window.activeNotebookEditor;
    if (!editor) {
      vscode.window.showWarningMessage(
        "No Jupyter notebook is open. Open a .ipynb file first."
      );
      return false;
    }

    const notebook = editor.notebook;
    const cellData = new vscode.NotebookCellData(
      vscode.NotebookCellKind.Code,
      code,
      "python"
    );

    const edit = new vscode.WorkspaceEdit();
    const insertIndex = notebook.cellCount;

    edit.set(notebook.uri, [
      vscode.NotebookEdit.insertCells(insertIndex, [cellData]),
    ]);

    const success = await vscode.workspace.applyEdit(edit);

    if (success) {
      // Scroll to the new cell
      const newCell = notebook.cellAt(insertIndex);
      const range = new vscode.NotebookRange(insertIndex, insertIndex + 1);
      editor.revealRange(range, vscode.NotebookEditorRevealType.InCenter);
    }

    return success;
  }

  /**
   * Insert a markdown cell (for explanations/headers).
   */
  async insertMarkdownCell(text: string): Promise<boolean> {
    const editor = vscode.window.activeNotebookEditor;
    if (!editor) return false;

    const cellData = new vscode.NotebookCellData(
      vscode.NotebookCellKind.Markup,
      text,
      "markdown"
    );

    const edit = new vscode.WorkspaceEdit();
    edit.set(editor.notebook.uri, [
      vscode.NotebookEdit.insertCells(editor.notebook.cellCount, [cellData]),
    ]);

    return vscode.workspace.applyEdit(edit);
  }

  /**
   * Read all code cells from the active notebook.
   *
   * Used to build context for the agent — it needs to know
   * what code has already been run (imports, variable names, etc.)
   */
  getCells(): { type: string; source: string }[] {
    const editor = vscode.window.activeNotebookEditor;
    if (!editor) return [];

    const cells: { type: string; source: string }[] = [];
    for (let i = 0; i < editor.notebook.cellCount; i++) {
      const cell = editor.notebook.cellAt(i);
      cells.push({
        type:
          cell.kind === vscode.NotebookCellKind.Code ? "code" : "markdown",
        source: cell.document.getText(),
      });
    }
    return cells;
  }

  /**
   * Execute the last cell in the notebook.
   * Uses VS Code's built-in notebook execution command.
   */
  async executeLastCell(): Promise<void> {
    const editor = vscode.window.activeNotebookEditor;
    if (!editor || editor.notebook.cellCount === 0) return;

    const lastIndex = editor.notebook.cellCount - 1;
    const range = new vscode.NotebookRange(lastIndex, lastIndex + 1);
    editor.selection = range;

    await vscode.commands.executeCommand("notebook.cell.execute");
  }

  /**
   * Check if a Jupyter notebook is currently open and active.
   */
  isNotebookActive(): boolean {
    return !!vscode.window.activeNotebookEditor;
  }
}
