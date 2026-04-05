import { useState, useCallback } from "react";
import { useVsCodeMessage } from "./hooks/useVsCodeMessage";
import vscode from "./vscode";
import { UploadPanel } from "./components/UploadPanel";
import { PipelineProgress } from "./components/PipelineProgress";
import { DataProfileView } from "./components/DataProfileView";
import { EDACharts } from "./components/EDACharts";
import { ModelComparison } from "./components/ModelComparison";
import { ShapExplainer } from "./components/ShapExplainer";
import { AgentLog } from "./components/AgentLog";
import type { UploadData, PipelineStep, PipelineEvent } from "./types/messages";

/**
 * Main App component — the root of the DataPilot UI.
 *
 * Layout:
 *   ┌──────────────────────────────────┐
 *   │  Upload Panel (file picker)      │
 *   ├──────────────────────────────────┤
 *   │  Pipeline Progress (stepper)     │
 *   ├──────────────────────────────────┤
 *   │  Active Tab Content:             │
 *   │    Profile | EDA | Models | SHAP │
 *   ├──────────────────────────────────┤
 *   │  Agent Log (reasoning stream)    │
 *   └──────────────────────────────────┘
 *
 * State management:
 *   All state lives here in the top-level App component.
 *   Components receive data via props and send actions via callbacks.
 *   This is the simplest React architecture — no Redux/Zustand needed.
 */

// Define the 8 pipeline steps for the progress tracker
const PIPELINE_STEPS: PipelineStep[] = [
  { name: "detect_problem", label: "Problem Detection", status: "pending" },
  { name: "profile_data", label: "Data Profiling", status: "pending" },
  { name: "run_eda", label: "Exploratory Analysis", status: "pending" },
  { name: "preprocess_data", label: "Preprocessing", status: "pending" },
  { name: "engineer_features", label: "Feature Engineering", status: "pending" },
  { name: "train_models", label: "Model Training", status: "pending" },
  { name: "evaluate_model", label: "Evaluation", status: "pending" },
  { name: "explain_model", label: "Explainability", status: "pending" },
];

export default function App() {
  // --- State ---
  const [uploadData, setUploadData] = useState<UploadData | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [steps, setSteps] = useState<PipelineStep[]>(PIPELINE_STEPS);
  const [activeTab, setActiveTab] = useState<string>("upload");
  const [results, setResults] = useState<any>(null);
  const [agentLogs, setAgentLogs] = useState<PipelineEvent[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Handle incoming messages from the VS Code extension.
   *
   * This is the main event loop of the UI. Every event from the pipeline
   * flows through here and updates the appropriate state.
   */
  const handleMessage = useCallback((message: any) => {
    switch (message.type) {
      case "file:selected":
        // User picked a file via VS Code file dialog
        vscode.postMessage({ type: "upload:request", filePath: message.filePath });
        break;

      case "upload:complete":
        setUploadData(message.data);
        setError(null);
        setActiveTab("upload");
        break;

      case "upload:error":
        setError(`Upload failed: ${message.error}`);
        break;

      case "project:created":
        setProjectId(message.projectId);
        break;

      case "pipeline:event":
        handlePipelineEvent(message);
        break;

      case "pipeline:complete":
        setIsRunning(false);
        // Fetch final results
        if (projectId) {
          vscode.postMessage({ type: "results:get", projectId });
        }
        break;

      case "pipeline:error":
        setIsRunning(false);
        setError(`Pipeline error: ${message.error}`);
        break;

      case "results:data":
        setResults(message.data);
        break;
    }
  }, [projectId]);

  useVsCodeMessage(handleMessage);

  /**
   * Handle pipeline events — update step status and agent logs.
   */
  function handlePipelineEvent(event: any) {
    // Add to agent log
    setAgentLogs((prev) => [...prev, event]);

    if (event.type === "tool_start" && event.tool) {
      // Mark the tool as "running"
      setSteps((prev) =>
        prev.map((s) =>
          s.name === event.tool ? { ...s, status: "running" as const } : s
        )
      );
      setActiveTab(event.tool);
    }

    if (event.type === "tool_end") {
      // Mark the most recent "running" step as "done"
      setSteps((prev) => {
        const updated = [...prev];
        const runningIdx = updated.findIndex((s) => s.status === "running");
        if (runningIdx >= 0) {
          updated[runningIdx] = { ...updated[runningIdx], status: "done" };
        }
        return updated;
      });
    }

    if (event.type === "pipeline_complete") {
      setSteps((prev) => prev.map((s) => ({ ...s, status: "done" as const })));
    }
  }

  /**
   * Start the analysis pipeline.
   */
  function handleStartAnalysis(targetColumn?: string) {
    if (!uploadData) return;

    setIsRunning(true);
    setError(null);
    setAgentLogs([]);
    setSteps(PIPELINE_STEPS.map((s) => ({ ...s, status: "pending" as const })));

    vscode.postMessage({
      type: "analyze:start",
      datasetPath: uploadData.file_path,
      targetColumn,
    });
  }

  // --- Render ---
  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* Header */}
      <div className="p-3 border-b border-vscode-border">
        <h1 className="text-lg font-bold">DataPilot</h1>
        <p className="text-xs opacity-60">AI-Powered Data Science Copilot</p>
      </div>

      {/* Error banner */}
      {error && (
        <div className="mx-3 mt-2 p-2 text-sm rounded bg-red-500/20 text-red-400 border border-red-500/30">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">dismiss</button>
        </div>
      )}

      {/* Main content — scrollable */}
      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        {/* Upload section */}
        <UploadPanel
          uploadData={uploadData}
          onStartAnalysis={handleStartAnalysis}
          isRunning={isRunning}
        />

        {/* Pipeline progress */}
        {(isRunning || steps.some((s) => s.status !== "pending")) && (
          <PipelineProgress steps={steps} activeTab={activeTab} onTabClick={setActiveTab} />
        )}

        {/* Results tabs */}
        {results && (
          <div className="space-y-4">
            {/* Tab buttons */}
            <div className="flex gap-1 flex-wrap">
              {["profile", "eda", "models", "shap"].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-3 py-1 text-xs rounded ${
                    activeTab === tab
                      ? "bg-vscode-button-bg text-vscode-button-fg"
                      : "bg-vscode-input-bg text-vscode-fg opacity-70 hover:opacity-100"
                  }`}
                >
                  {tab === "profile" ? "Profile" : tab === "eda" ? "EDA" : tab === "models" ? "Models" : "SHAP"}
                </button>
              ))}
            </div>

            {/* Tab content */}
            {activeTab === "profile" && results.profile && (
              <DataProfileView profile={results.profile} />
            )}
            {activeTab === "eda" && results.eda && (
              <EDACharts eda={results.eda} />
            )}
            {activeTab === "models" && results.model_comparison && (
              <ModelComparison
                cvResults={results.model_comparison}
                bestModel={results.best_model}
                evaluation={results.evaluation}
                taskType={results.task_type}
              />
            )}
            {activeTab === "shap" && results.explainability && (
              <ShapExplainer importance={results.explainability} />
            )}
          </div>
        )}
      </div>

      {/* Agent log — fixed at bottom */}
      {agentLogs.length > 0 && <AgentLog logs={agentLogs} />}
    </div>
  );
}
