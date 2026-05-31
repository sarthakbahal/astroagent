from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from backend.agent.graph import GRAPH
from backend.agent.state import BirthDetails
from backend.db.crud import create_message, delete_history, list_messages
from backend.db.database import get_engine, get_session
from backend.db.models import Base
from backend.streaming import reset_stream_queue, set_stream_queue


class BirthDetailsModel(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    time: str = Field(..., description="HH:MM")
    place: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    timezone: str


class ChatRequest(BaseModel):
    message: str
    session_id: str
    birth_details: Optional[BirthDetailsModel] = None


class HistoryMessage(BaseModel):
    id: int
    role: str
    content: str
    tool_calls: Optional[List[str]] = None
    created_at: str


def _cors_origins() -> List[str]:
    frontend = os.getenv("FRONTEND_URL", "http://localhost:3000").strip()
    return sorted(list({"http://localhost:3000", frontend, "https://astroagent.vercel.app"}))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/history/{session_id}")
async def get_history(session_id: str, db=Depends(get_session)) -> List[HistoryMessage]:
    msgs = await list_messages(db, session_id)
    return [
        HistoryMessage(
            id=m.id,
            role=m.role,
            content=m.content,
            tool_calls=m.tool_calls,
            created_at=m.created_at.isoformat(),
        )
        for m in msgs
    ]


@app.delete("/api/history/{session_id}")
async def clear_history(session_id: str, db=Depends(get_session)) -> Dict[str, str]:
    await delete_history(db, session_id)
    return {"status": "cleared"}


def _sse(data: Dict[str, Any]) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.post("/api/chat")
async def chat(req: ChatRequest, db=Depends(get_session)):
    if not req.session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message required")

    session_id = req.session_id

    # Persist user message
    await create_message(db, session_id=session_id, role="user", content=req.message)

    # Build initial graph state
    state: Dict[str, Any] = {
        "messages": [{"role": "user", "content": req.message}],
        "birth_details": req.birth_details.model_dump() if req.birth_details else None,
        "natal_chart": None,
        "session_id": session_id,
        "tool_calls_made": [],
        "step_count": 0,
    }

    q: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
    token = set_stream_queue(q)

    async def run_graph() -> Dict[str, Any]:
        try:
            # Run graph in a thread to avoid blocking; nodes are sync.
            return await asyncio.to_thread(GRAPH.invoke, state)
        finally:
            reset_stream_queue(token)

    task = asyncio.create_task(run_graph())

    async def event_stream() -> AsyncIterator[str]:
        assistant_text = ""
        tool_calls: List[str] = []
        natal_chart: Optional[dict] = None

        try:
            while True:
                # If task done and queue empty, break.
                if task.done() and q.empty():
                    break

                try:
                    evt = await asyncio.wait_for(q.get(), timeout=0.25)
                except asyncio.TimeoutError:
                    continue

                etype = evt.get("type")
                if etype == "token":
                    assistant_text += str(evt.get("content", ""))
                    yield _sse({"type": "token", "content": evt.get("content", "")})
                elif etype in {"tool_start", "tool_end"}:
                    tool = evt.get("tool")
                    if tool and etype == "tool_end":
                        tool_calls.append(str(tool))
                    yield _sse({"type": etype, "tool": tool})
                elif etype == "done":
                    # Graph finished emitting streamed tokens; we'll still
                    # await final state for persistence and possible chart emit.
                    break
                else:
                    # Unknown event
                    yield _sse({"type": "error", "error": "Unknown event"})

            # Ensure graph finished
            final_state = await task

            # Persist assistant message. If streaming didn't capture (e.g. non-stream fallback), extract from final state.
            msgs = final_state.get("messages", []) if isinstance(final_state, dict) else []
            if not assistant_text and msgs:
                last = msgs[-1]
                assistant_text = str(getattr(last, "content", "") or (last.get("content", "") if isinstance(last, dict) else ""))

            natal_chart = final_state.get("natal_chart") if isinstance(final_state, dict) else None
            tool_calls = list(dict.fromkeys((final_state.get("tool_calls_made") or []) if isinstance(final_state, dict) else tool_calls))

            await create_message(
                db,
                session_id=session_id,
                role="assistant",
                content=assistant_text,
                tool_calls=tool_calls or None,
                extra={"natal_chart": natal_chart} if natal_chart else None,
            )

            # Optionally emit chart for UI
            if natal_chart:
                yield _sse({"type": "chart", "chart": natal_chart})

            yield _sse({"type": "done"})
        except Exception as exc:  # noqa: BLE001
            yield _sse({"type": "error", "error": str(exc)})
            yield _sse({"type": "done"})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
