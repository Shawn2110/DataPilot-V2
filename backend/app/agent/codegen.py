"""
Codegen — LLM fallback when no rule-based intent matched.

The prompt is intentionally narrow. The model must return a JSON object
with `code` and `explanation` fields and nothing else. We parse it back
into an IntentResult. If parsing fails we hand the raw output back as
explanation with empty code, so the user always sees *something*.
"""

from __future__ import annotations

import json
import re

from langchain_core.messages import SystemMessage, HumanMessage

from app.agent.intents import IntentResult
from app.agent.llm import get_llm


_SYSTEM = """You generate Python code for a Jupyter notebook session.

Return ONLY a JSON object on a single line:
{"explanation": "<one sentence>", "code": "<python code>"}

Rules:
- The DataFrame is already loaded as `df`.
- Use pandas, plotly.express, scikit-learn, numpy as needed.
- Keep code under 25 lines. Print results so they show in the notebook.
- Do not include markdown fences, prose outside the JSON, or apologies.
- If the request is impossible, set "code" to "" and put the reason in "explanation".
"""


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def generate(user_text: str, columns: list[str], df_name: str = "df") -> IntentResult:
    llm = get_llm()
    schema_hint = f"df has columns: {columns}" if columns else "df is not loaded yet."

    response = llm.invoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=f"{schema_hint}\n\nRequest: {user_text}"),
    ])
    raw = str(response.content).strip()

    try:
        parsed = json.loads(_strip_fences(raw))
        return IntentResult(
            explanation=str(parsed.get("explanation", "")).strip(),
            code=str(parsed.get("code", "")).strip() or None,
            source="codegen",
        )
    except (json.JSONDecodeError, AttributeError):
        # Fall back: try to pull a fenced code block out of free-form text.
        m = re.search(r"```(?:python)?\s*\n(.*?)```", raw, re.DOTALL)
        code = m.group(1).strip() if m else None
        explanation = re.sub(r"```.*?```", "", raw, flags=re.DOTALL).strip() or "Generated code."
        return IntentResult(explanation=explanation, code=code, source="codegen")
