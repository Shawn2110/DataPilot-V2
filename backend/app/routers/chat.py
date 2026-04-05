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

            # Add recent chat history for context (last 10 messages)
            for msg in session.chat_history[-10:]:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))

            collected_code = []
            collected_text = []

            # Stream agent events
            async for event in agent.astream_events(
                {"messages": messages},
                version="v2",
            ):
                kind = event.get("event", "")

                if kind == "on_tool_start":
                    tool_name = event.get("name", "")
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "thinking",
                            "content": f"Using {tool_name}...",
                        }),
                    }

                elif kind == "on_tool_end":
                    output = event.get("data", {}).get("output", "")
                    output_str = str(output)

                    # Check if the output looks like Python code
                    if _looks_like_code(output_str):
                        collected_code.append(output_str)
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "code",
                                "content": output_str,
                            }),
                        }

                elif kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk", None)
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        text = str(chunk.content)
                        if text.strip():
                            collected_text.append(text)
                            yield {
                                "event": "message",
                                "data": json.dumps({
                                    "type": "message",
                                    "content": text,
                                }),
                            }

            # Save assistant response to history
            full_response = "".join(collected_text)
            if full_response:
                session.chat_history.append({"role": "assistant", "content": full_response})

            # Send done event
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "done",
                    "session_id": session.session_id,
                }),
            }

        except Exception as e:
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "error",
                    "content": str(e),
                }),
            }

    return EventSourceResponse(event_stream())


@router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get the chat history for a session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"messages": session.chat_history}


def _looks_like_code(text: str) -> bool:
    """Heuristic: does this text look like Python code?"""
    code_indicators = ["import ", "def ", "class ", "print(", "plt.", "df.", "pd.", "np.", "for ", "if ", "="]
    return any(indicator in text for indicator in code_indicators)
