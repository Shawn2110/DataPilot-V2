import * as vscode from "vscode";
import { SidecarClient } from "../sidecar/sidecarClient";

/**
 * MessageHandler routes messages between the React webview and the Python sidecar.
 *
 * Message flow:
 *   React UI → postMessage({type: 'upload:request', ...})
 *     → MessageHandler receives it
 *       → Calls the appropriate SidecarClient method
 *         → Sends the result back to React via webview.postMessage()
 *
 * This is the "glue" layer. The React app doesn't know about HTTP.
 * The sidecar doesn't know about VS Code. This handler translates between them.
 */
export class MessageHandler {
  constructor(
    private client: SidecarClient,
    private outputChannel: vscode.OutputChannel
  ) {}

  /**
   * Handle an incoming message from the React webview.
   *
   * Each message has a 'type' field that determines what action to take.
   * This is a discriminated union pattern — common in message-passing systems.
   */
  async handleMessage(message: any, webview: vscode.Webview): Promise<void> {
    this.outputChannel.appendLine(`[webview → ext] ${message.type}`);

    switch (message.type) {
      case "upload:request":
        await this.handleUpload(message, webview);
        break;

      case "analyze:start":
        await this.handleAnalyze(message, webview);
        break;

      case "results:get":
        await this.handleGetResults(message, webview);
        break;

      case "predict:request":
        await this.handlePredict(message, webview);
        break;

      default:
        this.outputChannel.appendLine(`Unknown message type: ${message.type}`);
    }
  }

  /**
   * Handle file upload.
   * 1. Call sidecar to upload the file
   * 2. Send preview data back to the webview
   */
  private async handleUpload(message: any, webview: vscode.Webview): Promise<void> {
    try {
      const result = await this.client.uploadDataset(message.filePath);
      webview.postMessage({
        type: "upload:complete",
        data: result,
      });
    } catch (err) {
      webview.postMessage({
        type: "upload:error",
        error: String(err),
      });
    }
  }

  /**
   * Handle analysis — this is the main pipeline trigger.
   *
   * Flow:
   * 1. Create a project on the sidecar
   * 2. Start analysis (returns SSE stream)
   * 3. Read SSE events one by one
   * 4. Forward each event to the React webview in real-time
   *
   * SSE format (each line from the server):
   *   event: pipeline
   *   data: {"type": "tool_start", "tool": "eda"}
   *
   * We parse these lines and forward the JSON to the webview.
   */
  private async handleAnalyze(message: any, webview: vscode.Webview): Promise<void> {
    try {
      // Step 1: Create the project
      const project = await this.client.createProject({
        dataset_path: message.datasetPath,
        target_column: message.targetColumn,
        task_type: message.taskType,
      });

      webview.postMessage({
        type: "project:created",
        projectId: project.project_id,
      });

      // Step 2: Start analysis and read SSE stream
      const response = await this.client.analyze(project.project_id);

      if (!response.body) {
        throw new Error("No response body from analyze endpoint");
      }

      // Step 3: Read the SSE stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        // Decode the binary chunk to text and add to buffer
        buffer += decoder.decode(value, { stream: true });

        // SSE events are separated by double newlines
        // Each event has "data: {json}\n\n"
        const lines = buffer.split("\n");
        buffer = lines.pop() || ""; // Keep the incomplete last line

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const eventData = JSON.parse(line.slice(6));
              // Forward the event to the React webview
              webview.postMessage({
                type: "pipeline:event",
                ...eventData,
              });
            } catch {
              // Malformed JSON — skip
            }
          }
        }
      }

      // Pipeline finished
      webview.postMessage({ type: "pipeline:complete" });
    } catch (err) {
      webview.postMessage({
        type: "pipeline:error",
        error: String(err),
      });
    }
  }

  /** Fetch and forward final results */
  private async handleGetResults(message: any, webview: vscode.Webview): Promise<void> {
    try {
      const results = await this.client.getResults(message.projectId);
      webview.postMessage({
        type: "results:data",
        data: results,
      });
    } catch (err) {
      webview.postMessage({
        type: "results:error",
        error: String(err),
      });
    }
  }

  /** Run prediction with trained model */
  private async handlePredict(message: any, webview: vscode.Webview): Promise<void> {
    try {
      const result = await this.client.predict(message.projectId, message.features);
      webview.postMessage({
        type: "predict:result",
        data: result,
      });
    } catch (err) {
      webview.postMessage({
        type: "predict:error",
        error: String(err),
      });
    }
  }
}
