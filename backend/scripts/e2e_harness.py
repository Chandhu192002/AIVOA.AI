"""Offline E2E test harness — NOT the assignment demo.

Boots the real FastAPI app + LangGraph graph, but with the LLM replaced by a
scripted sequence of responses, so the full browser flow (React → Redux →
FastAPI → LangGraph tools → DB → form_updates → Redux → form) can be tested
without a GROQ_API_KEY / network. The real application requires a Groq key.

Run from `backend/`:  python -m scripts.e2e_harness
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./e2e_test.db")

import uvicorn  # noqa: E402
from langchain_core.messages import AIMessage  # noqa: E402

from app.agent import graph as graph_module  # noqa: E402

# Scripted agent turns for the exact video demo -----------------------------
SCRIPT = [
    # ---- chat turn 1: log --------------------------------------------------
    AIMessage(content="", tool_calls=[{
        "name": "log_interaction",
        "args": {
            "hcp_name": "Dr. Smith",
            "date": "today",
            "interaction_type": "Meeting",
            "topics_discussed": "Product X efficiency.",
            "sentiment": "Positive",
            "materials_shared": ["Brochures"],
        },
        "id": "call_1", "type": "tool_call",
    }]),
    AIMessage(content=(
        "✅ **Interaction logged successfully!** The details (HCP Name, Date, "
        "Sentiment, and Materials) have been automatically populated based on "
        "your summary. Would you like me to suggest a specific follow-up "
        "action, such as scheduling a meeting?"
    )),
    # ---- chat turn 2: edit -------------------------------------------------
    AIMessage(content="", tool_calls=[{
        "name": "edit_interaction",
        "args": {"hcp_name": "Dr. John", "sentiment": "Negative"},
        "id": "call_2", "type": "tool_call",
    }]),
    AIMessage(content=(
        "Done — I updated the **HCP Name to Dr. John** and the **sentiment to "
        "Negative**. Everything else was kept exactly the same."
    )),
    # ---- chat turn 3: suggestions ------------------------------------------
    AIMessage(content="", tool_calls=[{
        "name": "suggest_follow_ups", "args": {}, "id": "call_3",
        "type": "tool_call",
    }]),
    AIMessage(content=(
        "Here are three follow-up suggestions — click any of them in the form "
        "to add it to Follow-up Actions."
    )),
]


class ScriptedLLM:
    def __init__(self, responses):
        self._responses = list(responses)
        self._i = 0

    def invoke(self, _messages):
        msg = self._responses[min(self._i, len(self._responses) - 1)]
        self._i += 1
        return msg


_llm = ScriptedLLM(SCRIPT)
graph_module.get_agent_llm = lambda model=None: _llm  # patch before app import

from app.main import app  # noqa: E402  (import after the patch)

if __name__ == "__main__":
    if os.path.exists("e2e_test.db"):
        os.remove("e2e_test.db")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
