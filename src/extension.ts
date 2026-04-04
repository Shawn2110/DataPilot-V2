import * as vscode from "vscode";
import { SidecarManager } from "./sidecar/sidecarManager";
import { SidecarClient } from "./sidecar/sidecarClient";
import { DataPilotWebviewProvider } from "./webview/webviewProvider";

// These hold references so we can clean up when the extension closes
let sidecar: SidecarManager | undefined;
let client: SidecarClient | undefined;

/**
 * activate() is called by VS Code when the extension is first used.
 *
 * Flow:
 * 1. Start the Python FastAPI server as a child process
 * 2. Create an HTTP client to talk to it
 * 3. Register the webview (React UI) in the sidebar
 * 4. Register commands (upload, open panel)
 */
export async function activate(context: vscode.ExtensionContext) {
  const outputChannel = vscode.window.createOutputChannel("DataPilot");
  outputChannel.appendLine("DataPilot is starting...");

  // --- Step 1: Start the Python sidecar server ---
  sidecar = new SidecarManager(context, outputChannel);
  try {
    await sidecar.start();
    outputChannel.appendLine(`Sidecar running on port ${sidecar.getPort()}`);
  } catch (err) {
    vscode.window.showErrorMessage(
      `DataPilot: Failed to start Python backend. Make sure Python is installed. Error: ${err}`
    );
    return;
  }

  // --- Step 2: Create HTTP client for the sidecar ---
  client = new SidecarClient(`http://127.0.0.1:${sidecar.getPort()}`);

  // --- Step 3: Register the webview provider ---
  // This creates the React UI panel in the DataPilot sidebar tab
  const webviewProvider = new DataPilotWebviewProvider(
    context,
    client,
    outputChannel
  );

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      "datapilot.mainView",
      webviewProvider
    )
  );

  // --- Step 4: Register commands ---
  context.subscriptions.push(
    vscode.commands.registerCommand("datapilot.openPanel", () => {
      // Focus the DataPilot sidebar panel
      vscode.commands.executeCommand("datapilot.mainView.focus");
    }),

    vscode.commands.registerCommand("datapilot.uploadDataset", async () => {
      // Open file picker filtered to CSV/Excel files
      const fileUri = await vscode.window.showOpenDialog({
        canSelectMany: false,
        filters: {
          "Datasets": ["csv", "xlsx", "xls"],
        },
        title: "Select a dataset to analyze",
      });

      if (fileUri && fileUri[0]) {
        // Send the file path to the webview so it can trigger upload
        webviewProvider.postMessage({
          type: "file:selected",
          filePath: fileUri[0].fsPath,
        });
      }
    })
  );

  // Clean up the sidecar when extension is disposed
  context.subscriptions.push({
    dispose: () => {
      sidecar?.stop();
    },
  });

  outputChannel.appendLine("DataPilot is ready!");
  vscode.window.showInformationMessage("DataPilot is ready!");
}

/**
 * deactivate() is called when VS Code closes or the extension is disabled.
 * We kill the Python server here.
 */
export function deactivate() {
  sidecar?.stop();
}
