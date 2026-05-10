"""
Provider + API key config for the DataPilot CLI.

Resolution order, highest to lowest:
  1. Command-line flags  (--provider / --model / --api-key / --api-base)
  2. Environment variables (LLM_PROVIDER, CEREBRAS_API_KEY, etc.)
  3. Saved config file at ~/.datapilot/config.json
  4. Interactive prompt — written to the file for next time.

The API key is never logged, never echoed, never written to chat history.
The config file is created with 0600 permissions on POSIX (best-effort
on Windows — the user's profile is already private).
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field, asdict
from getpass import getpass
from pathlib import Path

CONFIG_DIR = Path.home() / ".datapilot"
CONFIG_PATH = CONFIG_DIR / "config.json"

PROVIDERS = ("cerebras", "groq", "ollama")

DEFAULT_MODELS = {
    "cerebras": "llama3.1-8b",
    "groq": "llama-3.3-70b-versatile",
    "ollama": "llama3.2:1b",
}

# Provider → env-var name for the key (Ollama needs no key).
KEY_ENV_VAR = {
    "cerebras": "CEREBRAS_API_KEY",
    "groq": "GROQ_API_KEY",
}


@dataclass
class Config:
    provider: str = "cerebras"
    model: str = ""
    api_key: str = ""              # not used for ollama
    api_base: str = ""             # only used for ollama (defaults to localhost:11434)

    def __post_init__(self) -> None:
        if not self.model:
            self.model = DEFAULT_MODELS.get(self.provider, "")

    def to_safe_dict(self) -> dict:
        """Like asdict but masks the key — for logs / debug only."""
        d = asdict(self)
        if d.get("api_key"):
            d["api_key"] = "***"
        return d


# --- File I/O ---

def load_from_file() -> Config | None:
    if not CONFIG_PATH.exists():
        return None
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return Config(
            provider=data.get("provider", "cerebras"),
            model=data.get("model", ""),
            api_key=data.get("api_key", ""),
            api_base=data.get("api_base", ""),
        )
    except (OSError, json.JSONDecodeError):
        return None


def save_to_file(cfg: Config) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(asdict(cfg), indent=2)
    CONFIG_PATH.write_text(payload, encoding="utf-8")
    if os.name != "nt":
        try:
            os.chmod(CONFIG_PATH, 0o600)
        except OSError:
            pass


# --- Resolution ---

def _load_dotenv_silently() -> None:
    """Best-effort: pull keys from a local .env so devs running from the
    project root keep working without rerunning `datapilot config`."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for candidate in (Path.cwd() / ".env", Path.cwd() / "backend" / ".env"):
        if candidate.exists():
            load_dotenv(candidate, override=False)


def from_env() -> Config | None:
    _load_dotenv_silently()
    provider = os.environ.get("LLM_PROVIDER", "").lower()
    if provider not in PROVIDERS:
        return None
    cfg = Config(provider=provider)
    if provider == "cerebras":
        cfg.api_key = os.environ.get("CEREBRAS_API_KEY", "")
        cfg.model = os.environ.get("CEREBRAS_MODEL", DEFAULT_MODELS["cerebras"])
    elif provider == "groq":
        cfg.api_key = os.environ.get("GROQ_API_KEY", "")
        cfg.model = os.environ.get("GROQ_MODEL", DEFAULT_MODELS["groq"])
    elif provider == "ollama":
        cfg.api_base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        cfg.model = os.environ.get("OLLAMA_MODEL", DEFAULT_MODELS["ollama"])
    if provider != "ollama" and not cfg.api_key:
        return None
    return cfg


def apply_to_env(cfg: Config) -> None:
    """Push resolved config into os.environ so app.config picks it up."""
    os.environ["LLM_PROVIDER"] = cfg.provider
    if cfg.provider == "cerebras":
        os.environ["CEREBRAS_API_KEY"] = cfg.api_key
        os.environ["CEREBRAS_MODEL"] = cfg.model
    elif cfg.provider == "groq":
        os.environ["GROQ_API_KEY"] = cfg.api_key
        os.environ["GROQ_MODEL"] = cfg.model
    elif cfg.provider == "ollama":
        os.environ["OLLAMA_BASE_URL"] = cfg.api_base or "http://localhost:11434"
        os.environ["OLLAMA_MODEL"] = cfg.model


