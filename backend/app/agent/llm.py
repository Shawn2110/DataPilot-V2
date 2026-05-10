"""
LLM provider factory.

get_llm() returns a LangChain ChatModel for whichever provider is
configured. Callers can pass an LLMConfig to override the env-var
defaults — that's how per-request overrides flow in from the chat
router (X-Datapilot-* headers) without touching the backend's env.

Security note: the api_key inside an LLMConfig must never be logged
or returned in responses. It exists only to be handed to the LangChain
client for a single call.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import (
    LLM_PROVIDER, LLM_TEMPERATURE,
    CEREBRAS_API_KEY, CEREBRAS_MODEL,
    GROQ_API_KEY, GROQ_MODEL,
    OLLAMA_BASE_URL, OLLAMA_MODEL,
)


@dataclass
class LLMConfig:
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    api_base: str | None = None


def _resolve(cfg: LLMConfig | None) -> tuple[str, str, str, str]:
    """Return (provider, model, key, base) with env fallback for missing fields."""
    cfg = cfg or LLMConfig()
    provider = (cfg.provider or LLM_PROVIDER or "cerebras").lower()
    if provider == "cerebras":
        return provider, cfg.model or CEREBRAS_MODEL, cfg.api_key or CEREBRAS_API_KEY, ""
    if provider == "groq":
        return provider, cfg.model or GROQ_MODEL, cfg.api_key or GROQ_API_KEY, ""
    if provider == "ollama":
        return provider, cfg.model or OLLAMA_MODEL, "", cfg.api_base or OLLAMA_BASE_URL
    raise ValueError(
        f"Unknown LLM provider: {provider!r}. Use 'cerebras', 'groq', or 'ollama'."
    )


def get_llm(config: LLMConfig | None = None, temperature: float | None = None):
    provider, model, api_key, api_base = _resolve(config)
    t = LLM_TEMPERATURE if temperature is None else temperature

    if provider == "cerebras":
        from langchain_cerebras import ChatCerebras
        return ChatCerebras(model=model, api_key=api_key, temperature=t)

    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(model=model, api_key=api_key, temperature=t)

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(base_url=api_base, model=model, temperature=t)

    # Unreachable: _resolve already raises.
    raise ValueError(f"Unknown LLM provider: {provider!r}")
