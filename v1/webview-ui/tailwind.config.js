/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      // Use VS Code's CSS variables for theming
      // This makes the UI match the user's VS Code theme (dark/light)
      colors: {
        vscode: {
          bg: "var(--vscode-editor-background)",
          fg: "var(--vscode-editor-foreground)",
          border: "var(--vscode-panel-border)",
          "input-bg": "var(--vscode-input-background)",
          "input-fg": "var(--vscode-input-foreground)",
          "button-bg": "var(--vscode-button-background)",
          "button-fg": "var(--vscode-button-foreground)",
          "button-hover": "var(--vscode-button-hoverBackground)",
          "badge-bg": "var(--vscode-badge-background)",
          "badge-fg": "var(--vscode-badge-foreground)",
          "success": "var(--vscode-testing-iconPassed)",
          "error": "var(--vscode-testing-iconFailed)",
          "warning": "var(--vscode-editorWarning-foreground)",
        },
      },
    },
  },
  plugins: [],
};
