"""
Pipeline — single entry point that the CLI and the FastAPI router both call.

    result = run(text, columns=[...], chat_history=[...])

It does:
  1. Route the text to an Intent (deterministic).
  2. If a template handles that intent → render and return (no LLM).
  3. If QA → LLM text answer.
  4. If CUSTOM → LLM code generation.

Token cost: tier 1 = 0, tier 2/3 = one LLM call.
"""

from __future__ import annotations

from app.agent.intents import IntentResult, IntentKind
from app.agent.router import route, RouterContext
from app.agent.templates import render
from app.agent import codegen, qa


def run(
    text: str,
    columns: list[str] | None = None,
    chat_history: list[dict] | None = None,
    df_name: str = "df",
) -> IntentResult:
    columns = columns or []
    chat_history = chat_history or []

    intent = route(text, RouterContext(columns=columns, has_data=bool(columns)))

    if intent.kind == IntentKind.QA:
        return qa.answer(text, chat_history, columns)

    if intent.kind == IntentKind.CUSTOM:
        return codegen.generate(text, columns, df_name=df_name)

    rendered = render(intent, df_name=df_name)
    if rendered is None:
        # Should not happen — every non-QA/CUSTOM intent has a template.
        return codegen.generate(text, columns, df_name=df_name)
    return rendered
