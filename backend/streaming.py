from __future__ import annotations

import asyncio
import contextvars
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from langchain_core.callbacks import BaseCallbackHandler


@dataclass(frozen=True)
class StreamContext:
    loop: asyncio.AbstractEventLoop
    queue: asyncio.Queue[Dict[str, Any]]


_stream_ctx: contextvars.ContextVar[Optional[StreamContext]] = contextvars.ContextVar(
    "astroagent_stream_ctx", default=None
)


def set_stream_context(ctx: StreamContext):
    return _stream_ctx.set(ctx)


def reset_stream_context(token):
    _stream_ctx.reset(token)


def get_stream_context() -> Optional[StreamContext]:
    return _stream_ctx.get()


def emit_event(evt: Dict[str, Any]) -> None:
    ctx = get_stream_context()
    if ctx is None:
        return
    # Thread-safe enqueue back into the main event loop.
    ctx.loop.call_soon_threadsafe(ctx.queue.put_nowait, evt)


def emit_tool_events(kind: str, tool_names: List[str]):
    for t in tool_names:
        emit_event({"type": kind, "tool": t})


class QueueStreamingCallback(BaseCallbackHandler):
    """Streams new tokens into an asyncio queue as SSE events."""

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:  # noqa: ANN401
        if not token:
            return
        emit_event({"type": "token", "content": token})
