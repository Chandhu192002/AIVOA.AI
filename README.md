# AI-First CRM — HCP Module · Log Interaction Screen

An **AI-first** "Log HCP Interaction" screen for pharma field representatives.
The screen is split in two: an **Interaction Details form** on the left and an
**AI Assistant chat** on the right. The golden rule of this build (per the
task video): **the form is never filled manually — the AI Assistant controls
it.** You describe the interaction in natural language; a **LangGraph agent**
running on **Groq `gemma2-9b-it`** extracts the details with tools and
populates the form (and the database) for you.

> "Today I met with Dr. Smith and discussed product X efficiency. The
> sentiment was positive, and I shared the brochures."
>
> → HCP Name = *Dr. Smith*, Date = *today*, Topics = *Product X efficiency*,
> Sentiment = *Positive*, Materials Shared = *Brochures* — all filled by the
> agent, live, on the left panel.

---

## Tech stack (as mandated by the brief)

| Layer      | Technology |
| ---------- | ---------- |
| Frontend   | React 18 + **Redux Toolkit** (Vite) |
| Backend    | Python + **FastAPI** |
| AI Agent   | **LangGraph** (`StateGraph`, agent ⇄ tools loop) |
| LLM        | **Groq `gemma2-9b-it`** (auto-fallback: `llama-3.3-70b-versatile`) |
| Database   | **PostgreSQL / MySQL** via SQLAlchemy (SQLite as zero-setup default) |
| Font       | **Google Inter** |

---

## Architecture

```
┌───────────────────────────────┐        ┌─────────────────────────────────────────┐
│  React + Redux (Vite, :5173)  │        │            FastAPI (:8000)              │
│                               │        │                                         │
│  LogInteractionForm  ◄─────┐  │        │  POST /api/chat                         │
│   (reads Redux form slice) │  │  HTTP  │     │                                   │
│                            └──┼────────┼──►  ▼        LangGraph StateGraph       │
│  AiAssistantPanel ─ sendMessage thunk  │   ┌────────┐  tool_calls   ┌─────────┐  │
│   (chat slice)                │        │   │ agent  │ ────────────► │  tools  │  │
│                               │        │   │ (Groq  │ ◄──────────── │  node   │  │
│  form_updates ◄───────────────┼────────┼── │ gemma2)│  ToolMessages └────┬────┘  │
│  applied to Redux form state  │        │   └────────┘                    │       │
└───────────────────────────────┘        │        ▲     5 CRM tools        ▼       │
                                         │        └── system prompt   SQLAlchemy   │
                                         │            + live form      (Postgres/  │
                                         │            state + date      MySQL/     │
                                         │                              SQLite)    │
                                         └─────────────────────────────────────────┘
```

One chat turn = one `graph.invoke(...)`:

1. **agent node** — the LLM sees the system prompt (with today's date and the
   *live form state*), the chat history, and the new message. It decides to
   answer directly or emit tool calls.
2. **tools node** — executes each requested tool inside a per-request
   `ToolContext`. Tools write to the DB and stage `form_updates`.
3. Loop back to **agent** for the final natural-language confirmation.
4. The API responds with `{reply, form_updates, suggested_followups,
   interaction_id, tool_calls}`. The React app pushes the reply into the chat
   and dispatches `form_updates` into the Redux form slice — the left panel
   updates in place (freshly-written fields flash briefly).

### Role of the LangGraph agent

The agent is the *single writer* for HCP interaction data. It interprets
free-text field-rep updates, chooses the right tool, converts fuzzy language
into structured CRM fields ("today" → `2026-07-14`, "positive" → `Positive`,
"the brochures" → `["Brochures"]`), keeps unrelated fields untouched on
edits, retrieves history, generates follow-up suggestions, and schedules
tasks — while the UI stays a thin, reactive view of Redux state.

---

## The five LangGraph tools

| # | Tool | What it does | Example prompt |
| - | ---- | ------------ | -------------- |
| 1 | **`log_interaction`** *(mandatory)* | Creates a NEW interaction. The LLM extracts HCP name, type, date/time, attendees, topics, materials, samples, sentiment, outcomes and follow-ups from the message; the tool normalises values (dates, sentiment casing, list parsing, HCP-directory name resolution), saves the row, and stages `form_updates` for every extracted field. | "Today I met with Dr. Smith and discussed product X efficiency. The sentiment was positive, and I shared the brochures." |
| 2 | **`edit_interaction`** *(mandatory)* | Partially updates the current interaction. The agent passes **only** the corrected fields; the tool patches the DB row and the form, and everything else is preserved exactly. | "Sorry, the name was actually Dr. John and the sentiment was negative." |
| 3 | **`get_interaction_history`** | Retrieves recent logged interactions, optionally filtered by HCP — grounding the agent's answers in real DB data. | "What did I log for Dr. John?" |
| 4 | **`suggest_follow_ups`** | Makes a *second LLM call* to generate exactly 3 short, context-aware follow-up actions for the interaction on screen. They render as clickable **AI Suggested Follow-ups** links; clicking one appends it to the *Follow-up Actions* field. | "Yes, please suggest follow-ups." |
| 5 | **`schedule_follow_up`** | Creates a scheduled task (`scheduled_followups` table) with a resolved due date, and mirrors the commitment into the form's *Follow-up Actions*. | "Schedule a follow-up meeting with Dr. John in two weeks." |

