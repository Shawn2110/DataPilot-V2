/**
 * Message types exchanged between the React webview and VS Code extension.
 *
 * This is a "discriminated union" — each message has a `type` field
 * that tells you exactly what shape the rest of the object has.
 * TypeScript can narrow the type based on the `type` field.
 *
 * Example:
 *   if (msg.type === 'upload:complete') {
 *     msg.data.columns  // TypeScript knows this exists!
 *   }
 */

// --- Messages FROM extension TO webview ---
export type IncomingMessage =
  | { type: "file:selected"; filePath: string }
  | { type: "upload:complete"; data: UploadData }
  | { type: "upload:error"; error: string }
  | { type: "project:created"; projectId: string }
  | { type: "pipeline:event"; [key: string]: any }
  | { type: "pipeline:complete" }
  | { type: "pipeline:error"; error: string }
  | { type: "results:data"; data: any }
  | { type: "predict:result"; data: any };

// --- Messages FROM webview TO extension ---
export type OutgoingMessage =
  | { type: "upload:request"; filePath: string }
  | { type: "analyze:start"; datasetPath: string; targetColumn?: string; taskType?: string }
  | { type: "results:get"; projectId: string }
  | { type: "predict:request"; projectId: string; features: Record<string, any> };

// --- Data shapes ---
export interface UploadData {
  dataset_id: string;
  file_path: string;
  shape: [number, number];
  columns: string[];
  dtypes: Record<string, string>;
  preview: Record<string, any>[];
}

export interface PipelineEvent {
  type: string;
  tool?: string;
  message?: string;
  output_preview?: string;
  thought?: string;
  summary?: string;
}

export type PipelineStep = {
  name: string;
  label: string;
  status: "pending" | "running" | "done" | "error";
};
