"""
chat.py — Chat endpoint backed by the pipeline orchestrator.

The endpoint is a thin shim around app.agent.pipeline.run. Most requests
return a deterministic template (zero LLM tokens); only QA and unmatched
requests hit an LLM.

Response shape:
    {
        "session_id": str,
        "explanation": str,
        "code": str | None,
        "source": "template" | "codegen" | "qa"
    }
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.agent.llm import LLMConfig
from app.agent.pipeline import run as pipeline_run
from app.services.session import get_session, create_session

router = APIRouter()


def _llm_config_from_headers(request: Request) -> LLMConfig | None:
    """Pull provider/key/model overrides off X-Datapilot-* headers.

    The api key, if present, is used for this single request only — never
    logged, never persisted, never echoed back. Returns None when no
    header is set so the env defaults take over.
    """
    h = request.headers
    provider = h.get("x-datapilot-provider")
    model = h.get("x-datapilot-model")
    api_key = h.get("x-datapilot-api-key")
    api_base = h.get("x-datapilot-api-base")
    if not any([provider, model, api_key, api_base]):
        return None
    return LLMConfig(provider=provider, model=model, api_key=api_key, api_base=api_base)


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    explanation: str
    code: str | None
    source: str


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request) -> ChatResponse:
    if req.session_id:
        session = get_session(req.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = create_session()

    columns: list[str] = []
    df_info = session.data_context.get("df") if session.data_context else None
    if df_info:
        columns = list(df_info.get("columns", []))

    session.chat_history.append({"role": "user", "content": req.message})

    llm_config = _llm_config_from_headers(request)
    result = pipeline_run(
        text=req.message,
        columns=columns,
        chat_history=session.chat_history,
        llm_config=llm_config,
    )

    # Record the assistant turn for QA continuity.
    assistant_record = result.explanation
    if result.code:
        assistant_record += f"\n\n```python\n{result.code}\n```"
    session.chat_history.append({"role": "assistant", "content": assistant_record})

    return ChatResponse(
        session_id=session.session_id,
        explanation=result.explanation,
        code=result.code,
        source=result.source,
    )


@router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"messages": session.chat_history}