All five run **through the LangGraph graph and the Groq LLM** — nothing is
keyword-matched or hard-coded on the request path. (Tool #4 additionally has
a deterministic safety net *only* if the LLM call itself errors, so the UI
never breaks mid-demo.)

---

## Getting started

### 0. Prerequisites

- Python 3.11+ and Node 18+
- A free Groq API key → <https://console.groq.com/keys>
- (Optional) Docker, if you want the Postgres setup

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env       # then edit .env and paste your GROQ_API_KEY

uvicorn app.main:app --reload --port 8000
```

The API is now on <http://localhost:8000> (interactive docs at `/docs`).
Tables are created and 6 demo HCPs are seeded automatically on startup.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173> — and remember the rule: *don't touch the form*.
Talk to the assistant instead.

### 3. Database options

| Option | How |
| ------ | --- |
| **SQLite** (default) | Do nothing — `hcp_crm.db` is created automatically. Great for a quick run. |
| **PostgreSQL** (recommended for the demo) | `docker compose up -d` from the repo root, then set `DATABASE_URL=postgresql+psycopg2://crm:crm@localhost:5432/hcp_crm` in `backend/.env` and restart the backend. |
| **MySQL** | Set `DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/hcp_crm`. |

No migrations needed — the schema is created on startup.

---

## Try this exact demo flow

1. **Log** — type into the chat:
   `Today I met with Dr. Smith and discussed product X efficiency. The sentiment was positive, and I shared the brochures.`
   → watch HCP Name, Date, Topics, Sentiment and Materials fill themselves.
2. **Edit** — `Sorry, the name was actually Dr. John and the sentiment was negative.`
   → *only* those two fields change; topics/date/materials stay intact.
3. **Suggest** — `Yes, please suggest follow-ups.`
   → three **AI Suggested Follow-ups** links appear under the form; click one.
4. **Schedule** — `Schedule a follow-up meeting with Dr. John in two weeks.`
   → check `GET http://localhost:8000/api/followups`.
5. **History** — `What have I logged for Dr. John?`

---

## API reference

| Method & path | Purpose |
| ------------- | ------- |
| `POST /api/chat` | One agent turn. Body: `{message, history, form_state, interaction_id}` → `{reply, form_updates, suggested_followups, interaction_id, tool_calls, model_used}` |
| `GET /api/hcps` | Seeded HCP directory (feeds the form's autocomplete) |
| `GET /api/interactions?hcp_name=&limit=` | Logged interactions |
| `GET /api/followups` | Scheduled follow-up tasks |
| `GET /api/health` | Health + model configuration check |

---

## Tests (no API key needed)

```bash
cd backend
python -m scripts.smoke_test     # exercises the real LangGraph graph with a
                                 # scripted LLM: log → edit-preserves-fields →
                                 # history → schedule → no-tool turn
```

`scripts/e2e_harness.py` boots the same app with the scripted LLM on :8000 so
the full browser flow can be tested offline (it is a test harness only — the
real application requires `GROQ_API_KEY`).

---

## Project structure

```
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, startup seeding
│   │   ├── config.py            # env-driven settings
│   │   ├── database.py          # SQLAlchemy engine/session (PG/MySQL/SQLite)
│   │   ├── models.py            # HCP, Interaction, ScheduledFollowUp
│   │   ├── schemas.py           # Pydantic request/response models
│   │   ├── seed.py              # demo HCP directory
│   │   ├── agent/
│   │   │   ├── graph.py         # LangGraph StateGraph (agent ⇄ tools loop)
│   │   │   ├── tools.py         # the 5 tools + ToolContext + normalisers
│   │   │   ├── prompts.py       # system prompt w/ live date + form state
│   │   │   └── llm.py           # ChatGroq factory (primary + fallback)
│   │   └── routers/
│   │       ├── chat.py          # POST /api/chat → graph.invoke
│   │       └── interactions.py  # read-only data endpoints
│   └── scripts/
│       ├── smoke_test.py        # offline graph/tool tests
│       └── e2e_harness.py       # offline UI test server (scripted LLM)
├── frontend/
│   └── src/
│       ├── App.jsx              # split-screen layout
│       ├── App.css              # Inter font, reference-matching styles
│       ├── api/client.js        # fetch wrapper
│       ├── store/
│       │   ├── store.js         # Redux store
│       │   ├── formSlice.js     # form state + applies AI form_updates
│       │   └── chatSlice.js     # messages + sendMessage thunk
│       └── components/
│           ├── LogInteractionForm.jsx   # left panel (replica)
│           └── AiAssistantPanel.jsx     # right panel (chat)
├── docker-compose.yml           # optional Postgres
└── DEMO_SCRIPT.md               # 10–15 min recording outline
```

---

## Notes & troubleshooting

- **Model availability** — the brief mandates `gemma2-9b-it`. If Groq ever
  retires it, the backend automatically retries the same request on
  `GROQ_FALLBACK_MODEL` (`llama-3.3-70b-versatile`); both are configurable in
  `.env`. `GET /api/health` shows the active configuration, and each chat
  response reports `model_used`.
- **CORS errors** — add your frontend origin to `CORS_ORIGINS` in `backend/.env`.
- **"I could not reach the AI backend"** in the chat — the FastAPI server
  isn't running on :8000, or `GROQ_API_KEY` is missing/invalid.
- Small models occasionally phrase confirmations differently; all *data*
  normalisation (dates, sentiment, lists, names) happens in tool code, so the
  form always receives clean values.
`