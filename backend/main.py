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
from backend.services.ephemeris import compute_natal_chart
from backend.services.geocoding import geocode_place_name_async



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
    # Next.js dev server may bump ports (e.g. 3001) if 3000 is in use.
    return sorted(
        list(
            {
                "http://localhost:3000",
                "http://localhost:3001",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:3001",
                frontend,
                "https://astroagent.vercel.app",
            }
        )
    )


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

    await create_message(
        db, session_id=session_id, role="user", content=req.message
    )

    birth_details = req.birth_details.model_dump() if req.birth_details else None
    natal_chart: Optional[dict] = None

    # Make chart generation deterministic: if the frontend only sends a place,
    # resolve coordinates before handing control to the graph/LLM.
    if isinstance(birth_details, dict):
        lat = birth_details.get("lat")
        lng = birth_details.get("lng")
        tz = birth_details.get("timezone")
        if (lat is None or lng is None or not tz) and birth_details.get("place"):
            geo = await geocode_place_name_async(str(birth_details["place"]))
            if isinstance(geo, dict) and not geo.get("error"):
                birth_details = {
                    **birth_details,
                    "lat": float(geo.get("lat")) if geo.get("lat") is not None else lat,
                    "lng": float(geo.get("lng")) if geo.get("lng") is not None else lng,
                    "timezone": str(geo.get("timezone") or tz or "UTC"),
                    "place": str(birth_details.get("place") or geo.get("display_name") or ""),
                }

        if (
            birth_details.get("date")
            and birth_details.get("time")
            and birth_details.get("lat") is not None
            and birth_details.get("lng") is not None
            and birth_details.get("timezone")
        ):
            try:
                natal_chart = compute_natal_chart(
                    date_str=str(birth_details["date"]),
                    time_str=str(birth_details["time"]),
                    lat=float(birth_details["lat"]),
                    lng=float(birth_details["lng"]),
                    timezone=str(birth_details["timezone"]),
                )
            except Exception as exc:  # noqa: BLE001
                natal_chart = {"error": f"Failed to compute chart: {exc}"}

    state: Dict[str, Any] = {
        "messages":        [{"role": "user", "content": req.message}],
        "birth_details":   birth_details,
        "natal_chart":     natal_chart,
        "session_id":      session_id,
        "tool_calls_made": [],
        "step_count":      0,
    }

    async def event_stream() -> AsyncIterator[str]:
        assistant_text = ""
        tool_calls:    List[str] = []
        natal_chart:   Optional[dict] = None
        final_state:   Optional[dict] = None

        if isinstance(natal_chart, dict):
            if natal_chart.get("planets"):
                yield _sse({"type": "chart", "chart": natal_chart})
            elif natal_chart.get("error"):
                yield _sse({"type": "error", "error": str(natal_chart["error"])})

        try:
            async for event in GRAPH.astream_events(state, version="v2"):
                kind = event["event"]
                name = event.get("name", "")
    
                # ── Only stream tokens from respond_node and reasoner_node
                # NOT from router_node (which outputs "chart_request" etc.)
                if kind == "on_chat_model_stream":
                    # Filter: only capture from respond_node or reasoner final pass
                    tags = event.get("tags", []) or []
                    metadata = event.get("metadata", {}) or {}
                    langgraph_node = metadata.get("langgraph_node", "")
        
                    # Skip router tokens — they're internal classifications
                    if langgraph_node == "router_node":
                        continue
                        
                    chunk   = event["data"]["chunk"]
                    content = chunk.content if hasattr(chunk, "content") else ""
                    if content:
                        assistant_text += content
                        yield _sse({"type": "token", "content": content})

                elif kind == "on_tool_start":
                    yield _sse({"type": "tool_start", "tool": name})

                elif kind == "on_tool_end":
                    tool_calls.append(name)
                    output = event["data"].get("output")
                    if isinstance(output, dict) and output.get("planets"):
                        natal_chart = output
                    yield _sse({"type": "tool_end", "tool": name})

                elif kind == "on_chain_end" and name == "LangGraph":
                    final_state = event["data"].get("output")

            # ── After stream ends: extract natal_chart from final state ──
            if isinstance(final_state, dict):
                nc = final_state.get("natal_chart")
                if isinstance(nc, dict) and nc.get("planets"):
                    natal_chart = nc

                # Always extract the final assistant message
                msgs = final_state.get("messages", [])
                if msgs:
                    # Find the last AIMessage
                    for msg in reversed(msgs):
                        msg_type = getattr(msg, "type", None)
                        if msg_type == "ai":
                            content = str(getattr(msg, "content", ""))
                            if content and content != assistant_text:
                                # Stream any new content that wasn't already streamed
                                for char in content[len(assistant_text):]:
                                    assistant_text += char
                                    yield _sse({"type": "token", "content": char})
                            break

                # deduplicate tool calls
                tool_calls = list(dict.fromkeys(
                    final_state.get("tool_calls_made") or tool_calls
                ))

            # ── Persist assistant message ──
            await create_message(
                db,
                session_id=session_id,
                role="assistant",
                content=assistant_text,
                tool_calls=tool_calls or None,
                extra={"natal_chart": natal_chart} if natal_chart else None,
            )

            # ── Emit chart to frontend if we got one ──
            if isinstance(natal_chart, dict) and natal_chart.get("planets"):
                yield _sse({"type": "chart", "chart": natal_chart})
            elif isinstance(natal_chart, dict) and natal_chart.get("error"):
                yield _sse({"type": "error", "error": str(natal_chart["error"])})

            yield _sse({"type": "done"})

        except Exception as exc:
            yield _sse({"type": "error", "error": str(exc)})
            yield _sse({"type": "done"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",
        },
    )