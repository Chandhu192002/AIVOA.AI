# Demo Video Script (10–15 minutes)

A suggested outline that hits every deliverable in the brief: frontend
walkthrough, **all 5 LangGraph tools working**, code structure, and a summary
of the task understanding.

> Before recording: backend running with your `GROQ_API_KEY` set (Postgres via
> `docker compose up -d` if you want to show the mandated DB), frontend on
> :5173, browser zoom 100%. Have `http://localhost:8000/docs` open in a
> second tab.

---

## 1. Intro & task understanding (≈1.5 min)

- "This is the Log Interaction screen of an AI-first CRM's HCP module, built
  for pharma field reps."
- State the golden rule from the instructions: **the form on the left is
  never filled manually — the AI Assistant on the right controls it** through
  a LangGraph agent running on Groq `gemma2-9b-it`.
- Name the stack: React + Redux, FastAPI, LangGraph, Groq, Postgres, Inter font.

## 2. Frontend walkthrough (≈2 min)

- Point out the split layout replicating the reference: Interaction Details
  (HCP Name, Type, Date, Time, Attendees, Topics, voice-note consent link,
  Materials/Samples, Sentiment radios, Outcomes, Follow-up Actions) and the
  AI Assistant panel with its hint bubble and "Describe Interaction…" input.
- Mention Redux: the form is a view over the `form` slice; the chat drives it.

## 3. Tool demos (≈6 min) — the core of the video

**Tool 1 · log_interaction** — type:
`Today I met with Dr. Smith and discussed product X efficiency. The sentiment was positive, and I shared the brochures.`
Narrate the fields filling live (name, date = today, topics, sentiment,
materials) and the green success reply.

**Tool 2 · edit_interaction** — type:
`Sorry, the name was actually Dr. John and the sentiment was negative.`
Emphasise: *only* those two fields changed; topics, date and materials were
preserved — the tool patches, never overwrites.

**Tool 3 · suggest_follow_ups** — type:
`Yes, please suggest follow-ups.`
Show the three **AI Suggested Follow-ups** links appearing; click one and show
it appended to Follow-up Actions. Mention this is a second LLM call inside the
tool.

**Tool 4 · schedule_follow_up** — type:
`Schedule a follow-up meeting with Dr. John in two weeks.`
Then open `http://localhost:8000/api/followups` (or `/docs`) and show the
persisted task with the resolved due date.

**Tool 5 · get_interaction_history** — type:
`What have I logged for Dr. John?`
Show the grounded answer, then `GET /api/interactions` to prove it came from
the database.

## 4. Code & structure explanation (≈4 min)

Open the repo and walk through, briefly:

- `backend/app/agent/graph.py` — the LangGraph `StateGraph`: `agent` node
  (LLM with 5 tools bound) ⇄ `tools` node, conditional edge on
  `tool_calls`, state carrying `messages`, `form_state`, `form_updates`.
- `backend/app/agent/tools.py` — the five `@tool` functions, the
  `ToolContext`, and the normalisers (dates, sentiment, list parsing).
- `backend/app/agent/prompts.py` — system prompt injecting today's date and
  the live form state (how "today" becomes a real date).
- `backend/app/routers/chat.py` — one POST = one `graph.invoke`, returning
  `reply + form_updates`.
- `frontend/src/store/chatSlice.js` & `formSlice.js` — the `sendMessage`
  thunk, and the extraReducer that applies `form_updates` to the form (the
  chat→form wiring in Redux).
- Mention `scripts/smoke_test.py`: the graph and all tools are covered by an
  offline test.

## 5. Summary (≈1 min)

- Recap: conversational *and* structured logging in one screen; LangGraph +
  Groq mandated stack respected; edit preserves untouched fields; data lands
  in Postgres/MySQL; five tools, all LLM-driven, none hard-coded.
- Close with what you'd add next (auth, voice-note transcription with consent
  capture, HCP 360 view, compliance checks).
