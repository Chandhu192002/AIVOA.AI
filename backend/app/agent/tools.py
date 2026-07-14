"""The five LangGraph tools used by the CRM agent.

Mandatory (per the brief):
    1. log_interaction
    2. edit_interaction
Custom (our three additional sales tools):
    3. get_interaction_history
    4. suggest_follow_ups
    5. schedule_follow_up

Each tool runs inside a per-request ``ToolContext`` (a ContextVar set by the
graph's tool node). Tools write structured side effects into that context —
``form_updates`` drives the React form on the left of the screen, and
``suggested_followups`` feeds the "AI Suggested Follow-ups" links.
"""
from __future__ import annotations

import json
import re
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from dateutil import parser as dateparser
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import HCP, Interaction, ScheduledFollowUp
from .llm import get_chat_model

# --------------------------------------------------------------------------
# Per-request context shared between the tool node and the tools
# --------------------------------------------------------------------------


@dataclass
class ToolContext:
    db: Session
    form_state: dict = field(default_factory=dict)
    form_updates: dict = field(default_factory=dict)
    suggested_followups: list[str] = field(default_factory=list)
    interaction_id: Optional[int] = None


_tool_ctx: ContextVar[ToolContext] = ContextVar("tool_ctx")


def set_tool_context(ctx: ToolContext):
    return _tool_ctx.set(ctx)


def reset_tool_context(token) -> None:
    _tool_ctx.reset(token)


def get_tool_context() -> ToolContext:
    return _tool_ctx.get()


# --------------------------------------------------------------------------
# Normalisation helpers (defensive against small-model quirks)
# --------------------------------------------------------------------------

_SENTIMENTS = {"positive": "Positive", "neutral": "Neutral", "negative": "Negative"}
_TYPES = ["Meeting", "Call", "Email", "Conference", "Virtual"]


def _norm_sentiment(value: str | None) -> str | None:
    if not value:
        return None
    return _SENTIMENTS.get(value.strip().lower())


def _norm_type(value: str | None) -> str | None:
    if not value:
        return None
    v = value.strip().lower()
    for t in _TYPES:
        if t.lower() in v:
            return t
    return "Meeting"


def _norm_date(value: str | None) -> str | None:
    """Accept 'today', 'yesterday', 'tomorrow' or any parseable date."""
    if not value:
        return None
    v = value.strip().lower()
    today = datetime.now().date()
    if v in ("today", "now"):
        return today.isoformat()
    if v == "yesterday":
        return (today - timedelta(days=1)).isoformat()
    if v == "tomorrow":
        return (today + timedelta(days=1)).isoformat()
    try:
        return dateparser.parse(value, dayfirst=False, fuzzy=True).date().isoformat()
    except (ValueError, OverflowError):
        return None


