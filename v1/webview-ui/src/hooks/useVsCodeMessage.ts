import { useEffect, useCallback } from "react";

/**
 * Custom React hook to listen for messages from the VS Code extension.
 *
 * How it works:
 *   1. VS Code extension calls webview.postMessage({type: '...', data: ...})
 *   2. The webview receives it as a 'message' event on the window object
 *   3. This hook captures those events and calls your handler function
 *
 * Usage:
 *   useVsCodeMessage((message) => {
 *     if (message.type === 'upload:complete') {
 *       setData(message.data);
 *     }
 *   });
 *
 * Why a custom hook?
 *   Without this, you'd need useEffect + addEventListener + removeEventListener
 *   in every component. This hook handles the setup/cleanup for you.
 */
export function useVsCodeMessage(handler: (message: any) => void) {
  const stableHandler = useCallback(handler, [handler]);

  useEffect(() => {
    const listener = (event: MessageEvent) => {
      // VS Code wraps the message in event.data
      stableHandler(event.data);
    };

    window.addEventListener("message", listener);

    // Cleanup: remove listener when component unmounts
    return () => window.removeEventListener("message", listener);
  }, [stableHandler]);
}
