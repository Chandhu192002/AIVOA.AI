"""Offline smoke test for the LangGraph agent (no Groq key / network needed).

Injects a scripted fake chat model so we can verify the *graph mechanics*
end-to-end: agent node -> tool node -> DB write -> form_updates accumulation
-> final answer. Run from `backend/`:

    python -m scripts.smoke_test
"""
import os
import sys

os.environ.setdefault("DATABASE_URL", "sqlite:///./smoke_test.db")

from langchain_core.messages import AIMessage  # noqa: E402

from app.agent import graph as graph_module  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import Interaction, ScheduledFollowUp  # noqa: E402
from app.seed import seed_hcps  # noqa: E402


class ScriptedLLM:
    """Returns pre-scripted AI messages in order, ignoring the input."""

    def __init__(self, responses):
        self._responses = list(responses)
        self._i = 0

    def invoke(self, _messages):
        msg = self._responses[min(self._i, len(self._responses) - 1)]
        self._i += 1
        return msg


def run_turn(script, form_state, interaction_id=None, user_text=""):
    llm = ScriptedLLM(script)
    graph_module.get_agent_llm = lambda model=None: llm  # patch
    g = graph_module.build_graph()
    from langchain_core.messages import HumanMessage

    return g.invoke(
        {
            "messages": [HumanMessage(content=user_text)],
            "form_state": form_state,
            "form_updates": {},
            "suggested_followups": [],
            "interaction_id": interaction_id,
            "model_used": "",
        }
    )


def main():
    if os.path.exists("smoke_test.db"):
        os.remove("smoke_test.db")
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_hcps(db)

    # ---- Turn 1: log_interaction --------------------------------------
    log_call = AIMessage(
        content="",
        tool_calls=[{
            "name": "log_interaction",
            "args": {
                "hcp_name": "Dr. Smith",
                "date": "today",
                "topics_discussed": "Product X efficiency.",
                "sentiment": "positive",
                "materials_shared": ["Brochures"],
            },
            "id": "call_1",
            "type": "tool_call",
        }],
    )
    final_1 = AIMessage(content="✅ **Interaction logged successfully!** ...")
    out1 = run_turn([log_call, final_1], form_state={},
                    user_text="Today I met with Dr. Smith and discussed product X "
                              "efficiency. The sentiment was positive, and I shared "
                              "the brochures.")

    fu = out1["form_updates"]
    assert fu["hcp_name"] == "Dr. Smith", fu
    assert fu["sentiment"] == "Positive", fu
    assert fu["materials_shared"] == ["Brochures"], fu
    assert fu["topics_discussed"] == "Product X efficiency.", fu
    assert len(fu["date"]) == 10 and fu["date"].count("-") == 2, fu
    assert out1["interaction_id"] is not None
    print("PASS  turn 1 (log_interaction) — form_updates:", fu)

    # ---- Turn 2: edit_interaction (only 2 fields change) ---------------
    edit_call = AIMessage(
        content="",
        tool_calls=[{
            "name": "edit_interaction",
            "args": {"hcp_name": "Dr. John", "sentiment": "negative"},
            "id": "call_2",
            "type": "tool_call",
        }],
    )
    final_2 = AIMessage(content="Updated the HCP name to Dr. John and sentiment to Negative.")
    form_after_1 = {
        "hcp_name": "Dr. Smith", "sentiment": "Positive",
        "topics_discussed": "Product X efficiency.",
        "materials_shared": ["Brochures"], "date": fu["date"],
    }
    out2 = run_turn([edit_call, final_2], form_state=form_after_1,
                    interaction_id=out1["interaction_id"],
                    user_text="Sorry, the name was actually Dr. John and the "
                              "sentiment was negative.")

    fu2 = out2["form_updates"]
    assert set(fu2.keys()) == {"hcp_name", "sentiment"}, fu2   # ONLY the 2 fields
    assert fu2["hcp_name"] == "Dr. John" and fu2["sentiment"] == "Negative", fu2
    with SessionLocal() as db:
        row = db.get(Interaction, out1["interaction_id"])
        assert row.hcp_name == "Dr. John"
        assert row.sentiment == "Negative"
        assert row.topics_discussed == "Product X efficiency."     # preserved
        assert row.materials_shared == ["Brochures"]               # preserved
    print("PASS  turn 2 (edit_interaction) — only changed:", fu2)

    # ---- Turn 3: get_interaction_history -------------------------------
    hist_call = AIMessage(content="", tool_calls=[{
        "name": "get_interaction_history",
        "args": {"hcp_name": "Dr. John", "limit": 5},
        "id": "call_3", "type": "tool_call",
    }])
    out3 = run_turn([hist_call, AIMessage(content="You logged 1 interaction with Dr. John.")],
                    form_state=form_after_1, user_text="What did I log for Dr. John?")
    tool_msg = [m for m in out3["messages"] if m.type == "tool"][-1]
    assert '"count": 1' in tool_msg.content, tool_msg.content
    print("PASS  turn 3 (get_interaction_history)")

    # ---- Turn 4: schedule_follow_up ------------------------------------
    sched_call = AIMessage(content="", tool_calls=[{
        "name": "schedule_follow_up",
        "args": {"note": "Follow-up meeting re: Product X", "due_date": "tomorrow"},
        "id": "call_4", "type": "tool_call",
    }])
    out4 = run_turn([sched_call, AIMessage(content="Scheduled!")],
                    form_state={**form_after_1, "hcp_name": "Dr. John"},
                    interaction_id=out1["interaction_id"],
                    user_text="Schedule a follow-up meeting tomorrow")
    with SessionLocal() as db:
        tasks = db.query(ScheduledFollowUp).all()
        assert len(tasks) == 1 and tasks[0].hcp_name == "Dr. John", [t.to_dict() for t in tasks]
    assert "follow_up_actions" in out4["form_updates"]
    print("PASS  turn 4 (schedule_follow_up) — form follow_up_actions:",
          out4["form_updates"]["follow_up_actions"])

    # ---- Turn 5: plain answer, no tools --------------------------------
    out5 = run_turn([AIMessage(content="Hi! Describe your interaction and I'll log it.")],
                    form_state={}, user_text="hello")
    assert out5["form_updates"] == {}
    print("PASS  turn 5 (no-tool reply)")

    print("\nAll LangGraph smoke tests passed ✔")


if __name__ == "__main__":
    sys.exit(main())
