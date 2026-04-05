import * as fs from "fs";
import * as path from "path";

/**
 * BackendClient — HTTP + SSE client for the FastAPI backend.
 *
 * Handles:
 *   - POST /api/chat (SSE stream) — send message, stream response
 *   - POST /api/upload — upload dataset file
 *   - GET /health — check backend is alive
 */

export interface SSEEvent {
  type: "thinking" | "code" | "message" | "error" | "done";
  content?: string;
  session_id?: string;
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

  /**
   * Send a chat message and read the SSE stream.
   *
   * The callback is called for each SSE event:
   *   - {type: "thinking", content: "..."} — agent is reasoning
   *   - {type: "code", content: "import pandas..."} — generated code
   *   - {type: "message", content: "Here's your plot."} — text response
   *   - {type: "done"} — stream finished
   */
  async chat(
    sessionId: string | null,
    message: string,
    onEvent: (event: SSEEvent) => void
  ): Promise<void> {
    const res = await fetch(`${this.baseUrl}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        message,
      }),
    });

    if (!res.ok || !res.body) {
      onEvent({ type: "error", content: `Backend error: ${res.statusText}` });
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith("data: ")) {
          try {
            const event: SSEEvent = JSON.parse(trimmed.slice(6));
            onEvent(event);
          } catch {
            // Malformed JSON — skip
          }
        }
      }
    }
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
