"""
Q&A — text-only LLM reply for clarification questions.

The user asks "what does that do?" or "why did you fillna with median?".
The LLM gets the recent chat history (last few turns) plus the schema
hint. No tools, no code generation, just a short prose answer.
"""

from __future__ import annotations

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from app.agent.intents import IntentResult
from app.agent.llm import get_llm


_SYSTEM = """You are DataPilot's explainer. Answer the user's question in 1-3 short sentences.

Rules:
- No code in the reply unless the user explicitly asks for it.
- If the question references "the code", "this", or "that", you can see the
  recent turns in chat history — refer to them.
- If you don't know, say so plainly. Do not guess.
"""


def answer(user_text: str, chat_history: list[dict], columns: list[str]) -> IntentResult:
    llm = get_llm(temperature=0.2)

    messages = [SystemMessage(content=_SYSTEM)]
    if columns:
        messages.append(SystemMessage(content=f"The loaded DataFrame `df` has columns: {columns}"))

    # Hand over the last 6 turns so "what did you mean by X" works.
    for turn in chat_history[-6:]:
        role = turn.get("role")
        content = turn.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    messages.append(HumanMessage(content=user_text))

    response = llm.invoke(messages)
    return IntentResult(
        explanation=str(response.content).strip(),
        code=None,
        source="qa",
    )
