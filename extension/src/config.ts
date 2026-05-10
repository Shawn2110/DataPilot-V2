/**
 * Provider/key configuration for the VS Code extension.
 *
 *   - Provider, model, base URL  → workspace `datapilot.*` settings.
 *   - API key                    → SecretStorage (OS keychain).
 *
 * The key is never written to settings, never logged, never sent to any
 * destination other than the backend Authorization-equivalent header.
 */
import * as vscode from "vscode";

export type Provider = "cerebras" | "groq" | "ollama";

export interface DatapilotConfig {
  provider: Provider;
  model: string;
  apiKey: string; // empty for ollama
  apiBase: string; // only used for ollama
}

const SECRET_KEY_PREFIX = "datapilot.apiKey.";

const DEFAULT_MODELS: Record<Provider, string> = {
  cerebras: "llama3.1-8b",
  groq: "llama-3.3-70b-versatile",
  ollama: "llama3.2:1b",
};

const PROVIDER_LABELS: Record<Provider, string> = {
  cerebras: "Cerebras  ·  cloud, free, fastest",
  groq: "Groq  ·  cloud, free, more models",
  ollama: "Ollama  ·  local, no key needed",
};

function settings() {
  return vscode.workspace.getConfiguration("datapilot");
}

export async function loadConfig(
  context: vscode.ExtensionContext
): Promise<DatapilotConfig | null> {
  const cfg = settings();
  const provider = cfg.get<Provider>("provider");
  if (!provider) {
    return null;
  }
  const model = cfg.get<string>("model") || DEFAULT_MODELS[provider];
  const apiBase =
    cfg.get<string>("apiBase") ||
    (provider === "ollama" ? "http://localhost:11434" : "");
  const apiKey =
    provider === "ollama"
      ? ""
      : (await context.secrets.get(SECRET_KEY_PREFIX + provider)) || "";

  if (provider !== "ollama" && !apiKey) {
    return null;
  }
  return { provider, model, apiKey, apiBase };
}

/**
 * Walks the user through picking a provider and entering a key.
 * Persists provider/model/apiBase in workspace settings, key in SecretStorage.
 * Returns null if the user cancelled.
 */
export async function configureInteractively(
  context: vscode.ExtensionContext
): Promise<DatapilotConfig | null> {
  const providerPick = await vscode.window.showQuickPick(
    (Object.keys(PROVIDER_LABELS) as Provider[]).map((p) => ({
      label: PROVIDER_LABELS[p],
      detail: "",
      provider: p,
    })),
    { placeHolder: "Pick an LLM provider" }
  );
  if (!providerPick) return null;
  const provider = (providerPick as any).provider as Provider;

  const model =
    (await vscode.window.showInputBox({
      prompt: "Model name",
      value: DEFAULT_MODELS[provider],
      ignoreFocusOut: true,
    })) || DEFAULT_MODELS[provider];

  let apiKey = "";
  let apiBase = "";

  if (provider === "ollama") {
    apiBase =
      (await vscode.window.showInputBox({
        prompt: "Ollama base URL",
        value: "http://localhost:11434",
        ignoreFocusOut: true,
      })) || "http://localhost:11434";
  } else {
    const entered = await vscode.window.showInputBox({
      prompt: `${provider} API key (stored in OS keychain via SecretStorage)`,
      password: true,
      ignoreFocusOut: true,
    });
    if (entered === undefined) return null; // user pressed Esc
    apiKey = entered;
  }

  // Persist non-secret bits to settings (workspace > global, fall back to global).
  const cfg = settings();
  await cfg.update("provider", provider, vscode.ConfigurationTarget.Global);
  await cfg.update("model", model, vscode.ConfigurationTarget.Global);
  if (apiBase) {
    await cfg.update("apiBase", apiBase, vscode.ConfigurationTarget.Global);
  }
  if (apiKey) {
    await context.secrets.store(SECRET_KEY_PREFIX + provider, apiKey);
  }

  return { provider, model, apiKey, apiBase };
}

export async function ensureConfig(
  context: vscode.ExtensionContext
): Promise<DatapilotConfig | null> {
  const existing = await loadConfig(context);
  if (existing) return existing;
  return configureInteractively(context);
}
