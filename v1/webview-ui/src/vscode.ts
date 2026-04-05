/**
 * VS Code API bridge for the webview.
 *
 * acquireVsCodeApi() is a special function injected by VS Code into webviews.
 * It returns an object with:
 *   - postMessage(msg): send a message to the extension host
 *   - getState(): read saved state (survives webview hide/show)
 *   - setState(state): save state (survives webview hide/show)
 *
 * We wrap it in a module so every component can import and use it.
 *
 * Message flow:
 *   React component → vscode.postMessage({type: 'upload:request'})
 *     → VS Code extension receives it in webviewProvider.ts
 *       → Extension calls sidecar API
 *         → Extension sends result back: webview.postMessage({type: 'upload:complete'})
 *           → React component receives it via window.addEventListener('message')
 */

interface VsCodeApi {
  postMessage(message: any): void;
  getState(): any;
  setState(state: any): void;
}

// Declare the global function that VS Code injects into webviews.
// TypeScript doesn't know about it, so we tell it "trust us, this exists at runtime."
declare function acquireVsCodeApi(): VsCodeApi;

// acquireVsCodeApi can only be called ONCE per webview session
// If we're in VS Code, use it. Otherwise (dev mode), use a mock.
const vscode: VsCodeApi =
  typeof acquireVsCodeApi === "function"
    ? acquireVsCodeApi()
    : {
        // Mock for development (when running `npm run dev` outside VS Code)
        postMessage: (msg: any) => console.log("[mock vscode]", msg),
        getState: () => ({}),
        setState: (_state: any) => {},
      };

export default vscode;
