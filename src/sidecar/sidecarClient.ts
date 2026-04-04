import * as fs from "fs";
import * as path from "path";

/**
 * SidecarClient is a typed HTTP client for the Python FastAPI backend.
 *
 * Why not just use fetch() directly?
 *   1. Centralizes all API URLs in one place
 *   2. Adds TypeScript types for request/response
 *   3. Handles errors consistently
 *   4. Makes it easy to swap the backend URL (e.g., for testing)
 *
 * Every method corresponds to one FastAPI endpoint.
 */
export class SidecarClient {
  constructor(private baseUrl: string) {}

  /** Check if the sidecar is alive */
  async health(): Promise<boolean> {
    try {
      const res = await fetch(`${this.baseUrl}/health`);
      return res.ok;
    } catch {
      return false;
    }
  }

  /**
   * Upload a dataset file (CSV or Excel) to the backend.
   *
   * We read the file from disk and send it as multipart/form-data,
   * which is the standard way to upload files over HTTP.
   */
  async uploadDataset(filePath: string): Promise<UploadResponse> {
    const fileBuffer = fs.readFileSync(filePath);
    const fileName = path.basename(filePath);

    // Create a Blob from the file buffer (Node 18+ supports Blob)
    const blob = new Blob([fileBuffer]);

    const formData = new FormData();
    formData.append("file", blob, fileName);

    const res = await fetch(`${this.baseUrl}/upload-dataset`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      throw new Error(`Upload failed: ${res.statusText}`);
    }

    return res.json() as Promise<UploadResponse>;
  }

  /**
   * Create a project and trigger the ML pipeline.
   *
   * Returns a ReadableStream of SSE (Server-Sent Events).
   * The extension reads this stream and forwards events to the webview.
   */
  async createProject(config: ProjectConfig): Promise<CreateProjectResponse> {
    const res = await fetch(`${this.baseUrl}/projects/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });

    if (!res.ok) {
      throw new Error(`Create project failed: ${res.statusText}`);
    }

    return res.json() as Promise<CreateProjectResponse>;
  }

  /**
   * Start analysis — returns an SSE stream.
   *
   * SSE (Server-Sent Events) is a protocol where the server sends
   * a continuous stream of events over HTTP. Each event looks like:
   *   data: {"type": "tool_start", "tool": "eda"}
   *
   * The browser/Node reads these line-by-line as they arrive.
   * This is how we get real-time pipeline progress updates.
   */
  async analyze(projectId: string): Promise<Response> {
    const res = await fetch(`${this.baseUrl}/projects/${projectId}/analyze`, {
      method: "POST",
    });

    if (!res.ok) {
      throw new Error(`Analyze failed: ${res.statusText}`);
    }

    return res; // Return raw response so caller can read the SSE stream
  }

  /** Get final results after pipeline completes */
  async getResults(projectId: string): Promise<PipelineResults> {
    const res = await fetch(`${this.baseUrl}/projects/${projectId}/results`);

    if (!res.ok) {
      throw new Error(`Get results failed: ${res.statusText}`);
    }

    return res.json() as Promise<PipelineResults>;
  }

  /** Run prediction using the trained model */
  async predict(projectId: string, features: Record<string, any>[]): Promise<PredictionResponse> {
    const res = await fetch(`${this.baseUrl}/projects/${projectId}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ instances: features }),
    });

    if (!res.ok) {
      throw new Error(`Predict failed: ${res.statusText}`);
    }

    return res.json() as Promise<PredictionResponse>;
  }
}

// --- Type definitions ---
// These match the JSON shapes returned by the FastAPI backend

export interface UploadResponse {
  dataset_id: string;
  file_path: string;
  shape: [number, number];
  columns: string[];
  preview: Record<string, any>[];
}

export interface ProjectConfig {
  dataset_path: string;
  target_column?: string;
  task_type?: "classification" | "regression";
}

export interface CreateProjectResponse {
  project_id: string;
  status: string;
}

export interface PipelineResults {
  status: "running" | "completed" | "error";
  profile?: any;
  eda?: any;
  preprocessing?: any;
  model_comparison?: any;
  evaluation?: any;
  explainability?: any;
  report_path?: string;
  model_path?: string;
}

export interface PredictionResponse {
  predictions: any[];
  explanations?: any[];
}
