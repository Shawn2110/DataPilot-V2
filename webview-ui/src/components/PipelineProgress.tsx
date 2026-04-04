import type { PipelineStep } from "../types/messages";

/**
 * PipelineProgress — Visual stepper showing pipeline progress.
 *
 * Displays the 8 pipeline steps with status icons:
 *   ⏳ pending (gray)
 *   🔄 running (blue, animated)
 *   ✅ done (green)
 *   ❌ error (red)
 */

interface Props {
  steps: PipelineStep[];
  activeTab: string;
  onTabClick: (tab: string) => void;
}

export function PipelineProgress({ steps, activeTab, onTabClick }: Props) {
  return (
    <div className="border border-vscode-border rounded-lg p-3">
      <h3 className="text-xs font-semibold mb-2 opacity-60 uppercase tracking-wide">Pipeline Progress</h3>
      <div className="space-y-1">
        {steps.map((step, i) => (
          <button
            key={step.name}
            onClick={() => onTabClick(step.name)}
            className={`w-full flex items-center gap-2 px-2 py-1.5 rounded text-xs text-left transition-colors ${
              activeTab === step.name ? "bg-vscode-input-bg" : "hover:bg-vscode-input-bg/50"
            }`}
          >
            {/* Step number + status icon */}
            <span className="flex items-center justify-center w-5 h-5 rounded-full text-[10px] font-bold shrink-0" style={{
              backgroundColor: step.status === "done" ? "var(--vscode-testing-iconPassed, #4caf50)" :
                              step.status === "running" ? "var(--vscode-progressBar-background, #0078d4)" :
                              step.status === "error" ? "var(--vscode-testing-iconFailed, #f44336)" :
                              "var(--vscode-badge-background, #666)",
              color: "white",
            }}>
              {step.status === "done" ? "✓" :
               step.status === "running" ? "•" :
               step.status === "error" ? "✗" :
               i + 1}
            </span>

            {/* Step label */}
            <span className={`flex-1 ${step.status === "running" ? "font-medium" : "opacity-80"}`}>
              {step.label}
            </span>

            {/* Running indicator */}
            {step.status === "running" && (
              <span className="animate-pulse text-[10px] opacity-60">running...</span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
