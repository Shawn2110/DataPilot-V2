import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/**
 * Vite config for the VS Code webview.
 *
 * Key difference from a normal React app:
 * - We output a SINGLE main.js + main.css file (no code splitting)
 * - Base is empty string so paths are relative (webview uses special URIs)
 * - Output goes to dist/ which the extension reads at runtime
 */
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
    rollupOptions: {
      output: {
        // Single file output — VS Code webview loads ONE script tag
        entryFileNames: "main.js",
        chunkFileNames: "main.js",
        assetFileNames: "main.[ext]",
      },
    },
  },
});
