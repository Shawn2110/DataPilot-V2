import * as vscode from "vscode";
import { ChatViewProvider } from "./chat/ChatViewProvider";
import { NotebookBridge } from "./notebook/NotebookBridge";
import { BackendClient } from "./backend/BackendClient";
import {
  configureInteractively,
  ensureConfig,
  loadConfig,
} from "./config";

/**
 * v2 Extension entry point.
 *
 * Activates only when a Jupyter notebook (.ipynb) is open. The chat
 * sidebar generates code that gets inserted into notebook cells. The
 * provider/key configured via SecretStorage flows to the backend on
 * every request as X-Datapilot-* headers — nothing is cached server-side.
 */
export function activate(context: vscode.ExtensionContext) {
  const outputChannel = vscode.window.createOutputChannel("DataPilot");
  outputChannel.appendLine("DataPilot v2 activated");

  const backendUrl =
    vscode.workspace.getConfiguration("datapilot").get<string>("backendUrl") ||
    "http://localhost:8000";

  // Headers callback: read provider/key fresh every call so a /reconfigure
  // takes effect immediately without restarting the extension.
  const client = new BackendClient(backendUrl, async () => {
    const cfg = await loadConfig(context);
    if (!cfg) return null;
    return {
      provider: cfg.provider,
      model: cfg.model,
      apiKey: cfg.apiKey,
      apiBase: cfg.apiBase,
    };
  });

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
    }),
    vscode.commands.registerCommand("datapilot.configure", async () => {
      const cfg = await configureInteractively(context);
      if (cfg) {
        vscode.window.showInformationMessage(
          `DataPilot using ${cfg.provider} (${cfg.model})`
        );
      }
    })
  );

  outputChannel.appendLine(`Backend URL: ${backendUrl}`);

  // First-run prompt — only if there's no provider configured yet.
  loadConfig(context).then((cfg) => {
    if (!cfg) {
      outputChannel.appendLine("No provider configured; prompting user.");
      ensureConfig(context).then((picked) => {
        if (picked) {
          outputChannel.appendLine(
            `Configured: ${picked.provider} / ${picked.model}`
          );
        }
      });
    } else {
      outputChannel.appendLine(`Provider: ${cfg.provider} / ${cfg.model}`);
    }
  });

  outputChannel.appendLine("DataPilot v2 ready!");
}

export function deactivate() {}
