"use client";

import { useSearchParams } from "next/navigation";
import { useState, useCallback, Suspense } from "react";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { NotebookPanel, type Cell } from "@/components/workspace/NotebookPanel";

/**
 * Workspace page — Split view: Notebook (left) + Chat (right).
 *
 * Layout:
 *   +----------------------------------+-------------+
 *   |  Cell 1: import pandas as pd     |  DataPilot  |
 *   |  [Run]                           |  Chat       |
 *   |  > Output: ...                   |             |
 *   |                                  |  User: show |
 *   |  Cell 2: df.head()               |  the data   |
 *   |  [Run]                           |             |
 *   +----------------------------------+-------------+
 *
 * The agent pushes code into cells via the onCodeGenerated callback.
 * User can edit cells in Monaco editor and click Run.
 */
function WorkspaceContent() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session") || "";
  const [cells, setCells] = useState<Cell[]>([]);

  // Called by ChatSidebar when the agent generates code
  const handleCodeGenerated = useCallback((code: string) => {
    const newCell: Cell = {
      id: Date.now().toString() + Math.random(),
      code,
    };
    setCells((prev) => [...prev, newCell]);
  }, []);

  function handleCellChange(id: string, code: string) {
    setCells((prev) =>
      prev.map((c) => (c.id === id ? { ...c, code } : c))
    );
  }

  function handleCellRun(id: string, code: string) {
    // Mark cell as running
    setCells((prev) =>
      prev.map((c) => (c.id === id ? { ...c, isRunning: true, output: undefined } : c))
    );

    // Execute via backend
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8002";
    fetch(`${backendUrl}/api/execute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, code }),
    })
      .then((res) => res.json())
      .then((data) => {
        setCells((prev) =>
          prev.map((c) =>
            c.id === id
              ? {
                  ...c,
                  isRunning: false,
                  output: data.error || data.stdout || data.result || "Done (no output)",
                }
              : c
          )
        );
      })
      .catch((err) => {
        setCells((prev) =>
          prev.map((c) =>
            c.id === id
              ? { ...c, isRunning: false, output: `Error: ${err.message}` }
              : c
          )
        );
      });
  }

  function handleCellDelete(id: string) {
    setCells((prev) => prev.filter((c) => c.id !== id));
  }

  function handleAddCell() {
    setCells((prev) => [
      ...prev,
      { id: Date.now().toString(), code: "" },
    ]);
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem)] overflow-hidden">
      {/* Notebook — 65% */}
      <div className="flex-1 min-w-0">
        <NotebookPanel
          cells={cells}
          onCellChange={handleCellChange}
          onCellRun={handleCellRun}
          onCellDelete={handleCellDelete}
          onAddCell={handleAddCell}
        />
      </div>

      {/* Chat sidebar — 380px */}
      <div className="w-[380px] border-l flex flex-col">
        <ChatSidebar sessionId={sessionId} onCodeGenerated={handleCodeGenerated} />
      </div>
    </div>
  );
}

export default function WorkspacePage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-screen items-center justify-center text-muted-foreground">
          Loading workspace...
        </div>
      }
    >
      <WorkspaceContent />
    </Suspense>
  );
}
