"""FastAPI application — AI-First CRM · HCP Module backend."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .database import Base, SessionLocal, engine
from .routers import chat, interactions
from .seed import seed_hcps

app = FastAPI(
    title="AI-First CRM — HCP Module",
    description=(
        "Backend for the Log Interaction screen. A LangGraph agent (Groq "
        "gemma2-9b-it) drives the form through five tools: log_interaction, "
        "edit_interaction, get_interaction_history, suggest_follow_ups and "
        "schedule_follow_up."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(interactions.router)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_hcps(db)


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "model": config.GROQ_MODEL,
        "fallback_model": config.GROQ_FALLBACK_MODEL,
        "groq_key_configured": bool(config.GROQ_API_KEY),
    }
