"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { ChatSidebar } from "../../components/ChatSidebar";
import { JupyterFrame } from "../../components/JupyterFrame";

/**
 * Workspace page — The Kaggle-like split view.
 *
 * Layout:
 *   +----------------------------------+-------------+
 *   |                                  |             |
 *   |     JupyterLab (iframe)          |   Chat      |
 *   |     70% width                    |   Sidebar   |
 *   |                                  |   30%       |
 *   |                                  |             |
 *   +----------------------------------+-------------+
 *
 * The JupyterLab iframe connects to a Jupyter Server.
 * The Chat sidebar sends messages to the FastAPI backend.
 * When the agent generates code, the backend inserts it into
 * the notebook via Jupyter Server REST API.
 */
function WorkspaceContent() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session") || "";

  const jupyterUrl = process.env.NEXT_PUBLIC_JUPYTER_URL || "http://localhost:8888";
  const jupyterToken = process.env.NEXT_PUBLIC_JUPYTER_TOKEN || "datapilot-dev-token";

  return (
    <div className="flex h-screen bg-gray-950">
      {/* JupyterLab iframe — 70% */}
      <div className="flex-1 min-w-0">
        <JupyterFrame
          baseUrl={jupyterUrl}
          token={jupyterToken}
          notebookPath={`work/${sessionId}.ipynb`}
        />
      </div>

      {/* Chat sidebar — 30% */}
      <div className="w-[380px] border-l border-gray-800 flex flex-col">
        <ChatSidebar sessionId={sessionId} />
      </div>
    </div>
  );
}

export default function WorkspacePage() {
  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center bg-gray-950 text-white">Loading workspace...</div>}>
      <WorkspaceContent />
    </Suspense>
  );
}
