import * as fs from "fs";
import * as path from "path";

/**
 * BackendClient — HTTP client for the FastAPI backend.
 *
 *   POST /api/chat   — single-shot JSON ({explanation, code, source})
 *   POST /api/upload — upload a dataset file
 *   GET  /health     — health check
 */

export type ChatSource = "template" | "codegen" | "qa";

export interface ChatResponse {
  session_id: string;
  explanation: string;
  code: string | null;
  source: ChatSource;
}

export interface UploadResponse {
  session_id: string;
  file_path: string;
  data_info: {
    columns: string[];
    dtypes: Record<string, string>;
    shape: [number, number];
    head: Record<string, any>[];
  };
  load_code: string;
}

export class BackendClient {
  constructor(private baseUrl: string) {}

  async health(): Promise<boolean> {
    try {
      const res = await fetch(`${this.baseUrl}/health`);
      return res.ok;
    } catch {
      return false;
    }
  }

  async chat(sessionId: string | null, message: string): Promise<ChatResponse> {
    const res = await fetch(`${this.baseUrl}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
    });

    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new Error(`backend ${res.status}: ${body || res.statusText}`);
    }

    return (await res.json()) as ChatResponse;
  }

  /**
   * Upload a dataset file to the backend.
   */
  async upload(
    filePath: string,
    sessionId: string | null
  ): Promise<UploadResponse> {
    const fileBuffer = fs.readFileSync(filePath);
    const fileName = path.basename(filePath);
    const blob = new Blob([fileBuffer]);

    const formData = new FormData();
    formData.append("file", blob, fileName);
    if (sessionId) {
      formData.append("session_id", sessionId);
    }

    const res = await fetch(`${this.baseUrl}/api/upload`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      throw new Error(`Upload failed: ${res.statusText}`);
    }

    return res.json() as Promise<UploadResponse>;
  }
}
