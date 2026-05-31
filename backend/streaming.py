from __future__ import annotations

import asyncio
import contextvars
from typing import Any, Dict, List, Optional

from langchain_core.callbacks import BaseCallbackHandler


_stream_queue: contextvars.ContextVar[Optional[asyncio.Queue[Dict[str, Any]]]] = contextvars.ContextVar(
    "astroagent_stream_queue", default=None
)


def set_stream_queue(q):
    return _stream_queue.set(q)


def reset_stream_queue(token):
    _stream_queue.reset(token)


def get_stream_queue():
    return _stream_queue.get()


def emit_tool_events(kind: str, tool_names: List[str]):
    q = get_stream_queue()
    if q is None:
        return
    for t in tool_names:
        q.put_nowait({"type": kind, "tool": t})


class QueueStreamingCallback(BaseCallbackHandler):
    """Streams new tokens into an asyncio queue as SSE events."""

    def __init__(self, queue):
        self.queue = queue

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:  # noqa: ANN401
        if token:
            self.queue.put_nowait({"type": "token", "content": token})
