import * as vscode from "vscode";
import * as path from "path";
import { SidecarClient } from "../sidecar/sidecarClient";
import { MessageHandler } from "./messageHandler";

/**
 * DataPilotWebviewProvider creates and manages the React UI panel
 * that appears in the VS Code sidebar.
 *
 * How VS Code webviews work:
 *   - A webview is essentially a sandboxed iframe inside VS Code
 *   - It can render any HTML/CSS/JS (our React app)
 *   - It communicates with the extension via postMessage (like iframe messaging)
 *   - It has strict security rules (CSP) about what it can load
 *
 * This class implements WebviewViewProvider, which VS Code calls
 * when the user opens the DataPilot panel in the sidebar.
 */
export class DataPilotWebviewProvider implements vscode.WebviewViewProvider {
  private view?: vscode.WebviewView;
  private messageHandler: MessageHandler;

  constructor(
    private context: vscode.ExtensionContext,
    private client: SidecarClient,
    private outputChannel: vscode.OutputChannel
  ) {
    this.messageHandler = new MessageHandler(client, outputChannel);
  }

  /**
   * Called by VS Code when the webview panel needs to be created.
   *
   * This is where we:
   * 1. Configure webview options (enable scripts, set resource roots)
   * 2. Generate the HTML that loads the React app
   * 3. Set up message listeners
   */
  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ): void {
    this.view = webviewView;

    // Configure the webview
    webviewView.webview.options = {
      enableScripts: true, // Allow JavaScript execution (needed for React)
      localResourceRoots: [
        // Only allow loading resources from these directories
        vscode.Uri.joinPath(this.context.extensionUri, "webview-ui", "dist"),
        vscode.Uri.joinPath(this.context.extensionUri, "media"),
      ],
    };

    // Set the HTML content (this loads our React app)
    webviewView.webview.html = this.getHtmlForWebview(webviewView.webview);

    // Listen for messages FROM the React app
    // When the React app calls vscode.postMessage({type: 'upload:request'}),
    // this handler receives it and routes it to the MessageHandler
    webviewView.webview.onDidReceiveMessage(
      (message) => this.messageHandler.handleMessage(message, webviewView.webview),
      undefined,
      this.context.subscriptions
    );

    // When the webview becomes visible again after being hidden,
    // VS Code destroys and recreates it. This event lets us know.
    webviewView.onDidChangeVisibility(() => {
      if (webviewView.visible) {
        this.outputChannel.appendLine("Webview became visible");
      }
    });
  }

  /**
   * Send a message TO the React app.
   * The React app listens for these via window.addEventListener('message', ...).
   */
  postMessage(message: any): void {
    this.view?.webview.postMessage(message);
  }

  /**
   * Generate the HTML that loads the React app inside the webview.
   *
   * Key concepts:
   * - We can't use regular file:// URLs — we must use webview.asWebviewUri()
   *   to convert local file paths into special webview-safe URIs
   * - CSP (Content Security Policy) restricts what the webview can load:
   *   - Scripts: only from our extension's files
   *   - Styles: from our files + inline styles (Tailwind needs this)
   *   - Images: from our files + data: URIs (for base64 SHAP plots)
   *   - Fonts: from our files
   * - nonce: a random token that must match in both CSP and script tags,
   *   preventing injection of unauthorized scripts
   */
  private getHtmlForWebview(webview: vscode.Webview): string {
    // Convert local file paths to webview-safe URIs
    const scriptUri = webview.asWebviewUri(
      vscode.Uri.joinPath(this.context.extensionUri, "webview-ui", "dist", "main.js")
    );
    const styleUri = webview.asWebviewUri(
      vscode.Uri.joinPath(this.context.extensionUri, "webview-ui", "dist", "main.css")
    );

    // Generate a random nonce for CSP
    const nonce = getNonce();

    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="
      default-src 'none';
      style-src ${webview.cspSource} 'unsafe-inline';
      script-src 'nonce-${nonce}';
      img-src ${webview.cspSource} data:;
      font-src ${webview.cspSource};
    ">
    <link rel="stylesheet" href="${styleUri}">
    <title>DataPilot</title>
</head>
<body>
    <div id="root"></div>
    <script nonce="${nonce}" src="${scriptUri}"></script>
</body>
</html>`;
  }
}

/** Generate a random 32-character hex string for CSP nonce */
function getNonce(): string {
  let text = "";
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  for (let i = 0; i < 32; i++) {
    text += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return text;
}
