from __future__ import annotations

from typing import Any, List, Optional, TypedDict

from langgraph.graph import MessagesState


class BirthDetails(TypedDict):
    """Normalized birth details used for chart computation."""

    date: str  # "YYYY-MM-DD"
    time: str  # "HH:MM"
    place: str  # raw place name
    lat: Optional[float]
    lng: Optional[float]
    timezone: str


class AgentState(MessagesState):
    """LangGraph-compatible state container.

    Note: LangGraph works best with plain dict-like state (TypedDict).
    MessagesState already carries the `messages` list.
    """

    birth_details: Optional[BirthDetails]
    natal_chart: Optional[dict]
    session_id: str
    tool_calls_made: List[str]
    step_count: int
