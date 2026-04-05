import { useState } from "react";
import vscode from "../vscode";
import type { UploadData } from "../types/messages";

/**
 * UploadPanel — File upload and dataset preview.
 *
 * Shows:
 *   1. A button to open VS Code's file picker
 *   2. After upload: dataset shape, columns, and first 5 rows
 *   3. Target column selector + start button
 */

interface Props {
  uploadData: UploadData | null;
  onStartAnalysis: (targetColumn?: string) => void;
  isRunning: boolean;
}

export function UploadPanel({ uploadData, onStartAnalysis, isRunning }: Props) {
  const [targetColumn, setTargetColumn] = useState<string>("");

  function handleUploadClick() {
    // Ask the extension to open a file picker
    // The extension will send back a 'file:selected' message
    vscode.postMessage({ type: "upload:request", filePath: "" });
  }

  if (!uploadData) {
    // No data uploaded yet — show the upload button
    return (
      <div className="flex flex-col items-center justify-center py-12 border-2 border-dashed border-vscode-border rounded-lg">
        <div className="text-4xl mb-3">📊</div>
        <h2 className="text-base font-semibold mb-1">Upload a Dataset</h2>
        <p className="text-xs opacity-60 mb-4">CSV or Excel files supported</p>
        <button
          onClick={handleUploadClick}
          className="px-4 py-2 rounded text-sm bg-vscode-button-bg text-vscode-button-fg hover:bg-vscode-button-hover"
        >
          Choose File
        </button>
      </div>
    );
  }

  // Data uploaded — show preview + analysis controls
  return (
    <div className="space-y-3">
      {/* Dataset info */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold">Dataset Loaded</h2>
          <p className="text-xs opacity-60">
            {uploadData.shape[0]} rows × {uploadData.shape[1]} columns
          </p>
        </div>
        <button
          onClick={handleUploadClick}
          className="text-xs px-2 py-1 rounded bg-vscode-input-bg hover:opacity-80"
        >
          Change
        </button>
      </div>

      {/* Column preview */}
      <div className="text-xs">
        <span className="opacity-60">Columns: </span>
        {uploadData.columns.map((col, i) => (
          <span key={col}>
            <span className="text-vscode-fg">{col}</span>
            <span className="opacity-40 text-[10px] ml-0.5">({uploadData.dtypes[col]})</span>
            {i < uploadData.columns.length - 1 && <span className="opacity-30">, </span>}
          </span>
        ))}
      </div>

      {/* Data preview table */}
      <div className="overflow-x-auto border border-vscode-border rounded">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-vscode-input-bg">
              {uploadData.columns.map((col) => (
                <th key={col} className="px-2 py-1 text-left font-medium whitespace-nowrap">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {uploadData.preview.map((row, i) => (
              <tr key={i} className="border-t border-vscode-border">
                {uploadData.columns.map((col) => (
                  <td key={col} className="px-2 py-1 whitespace-nowrap opacity-80">
                    {String(row[col] ?? "—")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Analysis controls */}
      <div className="flex items-end gap-2">
        <div className="flex-1">
          <label className="text-xs opacity-60 block mb-1">Target Column (what to predict)</label>
          <select
            value={targetColumn}
            onChange={(e) => setTargetColumn(e.target.value)}
            className="w-full px-2 py-1.5 text-xs rounded bg-vscode-input-bg text-vscode-input-fg border border-vscode-border"
          >
            <option value="">Auto-detect</option>
            {uploadData.columns.map((col) => (
              <option key={col} value={col}>{col}</option>
            ))}
          </select>
        </div>
        <button
          onClick={() => onStartAnalysis(targetColumn || undefined)}
          disabled={isRunning}
          className="px-4 py-1.5 text-xs rounded bg-vscode-button-bg text-vscode-button-fg hover:bg-vscode-button-hover disabled:opacity-50"
        >
          {isRunning ? "Running..." : "Analyze"}
        </button>
      </div>
    </div>
  );
}
