from __future__ import annotations

from typing import Any, Dict, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from backend.agent.nodes import (
    ask_details_node,
    reasoner_node,
    respond_node,
    router_node,
)
from backend.agent.state import AgentState
from backend.agent.tools import compute_birth_chart, geocode_place, get_daily_transits, knowledge_lookup
from backend.streaming import emit_tool_events


def _as_dict(content: Any) -> Any:
    if isinstance(content, dict) or isinstance(content, list):
        return content
    if isinstance(content, str):
        s = content.strip()
        if not s:
            return content
        try:
            import json

            return json.loads(s)
        except Exception:
            return content
    return content


def _route_from_router(state: AgentState) -> str:
    intent = state.get("intent")
    if intent == "needs_details":
        return "needs_details"
    if intent == "off_topic":
        return "off_topic"
    return "reasoner"


def _should_continue_reasoning(state: AgentState) -> str:
    # Hard guard against infinite loops
    if int(state.get("step_count", 0)) >= 8:
        return "respond"

    msgs = state.get("messages", [])
    if not msgs:
        return "respond"

    last = msgs[-1]
    tool_calls = getattr(last, "tool_calls", None)
    if tool_calls:
        return "tools"
    return "respond"


def _tool_node_wrapper(state: AgentState) -> Dict[str, Any]:
    """Run tools and emit SSE tool_start/tool_end events.

    We use ToolNode for execution, but we also append tool names to
    tool_calls_made for client visibility.
    """

    msgs = state.get("messages", [])
    last = msgs[-1] if msgs else None
    tool_calls = getattr(last, "tool_calls", None) or []
    tool_names = []
    for tc in tool_calls:
        name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
        if name:
            tool_names.append(str(name))

    if tool_names:
        emit_tool_events("tool_start", tool_names)

    tool_node = ToolNode([geocode_place, compute_birth_chart, get_daily_transits, knowledge_lookup])
    out = tool_node.invoke(state)

    # Update tool_calls_made
    existing = list(state.get("tool_calls_made") or [])
    existing.extend(tool_names)

    # Capture tool results of special tools into state for UI and responses.
    natal_chart = state.get("natal_chart")
    daily_transits = state.get("daily_transits") if isinstance(state, dict) else None
    birth_details = state.get("birth_details")

    # ToolNode returns messages including ToolMessage(s)
    new_msgs = out.get("messages", []) if isinstance(out, dict) else []
    for m in new_msgs:
        if getattr(m, "type", None) != "tool":
            continue
        name = getattr(m, "name", None)
        parsed = _as_dict(getattr(m, "content", None))
        if name == "geocode_place" and isinstance(parsed, dict) and "error" not in parsed:
            # Populate lat/lng/timezone for subsequent chart computation.
            if isinstance(birth_details, dict):
                birth_details = {
                    **birth_details,
                    "lat": float(parsed.get("lat")) if parsed.get("lat") is not None else birth_details.get("lat"),
                    "lng": float(parsed.get("lng")) if parsed.get("lng") is not None else birth_details.get("lng"),
                    "timezone": str(parsed.get("timezone") or birth_details.get("timezone") or "UTC"),
                    "place": str(birth_details.get("place") or parsed.get("display_name") or ""),
                }
        if name == "compute_birth_chart":
            if isinstance(parsed, dict):
                natal_chart = parsed
        if name == "get_daily_transits":
            daily_transits = parsed

    if tool_names:
        emit_tool_events("tool_end", tool_names)

    update: Dict[str, Any] = {"tool_calls_made": existing}
    if birth_details is not None:
        update["birth_details"] = birth_details
    if natal_chart is not None:
        update["natal_chart"] = natal_chart
    if daily_transits is not None:
        update["daily_transits"] = daily_transits

    # Merge ToolNode output state changes too
    if isinstance(out, dict):
        update.update(out)

    return update


def build_graph():
    g = StateGraph(AgentState)

    g.add_node("router_node", router_node)
    g.add_node("ask_details_node", ask_details_node)
    g.add_node("reasoner_node", reasoner_node)
    g.add_node("tool_node", _tool_node_wrapper)
    g.add_node("respond_node", respond_node)

    g.add_edge(START, "router_node")

    g.add_conditional_edges(
        "router_node",
        _route_from_router,
        {
            "needs_details": "ask_details_node",
            "off_topic": "respond_node",
            "reasoner": "reasoner_node",
        },
    )

    g.add_edge("ask_details_node", END)

    g.add_conditional_edges(
        "reasoner_node",
        _should_continue_reasoning,
        {
            "tools": "tool_node",
            "respond": "respond_node",
        },
    )

    g.add_edge("tool_node", "reasoner_node")
    g.add_edge("respond_node", END)

    return g.compile()


GRAPH = build_graph()
