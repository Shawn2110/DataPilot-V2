import * as vscode from "vscode";
import { ChatViewProvider } from "./chat/ChatViewProvider";
import { NotebookBridge } from "./notebook/NotebookBridge";
import { BackendClient } from "./backend/BackendClient";

/**
 * v2 Extension entry point.
 *
 * Activates ONLY when a Jupyter notebook (.ipynb) is open.
 * Creates a chat sidebar where users type data science instructions.
 * The agent generates code that gets inserted into notebook cells.
 */
export function activate(context: vscode.ExtensionContext) {
  const outputChannel = vscode.window.createOutputChannel("DataPilot");
  outputChannel.appendLine("DataPilot v2 activated");

  const backendUrl =
    vscode.workspace.getConfiguration("datapilot").get<string>("backendUrl") ||
    "http://localhost:8000";

  const client = new BackendClient(backendUrl);
  const notebookBridge = new NotebookBridge();

  const chatProvider = new ChatViewProvider(
    context,
    client,
    notebookBridge,
    outputChannel
  );

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      "datapilot.chatView",
      chatProvider
    ),
    vscode.commands.registerCommand("datapilot.openChat", () => {
      vscode.commands.executeCommand("datapilot.chatView.focus");
    })
  );

  outputChannel.appendLine(`Backend URL: ${backendUrl}`);
  outputChannel.appendLine("DataPilot v2 ready!");
}

export function deactivate() {}
