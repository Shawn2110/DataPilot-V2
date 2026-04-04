import * as vscode from "vscode";
import * as cp from "child_process";
import * as net from "net";
import * as path from "path";

/**
 * SidecarManager handles the lifecycle of the Python FastAPI server.
 *
 * Lifecycle:
 *   start() → finds free port → spawns Python → waits for health check
 *   stop()  → kills the Python process tree
 *
 * Why "sidecar"?
 *   In distributed systems, a "sidecar" is a helper process that runs alongside
 *   your main process. Here, the Python server runs alongside VS Code.
 */
export class SidecarManager {
  private process: cp.ChildProcess | undefined;
  private port: number = 0;
  private context: vscode.ExtensionContext;
  private outputChannel: vscode.OutputChannel;

  constructor(context: vscode.ExtensionContext, outputChannel: vscode.OutputChannel) {
    this.context = context;
    this.outputChannel = outputChannel;
  }

  /**
   * Start the Python sidecar server.
   *
   * 1. Find a free port (OS assigns one)
   * 2. Resolve the Python path from settings
   * 3. Spawn uvicorn as a child process
   * 4. Wait until /health responds (max 30s)
   */
  async start(): Promise<void> {
    this.port = await this.findFreePort();
    this.outputChannel.appendLine(`Found free port: ${this.port}`);

    const pythonPath = this.getPythonPath();
    const backendDir = path.join(this.context.extensionPath, "backend");

    this.outputChannel.appendLine(`Python path: ${pythonPath}`);
    this.outputChannel.appendLine(`Backend dir: ${backendDir}`);

    // Spawn the Python process
    // -m uvicorn = run uvicorn as a module
    // main:app = import 'app' from main.py
    // --host 127.0.0.1 = only accept local connections (security)
    this.process = cp.spawn(
      pythonPath,
      ["-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", String(this.port)],
      {
        cwd: backendDir,
        shell: true, // Required on Windows for PATH resolution
        env: {
          ...process.env,
          // Pass Ollama settings to the Python process (FREE, no API key needed)
          OLLAMA_MODEL:
            vscode.workspace.getConfiguration("datapilot").get("ollamaModel") || "llama3.1",
          OLLAMA_BASE_URL:
            vscode.workspace.getConfiguration("datapilot").get("ollamaUrl") || "http://localhost:11434",
        },
      }
    );

    // Pipe Python's stdout/stderr to VS Code's output panel
    // This is crucial for debugging — you can see Python errors in "Output > DataPilot"
    this.process.stdout?.on("data", (data: Buffer) => {
      this.outputChannel.appendLine(`[python] ${data.toString().trim()}`);
    });

    this.process.stderr?.on("data", (data: Buffer) => {
      this.outputChannel.appendLine(`[python-err] ${data.toString().trim()}`);
    });

    this.process.on("exit", (code) => {
      this.outputChannel.appendLine(`Python process exited with code ${code}`);
    });

    // Wait for the server to be ready
    await this.waitForHealth();
  }

  /**
   * Stop the Python server.
   *
   * On Windows, child_process.kill() only kills the parent process,
   * not its children (uvicorn spawns worker processes).
   * We use 'taskkill /T' to kill the entire process tree.
   */
  stop(): void {
    if (!this.process || !this.process.pid) {
      return;
    }

    this.outputChannel.appendLine("Stopping Python sidecar...");

    try {
      if (process.platform === "win32") {
        // /T = kill process tree, /F = force kill
        cp.execSync(`taskkill /pid ${this.process.pid} /T /F`, { stdio: "ignore" });
      } else {
        this.process.kill("SIGTERM");
      }
    } catch {
      // Process might already be dead — that's fine
    }

    this.process = undefined;
  }

  /** Returns the port the sidecar is running on */
  getPort(): number {
    return this.port;
  }

  /**
   * Find a free port by binding to port 0.
   *
   * How it works:
   *   1. Create a TCP server
   *   2. Bind to port 0 (OS picks a random available port)
   *   3. Read the assigned port number
   *   4. Close the server
   *   5. Return the port number
   *
   * This guarantees no port conflicts, even with multiple VS Code windows.
   */
  private findFreePort(): Promise<number> {
    return new Promise((resolve, reject) => {
      const server = net.createServer();
      server.listen(0, "127.0.0.1", () => {
        const addr = server.address();
        if (addr && typeof addr === "object") {
          const port = addr.port;
          server.close(() => resolve(port));
        } else {
          reject(new Error("Could not determine port"));
        }
      });
      server.on("error", reject);
    });
  }

  /**
   * Get the Python interpreter path.
   *
   * Priority order:
   * 1. datapilot.pythonPath setting (user explicitly set)
   * 2. python.defaultInterpreterPath (from Python extension)
   * 3. "python" (rely on system PATH)
   */
  private getPythonPath(): string {
    const config = vscode.workspace.getConfiguration("datapilot");
    const configuredPath = config.get<string>("pythonPath");

    if (configuredPath && configuredPath !== "python") {
      return configuredPath;
    }

    // Try the Python extension's interpreter
    const pythonExt = vscode.workspace.getConfiguration("python");
    const defaultInterpreter = pythonExt.get<string>("defaultInterpreterPath");
    if (defaultInterpreter) {
      return defaultInterpreter;
    }

    return "python";
  }

  /**
   * Wait for the sidecar to respond to health checks.
   *
   * Uses exponential backoff: 500ms, 1s, 2s, 4s...
   * Max wait time: ~30 seconds
   *
   * Why not just wait a fixed time?
   * Because server startup time varies by machine. On a fast machine it's 1s,
   * on a slow machine it might be 10s. Polling with backoff adapts automatically.
   */
  private async waitForHealth(): Promise<void> {
    const maxAttempts = 15;
    let delay = 500;

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        const response = await fetch(`http://127.0.0.1:${this.port}/health`);
        if (response.ok) {
          this.outputChannel.appendLine("Sidecar health check passed!");
          return;
        }
      } catch {
        // Server not ready yet — expected during startup
      }

      this.outputChannel.appendLine(
        `Health check attempt ${attempt}/${maxAttempts} — retrying in ${delay}ms...`
      );
      await new Promise((r) => setTimeout(r, delay));
      delay = Math.min(delay * 1.5, 4000); // exponential backoff, cap at 4s
    }

    throw new Error("Sidecar failed to start within 30 seconds");
  }
}
