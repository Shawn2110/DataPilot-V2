"""
graph.py — LangGraph agent for the v2 conversational copilot.

This builds a ReAct agent that:
1. Reads the user's message
2. Looks at the data context (what's loaded in the notebook)
3. Decides whether to generate code, ask a clarifying question, or respond
4. If generating code: uses tools to create Python code
5. Returns the code + explanation to the chat

The graph uses LangGraph's prebuilt create_react_agent which handles
the Think → Act → Observe loop automatically.
"""

from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage

from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL, LLM_TEMPERATURE
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import (
    generate_code,
    read_dataframe_info,
    create_visualization,
    train_model,
)


def build_agent():
    """
    Build the LangGraph ReAct agent.

    Returns a compiled graph that can be invoked with:
        result = agent.invoke({"messages": [...]})
    or streamed with:
        async for event in agent.astream_events({"messages": [...]}, version="v2"):
            ...
    """
    llm = ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        temperature=LLM_TEMPERATURE,
    )

    tools = [
        generate_code,
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

    The system prompt is dynamic — it includes information about what
    data is currently loaded and what cells are in the notebook.
    This helps the agent generate relevant code.
    """
    prompt = SYSTEM_PROMPT.format(
        data_context=data_context or "No data loaded yet.",
        notebook_summary=notebook_summary or "Notebook is empty.",
    )
    return SystemMessage(content=prompt)
