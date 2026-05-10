"""
graph.py — LangGraph agent for the v2 conversational copilot.

Supports 3 LLM providers:
  1. Cerebras (default) — free cloud, fastest, best code accuracy
  2. Groq (fallback)    — free cloud, fast, more models
  3. Ollama (offline)   — local, needs RAM

The provider is selected via LLM_PROVIDER env var.
LangChain abstracts the provider — all three use the same ChatModel interface.
Switching provider = changing one import + one constructor. No other code changes.
"""

from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage

from app.config import (
    LLM_PROVIDER, LLM_TEMPERATURE,
    CEREBRAS_API_KEY, CEREBRAS_MODEL,
    GROQ_API_KEY, GROQ_MODEL,
    OLLAMA_BASE_URL, OLLAMA_MODEL,
)
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import (
    read_dataframe_info,
    create_visualization,
    train_model,
)


def _create_llm():
    """
    Create the LLM based on the configured provider.

    All three return a LangChain ChatModel — same interface,
    different backends. The agent doesn't know or care which one it's using.
    """
    if LLM_PROVIDER == "cerebras":
        from langchain_cerebras import ChatCerebras
        return ChatCerebras(
            model=CEREBRAS_MODEL,
            api_key=CEREBRAS_API_KEY,
            temperature=LLM_TEMPERATURE,
        )

    elif LLM_PROVIDER == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=GROQ_MODEL,
            api_key=GROQ_API_KEY,
            temperature=LLM_TEMPERATURE,
        )

    elif LLM_PROVIDER == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            base_url=OLLAMA_BASE_URL,
            model=OLLAMA_MODEL,
            temperature=LLM_TEMPERATURE,
        )

    else:
        raise ValueError(f"Unknown LLM provider: {LLM_PROVIDER}. Use 'cerebras', 'groq', or 'ollama'.")


def build_agent():
    """
    Build the LangGraph ReAct agent.

    Returns a compiled graph that can be streamed with:
        async for event in agent.astream_events({"messages": [...]}, version="v2"):
            ...
    """
    llm = _create_llm()

    tools = [
        read_dataframe_info,
        create_visualization,
        train_model,
    ]

    agent = create_react_agent(
        model=llm,
        tools=tools,
    )

    return agent


def get_system_message(data_context: str, notebook_summary: str) -> SystemMessage:
    """
    Build the system message with current data context.
    """
    prompt = SYSTEM_PROMPT.format(
        data_context=data_context or "No data loaded yet.",
        notebook_summary=notebook_summary or "Notebook is empty.",
    )
    return SystemMessage(content=prompt)