def _norm_time(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return dateparser.parse(value, fuzzy=True).strftime("%H:%M")
    except (ValueError, OverflowError):
        return None


def _norm_list(value) -> list[str] | None:
    """Accept a list, or a comma/'and'-separated string."""
    if value is None:
        return None
    if isinstance(value, list):
        items = [str(x).strip() for x in value if str(x).strip()]
        return items or None
    if isinstance(value, str):
        parts = re.split(r",| and ", value)
        items = [p.strip(" .") for p in parts if p.strip(" .")]
        return items or None
    return None


def _resolve_hcp_name(db: Session, name: str | None) -> str | None:
    """Match a partial name against the HCP directory (e.g. 'smith' -> 'Dr. Smith')."""
    if not name:
        return None
    name = name.strip()
    bare = re.sub(r"^(dr\.?|prof\.?)\s+", "", name, flags=re.I).strip()
    rows = db.execute(select(HCP)).scalars().all()
    for hcp in rows:
        hcp_bare = re.sub(r"^(dr\.?|prof\.?)\s+", "", hcp.name, flags=re.I).strip()
        if hcp_bare.lower() == bare.lower():
            return hcp.name
    if not re.match(r"^(dr\.?|prof\.?)\s+", name, flags=re.I):
        return f"Dr. {bare.title()}"
    return name


def _collect_field_updates(ctx: ToolContext, raw: dict) -> dict:
    """Normalise incoming tool args -> {form_field: value} (skips empties)."""
    updates: dict = {}
    if raw.get("hcp_name"):
        updates["hcp_name"] = _resolve_hcp_name(ctx.db, raw["hcp_name"])
    if raw.get("interaction_type"):
        updates["interaction_type"] = _norm_type(raw["interaction_type"])
    if raw.get("date"):
        d = _norm_date(raw["date"])
        if d:
            updates["date"] = d
    if raw.get("time"):
        t = _norm_time(raw["time"])
        if t:
            updates["time"] = t
    if raw.get("attendees"):
        att = raw["attendees"]
        updates["attendees"] = ", ".join(att) if isinstance(att, list) else str(att).strip()
    if raw.get("topics_discussed"):
        updates["topics_discussed"] = str(raw["topics_discussed"]).strip()
    if raw.get("materials_shared") is not None:
        mats = _norm_list(raw["materials_shared"])
        if mats:
            updates["materials_shared"] = mats
    if raw.get("samples_distributed") is not None:
        samples = _norm_list(raw["samples_distributed"])
        if samples:
            updates["samples_distributed"] = samples
    if raw.get("sentiment"):
        s = _norm_sentiment(raw["sentiment"])
        if s:
            updates["sentiment"] = s
    if raw.get("outcomes"):
        updates["outcomes"] = str(raw["outcomes"]).strip()
    if raw.get("follow_up_actions"):
        fua = raw["follow_up_actions"]
        updates["follow_up_actions"] = (
            "\n".join(fua) if isinstance(fua, list) else str(fua).strip()
        )
    return updates


# --------------------------------------------------------------------------
# Tool 1 — Log Interaction (mandatory)
# --------------------------------------------------------------------------


@tool
def log_interaction(
    hcp_name: str,
    interaction_type: Optional[str] = None,
    date: Optional[str] = None,
    time: Optional[str] = None,
    attendees: Optional[str] = None,
    topics_discussed: Optional[str] = None,
    materials_shared: Optional[list[str]] = None,
    samples_distributed: Optional[list[str]] = None,
    sentiment: Optional[str] = None,
    outcomes: Optional[str] = None,
    follow_up_actions: Optional[str] = None,
) -> str:
    """Log a NEW HCP interaction. Extract every detail from the user's natural
    language summary and pass it here; the form on screen and the database are
    both updated. Only pass values the user actually stated.

    Args:
        hcp_name: Healthcare professional's name, e.g. "Dr. Smith".
        interaction_type: One of Meeting, Call, Email, Conference, Virtual.
        date: Interaction date in YYYY-MM-DD (convert "today"/"yesterday").
        time: Interaction time in 24h HH:MM.
        attendees: Other people present (comma separated).
        topics_discussed: Key discussion points, e.g. "Product X efficacy".
        materials_shared: Materials given, e.g. ["Brochures"].
        samples_distributed: Product samples handed out, e.g. ["OncoBoost 10mg"].
        sentiment: Observed HCP sentiment: Positive, Neutral or Negative.
        outcomes: Key outcomes or agreements.
        follow_up_actions: Next steps or tasks.
    """
    ctx = get_tool_context()
    updates = _collect_field_updates(ctx, {
        "hcp_name": hcp_name,
        "interaction_type": interaction_type,
        "date": date,
        "time": time,
        "attendees": attendees,
        "topics_discussed": topics_discussed,
        "materials_shared": materials_shared,
        "samples_distributed": samples_distributed,
        "sentiment": sentiment,
        "outcomes": outcomes,
        "follow_up_actions": follow_up_actions,
    })

    # Sensible defaults for a brand new record
    updates.setdefault("interaction_type", "Meeting")
    updates.setdefault("date", datetime.now().date().isoformat())
    updates.setdefault("time", datetime.now().strftime("%H:%M"))

    row = Interaction(
        hcp_name=updates.get("hcp_name", ""),
        interaction_type=updates.get("interaction_type", "Meeting"),
        date=updates.get("date", ""),
        time=updates.get("time", ""),
        attendees=updates.get("attendees", ""),
        topics_discussed=updates.get("topics_discussed", ""),
        materials_shared=updates.get("materials_shared", []),
        samples_distributed=updates.get("samples_distributed", []),
        sentiment=updates.get("sentiment", "Neutral"),
        outcomes=updates.get("outcomes", ""),
        follow_up_actions=updates.get("follow_up_actions", ""),
    )
    ctx.db.add(row)
    ctx.db.commit()
    ctx.db.refresh(row)

    ctx.form_updates.update(updates)
    ctx.interaction_id = row.id

    return json.dumps(
        {
            "status": "success",
            "interaction_id": row.id,
            "fields_populated": sorted(updates.keys()),
            "record": row.to_dict(),
        }
    )


# --------------------------------------------------------------------------
# Tool 2 — Edit Interaction (mandatory)
# --------------------------------------------------------------------------


@tool
def edit_interaction(
    hcp_name: Optional[str] = None,
    interaction_type: Optional[str] = None,
    date: Optional[str] = None,
    time: Optional[str] = None,
    attendees: Optional[str] = None,
    topics_discussed: Optional[str] = None,
    materials_shared: Optional[list[str]] = None,
    samples_distributed: Optional[list[str]] = None,
    sentiment: Optional[str] = None,
    outcomes: Optional[str] = None,
    follow_up_actions: Optional[str] = None,
    interaction_id: Optional[int] = None,
) -> str:
    """Edit the CURRENT (or a specific) interaction. Pass ONLY the fields the
    user asked to change — every other field is preserved exactly as it was.
    Use when the user corrects a mistake, e.g. "sorry, the name was actually
    Dr. John and the sentiment was negative".

    Args:
        hcp_name: New HCP name (only if the user corrected it).
        interaction_type: New type (Meeting/Call/Email/Conference/Virtual).
        date: New date (YYYY-MM-DD).
        time: New time (HH:MM, 24h).
        attendees: New attendees value.
        topics_discussed: New discussion points.
        materials_shared: New full list of materials shared.
        samples_distributed: New full list of samples distributed.
        sentiment: New sentiment: Positive, Neutral or Negative.
        outcomes: New outcomes text.
        follow_up_actions: New follow-up actions text.
        interaction_id: Optional explicit record id (defaults to the one on screen).
    """
    ctx = get_tool_context()
    updates = _collect_field_updates(ctx, {
        "hcp_name": hcp_name,
        "interaction_type": interaction_type,
        "date": date,
        "time": time,
        "attendees": attendees,
        "topics_discussed": topics_discussed,
        "materials_shared": materials_shared,
        "samples_distributed": samples_distributed,
        "sentiment": sentiment,
        "outcomes": outcomes,
        "follow_up_actions": follow_up_actions,
    })

    if not updates:
        return json.dumps(
            {"status": "error", "message": "No editable fields were provided."}
        )

    target_id = interaction_id or ctx.interaction_id
    row: Interaction | None = None
    if target_id:
        row = ctx.db.get(Interaction, target_id)
    if row is None:  # fall back to the most recently logged interaction
        row = (
            ctx.db.execute(select(Interaction).order_by(Interaction.id.desc()).limit(1))
            .scalars()
            .first()
        )

    changed = sorted(updates.keys())
    if row is not None:
        for key, value in updates.items():
            setattr(row, key, value)
        ctx.db.commit()
        ctx.db.refresh(row)
        ctx.interaction_id = row.id
        record = row.to_dict()
    else:
        record = None  # nothing logged yet – still update the on-screen form

    ctx.form_updates.update(updates)

    return json.dumps(
        {
            "status": "success",
            "interaction_id": ctx.interaction_id,
            "fields_changed": changed,
            "unchanged_fields_preserved": True,
            "record": record,
        }
    )


# --------------------------------------------------------------------------
# Tool 3 — Interaction History (custom)
# --------------------------------------------------------------------------


@tool
def get_interaction_history(hcp_name: Optional[str] = None, limit: int = 5) -> str:
    """Retrieve previously logged interactions, optionally filtered by HCP.
    Use when the user asks things like "what did I log for Dr. Smith?" or
    "show my recent interactions".

    Args:
        hcp_name: Optional HCP name filter, e.g. "Dr. Smith".
        limit: Max number of records to return (default 5).
    """
    ctx = get_tool_context()
    stmt = select(Interaction).order_by(Interaction.id.desc()).limit(max(1, min(limit, 20)))
    if hcp_name:
        resolved = _resolve_hcp_name(ctx.db, hcp_name) or hcp_name
        stmt = (
            select(Interaction)
            .where(Interaction.hcp_name.ilike(f"%{resolved.replace('Dr. ', '')}%"))
            .order_by(Interaction.id.desc())
            .limit(max(1, min(limit, 20)))
        )
    rows = ctx.db.execute(stmt).scalars().all()
    return json.dumps(
        {
            "status": "success",
            "count": len(rows),
            "interactions": [r.to_dict() for r in rows],
        }
    )


# --------------------------------------------------------------------------
# Tool 4 — AI Suggested Follow-ups (custom, LLM-powered)
# --------------------------------------------------------------------------


@tool
def suggest_follow_ups() -> str:
    """Generate exactly 3 smart, specific follow-up suggestions for the
    interaction currently on screen (they appear as clickable
    "AI Suggested Follow-ups" in the form). Use when the user asks for
    follow-up ideas / next steps, or right after logging when they say yes to
    suggestions.
    """
    ctx = get_tool_context()
    state = {**ctx.form_state, **ctx.form_updates}
    context_json = json.dumps(
        {k: v for k, v in state.items() if v}, ensure_ascii=False
    )

    prompt = [
        SystemMessage(
            content=(
                "You are a pharma sales operations expert. Given an HCP "
                "interaction, propose exactly 3 short, concrete follow-up "
                "actions (max 9 words each) a field rep should take. Reply "
                'with ONLY a JSON array of 3 strings, e.g. ["Schedule '
                'follow-up meeting in 2 weeks", "Send Product X Phase III '
                'PDF", "Add Dr. Smith to advisory board list"].'
            )
        ),
        HumanMessage(content=f"Interaction details: {context_json}"),
    ]
    suggestions: list[str] = []
    try:
        llm = get_chat_model()
        raw = llm.invoke(prompt).content
        match = re.search(r"\[.*\]", raw, re.S)
        if match:
            parsed = json.loads(match.group(0))
            suggestions = [str(s).strip() for s in parsed if str(s).strip()][:3]
    except Exception:
        suggestions = []

    if not suggestions:  # deterministic safety net (still LLM-first)
        hcp = state.get("hcp_name") or "the HCP"
        suggestions = [
            "Schedule follow-up meeting in 2 weeks",
            f"Send requested product literature to {hcp}",
            f"Add {hcp} to advisory board invite list",
        ]

    ctx.suggested_followups = suggestions
    return json.dumps({"status": "success", "suggestions": suggestions})


# --------------------------------------------------------------------------
# Tool 5 — Schedule Follow-up (custom)
# --------------------------------------------------------------------------


@tool
def schedule_follow_up(
    note: str,
    due_date: Optional[str] = None,
    hcp_name: Optional[str] = None,
) -> str:
    """Create a scheduled follow-up task (meeting, call or to-do) for an HCP.
    Use when the user says e.g. "schedule a follow-up meeting with Dr. Smith
    next Friday" or accepts a suggested follow-up.

    Args:
        note: What the follow-up is, e.g. "Follow-up meeting re: Product X".
        due_date: When it is due (YYYY-MM-DD; convert phrases like
            "in 2 weeks" / "next Friday" to a date before calling).
        hcp_name: The HCP it concerns (defaults to the one on the form).
    """
    ctx = get_tool_context()
    state = {**ctx.form_state, **ctx.form_updates}

    resolved_name = _resolve_hcp_name(ctx.db, hcp_name) or state.get("hcp_name") or ""
    resolved_date = _norm_date(due_date) or (
        datetime.now().date() + timedelta(days=14)
    ).isoformat()

    row = ScheduledFollowUp(
        interaction_id=ctx.interaction_id,
        hcp_name=resolved_name,
        due_date=resolved_date,
        note=note.strip(),
        status="pending",
    )
    ctx.db.add(row)
    ctx.db.commit()
    ctx.db.refresh(row)

    # Reflect the commitment in the form's Follow-up Actions field too
    existing = (state.get("follow_up_actions") or "").strip()
    line = f"{note.strip()} (due {resolved_date})"
    ctx.form_updates["follow_up_actions"] = f"{existing}\n{line}".strip() if existing else line

    return json.dumps({"status": "success", "followup": row.to_dict()})


ALL_TOOLS = [
    log_interaction,
    edit_interaction,
    get_interaction_history,
    suggest_follow_ups,
    schedule_follow_up,
]

TOOLS_BY_NAME = {t.name: t for t in ALL_TOOLS}
