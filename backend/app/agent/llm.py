"""Groq LLM factories.

The brief mandates `gemma2-9b-it` (with `llama-3.3-70b-versatile` suggested
"for context"). Both are configurable through env vars; if the primary model
errors (e.g. it was decommissioned on Groq) the agent transparently retries
with the fallback model.
"""
from functools import lru_cache

from langchain_groq import ChatGroq

from .. import config


@lru_cache(maxsize=4)
def get_chat_model(model: str | None = None) -> ChatGroq:
    """Plain chat model (no tools bound). Used e.g. inside suggest_follow_ups."""
    return ChatGroq(
        model=model or config.GROQ_MODEL,
        api_key=config.GROQ_API_KEY or None,
        temperature=config.LLM_TEMPERATURE,
        max_retries=2,
    )


def get_primary_model_name() -> str:
    return config.GROQ_MODEL


def get_fallback_model_name() -> str:
    return config.GROQ_FALLBACK_MODEL
