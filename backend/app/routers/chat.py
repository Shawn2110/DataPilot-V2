"""
chat.py — Chat endpoint with SSE streaming.

This is the main endpoint both the VS Code extension and web app use.
The user sends a message, and the agent streams back:
  - thinking events (agent reasoning)
  - code events (generated Python code)
  - message events (natural language response)

Both clients read the SSE stream and handle events:
  - Extension: inserts code into notebook cells via Notebook API
  - Web app: inserts code via Jupyter Server REST API
"""

import json
import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from langchain_core.messages import HumanMessage

from app.agent.graph import build_agent, get_system_message
from app.services.session import get_session, create_session
from app.jupyter.notebook_manager import get_notebook_summary

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


@router.post("/chat")
async def chat(req: ChatRequest):
    """
    Send a message to the DataPilot agent. Returns an SSE stream.

    SSE events:
      data: {"type": "thinking", "content": "I should generate a scatter plot..."}
      data: {"type": "code", "content": "import matplotlib.pyplot as plt\\n..."}
      data: {"type": "message", "content": "Here's a scatter plot of age vs salary."}
      data: {"type": "done"}
    """
    # Get or create session
    if req.session_id:
        session = get_session(req.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = create_session()

    # Build context from session
    data_context = json.dumps(session.data_context, indent=2) if session.data_context else "No data loaded."
    notebook_summary = ""
    if session.notebook_path:
        try:
            notebook_summary = get_notebook_summary(session.notebook_path)
        except Exception:
            notebook_summary = "Could not read notebook."

    # Add user message to history
    session.chat_history.append({"role": "user", "content": req.message})

    async def event_stream():
        try:
            agent = build_agent()

            # Build messages: system prompt + chat history + new message
            system_msg = get_system_message(data_context, notebook_summary)
            messages = [system_msg]

            # Add recent chat history for context
            for msg in session.chat_history[-10:]:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))

            # Collect the full response, then parse text vs code blocks
            full_text = []

            async for event in agent.astream_events(
                {"messages": messages},
                version="v2",
            ):
                kind = event.get("event", "")

                if kind == "on_tool_start":
                    tool_name = event.get("name", "")
                    yield {
                        "event": "message",
                        "data": json.dumps({"type": "thinking", "content": f"Using {tool_name}..."}),
                    }

                elif kind == "on_tool_end":
                    output_data = event.get("data", {}).get("output", "")
                    # Extract just the content string from ToolMessage
                    if hasattr(output_data, "content"):
                        output = str(output_data.content)
                    else:
                        output = str(output_data)
                    # Clean up escaped newlines
                    output = output.replace("\\n", "\n")
                    if _looks_like_code(output):
                        yield {
                            "event": "message",
                            "data": json.dumps({"type": "code", "content": output}),
                        }

                elif kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk", None)
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        full_text.append(str(chunk.content))

            # Parse the full response — separate text from ```python code blocks
            full_response = "".join(full_text)
            if full_response:
                session.chat_history.append({"role": "assistant", "content": full_response})
                parts = _split_code_blocks(full_response)
                for part in parts:
                    yield {
                        "event": "message",
                        "data": json.dumps(part),
                    }

            yield {
                "event": "message",
                "data": json.dumps({"type": "done", "session_id": session.session_id}),
            }

        except Exception as e:
            yield {
                "event": "message",
                "data": json.dumps({"type": "error", "content": str(e)}),
            }

    return EventSourceResponse(event_stream())


@router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get the chat history for a session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"messages": session.chat_history}


def _split_code_blocks(text: str) -> list[dict]:
    """
    Split a response into text and code parts.

    Input:  "Here's the code:\n```python\nimport pandas\n```\nDone!"
    Output: [
        {"type": "message", "content": "Here's the code:"},
        {"type": "code", "content": "import pandas"},
        {"type": "message", "content": "Done!"},
    ]
    """
    import re
    parts = []
    # Split on ```python ... ``` or ``` ... ``` blocks
    pattern = r"```(?:python)?\s*\n(.*?)```"
    last_end = 0

    for match in re.finditer(pattern, text, re.DOTALL):
        # Text before the code block
        before = text[last_end:match.start()].strip()
        if before:
            parts.append({"type": "message", "content": before})

        # The code block itself
        code = match.group(1).strip()
        if code:
            parts.append({"type": "code", "content": code})

        last_end = match.end()

    # Text after the last code block
    after = text[last_end:].strip()
    if after:
        parts.append({"type": "message", "content": after})

    # If no code blocks found, return as plain message
    if not parts:
        parts.append({"type": "message", "content": text.strip()})

    return parts


def _looks_like_code(text: str) -> bool:
    """Heuristic: does this text look like Python code?"""
    code_indicators = ["import ", "def ", "class ", "print(", "plt.", "df.", "pd.", "np.", "for ", "if ", "="]
    return any(indicator in text for indicator in code_indicators)
