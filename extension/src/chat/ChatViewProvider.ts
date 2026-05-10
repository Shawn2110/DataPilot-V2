import * as vscode from "vscode";
import { BackendClient } from "../backend/BackendClient";
import { NotebookBridge } from "../notebook/NotebookBridge";

/**
 * ChatViewProvider — Chat sidebar webview for DataPilot.
 *
 * This creates a chat UI in the VS Code sidebar where users type
 * data science instructions. The flow:
 *
 *   1. User types "plot age vs salary"
 *   2. Webview sends message to extension host
 *   3. Extension sends POST /api/chat to backend (SSE stream)
 *   4. On "code" event → NotebookBridge inserts cell into notebook
 *   5. On "message" event → rendered in chat as assistant response
 *   6. User sees the code cell in their notebook, can edit + run it
 */
export class ChatViewProvider implements vscode.WebviewViewProvider {
  private view?: vscode.WebviewView;
  private sessionId: string | null = null;

  constructor(
    private context: vscode.ExtensionContext,
    private client: BackendClient,
    private notebook: NotebookBridge,
    private output: vscode.OutputChannel
  ) {}

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ): void {
    this.view = webviewView;

    webviewView.webview.options = {
      enableScripts: true,
    };

    webviewView.webview.html = this.getHtml();

    webviewView.webview.onDidReceiveMessage(async (msg) => {
      switch (msg.type) {
        case "chat":
          await this.handleChat(msg.text);
          break;
        case "upload":
          await this.handleUpload();
          break;
      }
    });
  }

  /**
   * Handle a chat message from the webview.
   *
   * The new backend returns a single JSON ({explanation, code, source}).
   * Templates cost no LLM tokens; QA returns text only; codegen returns
   * LLM-written code. We always show the explanation; if there's code,
   * we insert it into the notebook and echo it in chat.
   */
  private async handleChat(text: string): Promise<void> {
    this.output.appendLine(`[chat] User: ${text}`);
    this.postMessage({ type: "user-message", content: text });

    try {
      const reply = await this.client.chat(this.sessionId, text);
      this.sessionId = reply.session_id;

      this.postMessage({
        type: "assistant-message",
        content: reply.explanation,
        source: reply.source,
      });

      if (reply.code) {
        await this.notebook.insertCodeCell(reply.code);
        this.postMessage({ type: "code", content: reply.code });
      }

      this.postMessage({ type: "done" });
    } catch (err) {
      this.postMessage({
        type: "error",
        content: `Failed to reach backend: ${err}`,
      });
    }
  }

  /**
   * Handle file upload — open file picker, upload to backend,
   * insert load code into notebook.
   */
  private async handleUpload(): Promise<void> {
    const fileUri = await vscode.window.showOpenDialog({
      canSelectMany: false,
      filters: { Datasets: ["csv", "xlsx", "xls"] },
      title: "Select a dataset",
    });

    if (!fileUri || !fileUri[0]) return;

    try {
      const result = await this.client.upload(
        fileUri[0].fsPath,
        this.sessionId
      );
      this.sessionId = result.session_id;

      // Insert the load code into the notebook
      await this.notebook.insertCodeCell(result.load_code);

      this.postMessage({
        type: "upload-success",
        content: `Loaded ${result.data_info.shape[0]} rows, ${result.data_info.shape[1]} columns`,
        columns: result.data_info.columns,
      });
    } catch (err) {
      this.postMessage({
        type: "error",
        content: `Upload failed: ${err}`,
      });
    }
  }

  private postMessage(msg: any): void {
    this.view?.webview.postMessage(msg);
  }

  /**
   * The chat UI HTML.
   *
   * This is a lightweight chat interface — no React, just vanilla HTML/CSS/JS.
   * Keeps the extension small and fast to load.
   */
  private getHtml(): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: var(--vscode-font-family);
    font-size: var(--vscode-font-size);
    color: var(--vscode-foreground);
    background: var(--vscode-sideBar-background);
    display: flex;
    flex-direction: column;
    height: 100vh;
  }

  .header {
    padding: 12px;
    border-bottom: 1px solid var(--vscode-panel-border);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .header h2 { font-size: 14px; font-weight: 600; }

  .upload-btn {
    padding: 4px 10px;
    font-size: 12px;
    background: var(--vscode-button-background);
    color: var(--vscode-button-foreground);
    border: none;
    border-radius: 4px;
    cursor: pointer;
  }
  .upload-btn:hover { background: var(--vscode-button-hoverBackground); }

  .messages {
    flex: 1;
    overflow-y: auto;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .msg {
    padding: 8px 12px;
    border-radius: 8px;
    max-width: 95%;
    font-size: 13px;
    line-height: 1.5;
    word-wrap: break-word;
  }
  .msg.user {
    background: var(--vscode-button-background);
    color: var(--vscode-button-foreground);
    align-self: flex-end;
    border-radius: 8px 8px 2px 8px;
  }
  .msg.assistant {
    background: var(--vscode-editor-background);
    border: 1px solid var(--vscode-panel-border);
    align-self: flex-start;
    border-radius: 8px 8px 8px 2px;
  }
  .badge {
    display: inline-block;
    padding: 1px 6px;
    margin-right: 4px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    vertical-align: middle;
  }
  .badge-template { background: rgba(120, 120, 120, 0.2); color: var(--vscode-descriptionForeground); }
  .badge-codegen  { background: rgba(220, 180, 60, 0.2); color: #d4a64b; }
  .badge-qa       { background: rgba(80, 140, 220, 0.2); color: #6ba6dc; }
  .msg.code-msg {
    background: var(--vscode-textCodeBlock-background);
    border: 1px solid var(--vscode-panel-border);
    font-family: var(--vscode-editor-font-family);
    font-size: 12px;
    white-space: pre-wrap;
    align-self: flex-start;
    max-width: 100%;
  }
  .msg.error {
    background: rgba(255, 80, 80, 0.15);
    border: 1px solid rgba(255, 80, 80, 0.3);
    color: var(--vscode-errorForeground);
    align-self: flex-start;
  }
  .code-label {
    font-size: 11px;
    color: var(--vscode-descriptionForeground);
    margin-bottom: 4px;
  }

  .input-area {
    padding: 10px 12px;
    border-top: 1px solid var(--vscode-panel-border);
    display: flex;
    gap: 6px;
  }
  .input-area input {
    flex: 1;
    padding: 8px 10px;
    font-size: 13px;
    background: var(--vscode-input-background);
    color: var(--vscode-input-foreground);
    border: 1px solid var(--vscode-input-border);
    border-radius: 6px;
    outline: none;
  }
  .input-area input:focus { border-color: var(--vscode-focusBorder); }
  .input-area button {
    padding: 8px 14px;
    background: var(--vscode-button-background);
    color: var(--vscode-button-foreground);
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
  }
  .input-area button:hover { background: var(--vscode-button-hoverBackground); }
  .input-area button:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
</head>
<body>
  <div class="header">
    <h2>DataPilot</h2>
    <button class="upload-btn" id="uploadBtn">Upload Data</button>
  </div>

  <div class="messages" id="messages">
    <div class="msg assistant">
      Hi! I'm DataPilot. Upload a dataset and tell me what you'd like to do.<br><br>
      Try: <em>"show missing values"</em>, <em>"plot age distribution"</em>, or <em>"train a random forest"</em>
    </div>
  </div>

  <div class="input-area">
    <input type="text" id="chatInput" placeholder="Ask DataPilot..." />
    <button id="sendBtn">Send</button>
  </div>

  <script>
    const vscode = acquireVsCodeApi();
    const messagesDiv = document.getElementById('messages');
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    const uploadBtn = document.getElementById('uploadBtn');
    let isLoading = false;

    function addMessage(type, content, source) {
      const div = document.createElement('div');
      div.className = 'msg ' + type;
      if (type === 'code-msg') {
        div.innerHTML = '<div class="code-label">Code inserted into notebook:</div>' + escapeHtml(content);
      } else if (type === 'assistant' && source) {
        const badge = document.createElement('span');
        badge.className = 'badge badge-' + source;
        badge.textContent = source;
        const text = document.createElement('span');
        text.textContent = ' ' + content;
        div.appendChild(badge);
        div.appendChild(text);
      } else {
        div.textContent = content;
      }
      messagesDiv.appendChild(div);
      messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    function escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }

    function setLoading(loading) {
      isLoading = loading;
      sendBtn.disabled = loading;
      chatInput.disabled = loading;
    }

    sendBtn.addEventListener('click', () => {
      const text = chatInput.value.trim();
      if (!text || isLoading) return;
      chatInput.value = '';
      setLoading(true);
      vscode.postMessage({ type: 'chat', text });
    });

    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendBtn.click();
      }
    });

    uploadBtn.addEventListener('click', () => {
      vscode.postMessage({ type: 'upload' });
    });

    window.addEventListener('message', (event) => {
      const msg = event.data;
      switch (msg.type) {
        case 'user-message':
          addMessage('user', msg.content);
          break;
        case 'assistant-message':
          addMessage('assistant', msg.content, msg.source);
          break;
        case 'code':
          addMessage('code-msg', msg.content);
          break;
        case 'error':
          addMessage('error', msg.content);
          setLoading(false);
          break;
        case 'done':
          setLoading(false);
          break;
        case 'upload-success':
          addMessage('assistant', msg.content);
          setLoading(false);
          break;
      }
    });

    chatInput.focus();
  </script>
</body>
</html>`;
  }
}
