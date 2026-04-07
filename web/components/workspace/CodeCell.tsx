"use client";

import { useState } from "react";
import Editor from "@monaco-editor/react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

/**
 * CodeCell — A single executable code cell (like Jupyter, but built-in).
 *
 * Features:
 *   - Monaco editor (same editor as VS Code) for code editing
 *   - Run button → sends code to backend for execution
 *   - Output display (text, errors)
 *   - Cell number indicator
 */
export function CodeCell({
  code,
  cellIndex,
  output,
  isRunning,
  onRun,
  onChange,
  onDelete,
}: {
  code: string;
  cellIndex: number;
  output?: string;
  isRunning?: boolean;
  onRun: (code: string) => void;
  onChange: (code: string) => void;
  onDelete: () => void;
}) {
  const [isEditorReady, setIsEditorReady] = useState(false);
  const lineCount = Math.max(code.split("\n").length, 3);
  const editorHeight = Math.min(Math.max(lineCount * 20, 60), 300);

  return (
    <Card className="border-border overflow-hidden">
      {/* Cell header */}
      <div className="flex items-center justify-between px-3 py-1 bg-muted/50 border-b border-border">
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-[10px] font-mono">
            [{cellIndex}]
          </Badge>
          <span className="text-[10px] text-muted-foreground">Python</span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-[11px]"
            onClick={() => onRun(code)}
            disabled={isRunning || !code.trim()}
          >
            {isRunning ? "Running..." : "Run"}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-[11px] text-muted-foreground"
            onClick={onDelete}
          >
            Delete
          </Button>
        </div>
      </div>

      {/* Monaco editor */}
      <div style={{ height: editorHeight }}>
        <Editor
          height="100%"
          defaultLanguage="python"
          value={code}
          onChange={(val) => onChange(val || "")}
          onMount={() => setIsEditorReady(true)}
          theme="vs-dark"
          options={{
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            fontSize: 13,
            lineNumbers: "on",
            folding: false,
            wordWrap: "on",
            padding: { top: 8, bottom: 8 },
            overviewRulerLanes: 0,
            hideCursorInOverviewRuler: true,
            overviewRulerBorder: false,
            scrollbar: {
              vertical: "hidden",
              horizontal: "auto",
            },
          }}
        />
      </div>

      {/* Output */}
      {output && (
        <div className="border-t border-border bg-background px-4 py-2">
          <pre className="text-xs font-mono whitespace-pre-wrap text-muted-foreground leading-relaxed">
            {output}
          </pre>
        </div>
      )}
    </Card>
  );
}