# --- Interactive prompt ---

def interactive_setup(default: Config | None = None) -> Config:
    """Walk the user through picking a provider + key. Echoes nothing for the key."""
    print()
    print("DataPilot — first-run configuration")
    print("Pick an LLM provider:")
    print("  1) cerebras  · cloud, free, very fast (recommended)")
    print("  2) groq      · cloud, free, more model variety")
    print("  3) ollama    · local, no key, needs RAM and a running Ollama server")
    print()

    default_provider = (default.provider if default else "cerebras")
    while True:
        choice = input(f"choice [1/2/3] (default {default_provider}): ").strip().lower()
        if not choice:
            provider = default_provider
            break
        if choice in ("1", "cerebras"):
            provider = "cerebras"
            break
        if choice in ("2", "groq"):
            provider = "groq"
            break
        if choice in ("3", "ollama"):
            provider = "ollama"
            break
        print("  invalid — type 1, 2, or 3.")

    cfg = Config(provider=provider)

    if provider in ("cerebras", "groq"):
        env_var = KEY_ENV_VAR[provider]
        existing_key = (default.api_key if (default and default.provider == provider) else "")
        prompt = f"{provider} API key (input hidden"
        if existing_key:
            prompt += ", press Enter to keep existing"
        prompt += "): "
        # getpass handles terminals without a TTY by reading from stdin without echoing.
        try:
            entered = getpass(prompt)
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(1)
        cfg.api_key = entered or existing_key
        if not cfg.api_key:
            print(f"  no key entered; you'll need to set {env_var} or rerun setup.")
        default_model = DEFAULT_MODELS[provider]
        model_in = input(f"model (default {default_model}): ").strip()
        cfg.model = model_in or default_model

    elif provider == "ollama":
        default_base = "http://localhost:11434"
        existing_base = (default.api_base if (default and default.provider == "ollama") else default_base)
        base_in = input(f"ollama base URL (default {existing_base}): ").strip()
        cfg.api_base = base_in or existing_base
        default_model = DEFAULT_MODELS["ollama"]
        existing_model = (default.model if (default and default.provider == "ollama") else default_model)
        model_in = input(f"model (default {existing_model}): ").strip()
        cfg.model = model_in or existing_model

    return cfg


def resolve(
    cli_provider: str | None = None,
    cli_model: str | None = None,
    cli_api_key: str | None = None,
    cli_api_base: str | None = None,
    interactive: bool = True,
) -> Config:
    """
    Apply the resolution order. Persists newly-prompted configs to the file.
    """
    # 1. CLI flags (full override if --provider given)
    if cli_provider:
        cli_provider = cli_provider.lower()
        if cli_provider not in PROVIDERS:
            raise ValueError(f"--provider must be one of {PROVIDERS}, got {cli_provider!r}")
        cfg = Config(provider=cli_provider)
        if cli_model:
            cfg.model = cli_model
        if cli_api_key:
            cfg.api_key = cli_api_key
        if cli_api_base:
            cfg.api_base = cli_api_base
        # Fill missing key/base from env or saved config.
        if cli_provider != "ollama" and not cfg.api_key:
            env_cfg = from_env()
            if env_cfg and env_cfg.provider == cli_provider:
                cfg.api_key = env_cfg.api_key
            else:
                file_cfg = load_from_file()
                if file_cfg and file_cfg.provider == cli_provider:
                    cfg.api_key = file_cfg.api_key
        return cfg

    # 2. Environment
    env_cfg = from_env()
    if env_cfg:
        return env_cfg

    # 3. Saved file
    file_cfg = load_from_file()
    if file_cfg and (file_cfg.provider == "ollama" or file_cfg.api_key):
        return file_cfg

    # 4. Interactive (only if attached to a terminal)
    if interactive and sys.stdin.isatty():
        cfg = interactive_setup(default=file_cfg)
        save_to_file(cfg)
        print(f"saved to {CONFIG_PATH}")
        return cfg

    # No interactive available — return whatever we have.
    return file_cfg or Config()
