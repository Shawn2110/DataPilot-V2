"""
LLM provider factory.

One function. Returns a LangChain ChatModel for whichever provider is
configured (Cerebras, Groq, Ollama). The codegen and qa modules both
import from here so the rest of the agent stays provider-agnostic.
"""

from __future__ import annotations

from app.config import (
    LLM_PROVIDER, LLM_TEMPERATURE,
    CEREBRAS_API_KEY, CEREBRAS_MODEL,
    GROQ_API_KEY, GROQ_MODEL,
    OLLAMA_BASE_URL, OLLAMA_MODEL,
)


def get_llm(temperature: float | None = None):
    t = LLM_TEMPERATURE if temperature is None else temperature

    if LLM_PROVIDER == "cerebras":
        from langchain_cerebras import ChatCerebras
        return ChatCerebras(model=CEREBRAS_MODEL, api_key=CEREBRAS_API_KEY, temperature=t)

    if LLM_PROVIDER == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(model=GROQ_MODEL, api_key=GROQ_API_KEY, temperature=t)

    if LLM_PROVIDER == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(base_url=OLLAMA_BASE_URL, model=OLLAMA_MODEL, temperature=t)

    raise ValueError(
        f"Unknown LLM_PROVIDER: {LLM_PROVIDER!r}. Use 'cerebras', 'groq', or 'ollama'."
    )
