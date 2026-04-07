"use client";

import { useState } from "react";
import { CodeCell } from "./CodeCell";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";

export interface Cell {
  id: string;
  code: string;
  output?: string;
  isRunning?: boolean;
}

/**
 * NotebookPanel — Built-in notebook with Monaco editor cells.
 *
 * Replaces the JupyterLab iframe. The agent pushes code into cells,
 * the user can edit and run them. Output displays below each cell.
 *
 * Code execution is done via the backend's /api/kernel/execute endpoint
 * (or users can copy-paste to their own environment).
 */
export function NotebookPanel({
  cells,
  onCellChange,
  onCellRun,
  onCellDelete,
  onAddCell,
}: {
  cells: Cell[];
  onCellChange: (id: string, code: string) => void;
  onCellRun: (id: string, code: string) => void;
  onCellDelete: (id: string) => void;
  onAddCell: () => void;
}) {
  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <div className="shrink-0 flex items-center justify-between px-4 py-2 border-b">
        <h2 className="text-sm font-semibold text-muted-foreground">Notebook</h2>
        <Button variant="outline" size="sm" className="h-7 text-xs" onClick={onAddCell}>
          + Add Cell
        </Button>
      </div>

      {/* Cells */}
      <ScrollArea className="flex-1 min-h-0">
        <div className="p-4 space-y-3">
          {cells.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground text-sm">
              <p>No cells yet.</p>
              <p className="mt-1">Chat with DataPilot to generate code, or add a cell manually.</p>
            </div>
          ) : (
            cells.map((cell, idx) => (
              <CodeCell
                key={cell.id}
                code={cell.code}
                cellIndex={idx + 1}
                output={cell.output}
                isRunning={cell.isRunning}
                onRun={(code) => onCellRun(cell.id, code)}
                onChange={(code) => onCellChange(cell.id, code)}
                onDelete={() => onCellDelete(cell.id)}
              />
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
