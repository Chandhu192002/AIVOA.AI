"""LangGraph agent graph.

Classic ReAct-style loop built with ``StateGraph``:

    START ──> agent ──(tool_calls?)──> tools ──> agent ──> ... ──> END

* ``agent`` — the Groq LLM (gemma2-9b-it) with the five CRM tools bound. It
  reads the chat history plus a system prompt containing the live form state
  and today's date, then decides whether to call tools or answer.
* ``tools`` — executes the requested tools inside a per-request ToolContext;
  tools persist to the DB and stage ``form_updates`` that the frontend applies
  to the Redux form.
"""
from __future__ import annotations

import logging
from typing import Annotated, Optional

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from ..database import SessionLocal
from .llm import get_chat_model, get_fallback_model_name, get_primary_model_name
from .prompts import build_system_prompt
from .tools import (
    ALL_TOOLS,
    TOOLS_BY_NAME,
    ToolContext,
    reset_tool_context,
    set_tool_context,
)

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State carried through the graph for one chat turn."""

    messages: Annotated[list, add_messages]
    form_state: dict
    form_updates: dict
    suggested_followups: list
    interaction_id: Optional[int]
    model_used: str


# --------------------------------------------------------------------------
# Nodes
# --------------------------------------------------------------------------


def get_agent_llm(model: str | None = None):
    """LLM with the five tools bound (patchable in tests)."""
    return get_chat_model(model).bind_tools(ALL_TOOLS)


def agent_node(state: AgentState) -> dict:
    """Ask the LLM what to do next (answer, or call one/more tools)."""
    live_form = {**(state.get("form_state") or {}), **(state.get("form_updates") or {})}
    system = SystemMessage(content=build_system_prompt(live_form))
    messages = [system, *state["messages"]]

    primary = get_primary_model_name()
    fallback = get_fallback_model_name()
    try:
        response = get_agent_llm(primary).invoke(messages)
        model_used = primary
    except Exception as exc:  # e.g. model decommissioned / transient failure
        logger.warning("Primary model '%s' failed (%s); retrying with '%s'",
                       primary, exc, fallback)
        response = get_agent_llm(fallback).invoke(messages)
        model_used = fallback

    return {"messages": [response], "model_used": model_used}


def tool_node(state: AgentState) -> dict:
    """Execute the tool calls requested by the last AI message."""
    last: AIMessage = state["messages"][-1]
    db = SessionLocal()
    ctx = ToolContext(
        db=db,
        form_state={**(state.get("form_state") or {}), **(state.get("form_updates") or {})},
        form_updates=dict(state.get("form_updates") or {}),
        suggested_followups=list(state.get("suggested_followups") or []),
        interaction_id=state.get("interaction_id"),
    )
    token = set_tool_context(ctx)
    results: list[ToolMessage] = []
    try:
        for call in last.tool_calls:
            tool = TOOLS_BY_NAME.get(call["name"])
            if tool is None:
                content = f'{{"status":"error","message":"Unknown tool {call["name"]}"}}'
            else:
                try:
                    content = tool.invoke(call["args"])
                except Exception as exc:  # keep the loop alive on bad args
                    logger.exception("Tool %s failed", call["name"])
                    content = f'{{"status":"error","message":"{exc}"}}'
            results.append(
                ToolMessage(content=str(content), tool_call_id=call["id"], name=call["name"])
            )
    finally:
        reset_tool_context(token)
        db.close()

    return {
        "messages": results,
        "form_updates": ctx.form_updates,
        "suggested_followups": ctx.suggested_followups,
        "interaction_id": ctx.interaction_id,
    }


def should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls:
        return "tools"
    return "end"


# --------------------------------------------------------------------------
# Graph
# --------------------------------------------------------------------------


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", tool_node)
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
    builder.add_edge("tools", "agent")
    return builder.compile()


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
