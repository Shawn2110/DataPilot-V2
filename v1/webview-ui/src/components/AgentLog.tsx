import { useState, useRef, useEffect } from "react";
import type { PipelineEvent } from "../types/messages";

/**
 * AgentLog — Shows the AI agent's reasoning stream.
 *
 * This is the "transparency" feature of DataPilot.
 * Users can see exactly what the agent is thinking and doing:
 *   - "Thinking..." — the LLM is generating
 *   - "Calling tool: eda" — the agent decided to run EDA
 *   - "Tool result: Found 3 outlier columns" — tool output
 *
 * Collapsible at the bottom of the UI.
 */

interface Props {
  logs: PipelineEvent[];
}

export function AgentLog({ logs }: Props) {
  const [isExpanded, setIsExpanded] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (isExpanded) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs.length, isExpanded]);

  return (
    <div className="border-t border-vscode-border bg-vscode-input-bg/50">
      {/* Toggle button */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-3 py-1.5 text-xs hover:bg-vscode-input-bg"
      >
        <span className="font-medium opacity-70">
          Agent Log ({logs.length} events)
        </span>
        <span className="opacity-40">{isExpanded ? "▼" : "▲"}</span>
      </button>

      {/* Log content */}
      {isExpanded && (
        <div className="max-h-48 overflow-y-auto px-3 pb-2 space-y-1">
          {logs.map((log, i) => (
            <LogEntry key={i} log={log} />
          ))}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}

function LogEntry({ log }: { log: PipelineEvent }) {
  const getIcon = () => {
    switch (log.type) {
      case "agent_thinking": return "💭";
      case "tool_start": return "🔧";
      case "tool_end": return "✅";
      case "agent_action": return "🎯";
      case "agent_finish": return "🏁";
      case "pipeline_start": return "🚀";
      case "pipeline_complete": return "🎉";
      case "pipeline_error": return "❌";
      default: return "📋";
    }
  };

  const getMessage = () => {
    switch (log.type) {
      case "agent_thinking": return "Agent is thinking...";
      case "tool_start": return `Running: ${log.tool}`;
      case "tool_end": return `Done: ${log.output_preview?.slice(0, 100) || "completed"}`;
      case "agent_action": return `Action: ${log.tool}${log.thought ? ` — ${log.thought.slice(0, 100)}` : ""}`;
      case "agent_finish": return `Summary: ${log.summary?.slice(0, 200) || "Analysis complete"}`;
      case "pipeline_start": return log.message || "Starting pipeline...";
      case "pipeline_complete": return log.summary || "Pipeline completed!";
      case "pipeline_error": return `Error: ${log.message}`;
      default: return JSON.stringify(log).slice(0, 100);
    }
  };

  return (
    <div className="flex gap-1.5 text-[11px] leading-relaxed">
      <span className="shrink-0">{getIcon()}</span>
      <span className="opacity-70 break-words">{getMessage()}</span>
    </div>
  );
}
