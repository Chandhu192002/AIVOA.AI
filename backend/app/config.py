"""Application configuration.

All runtime settings come from environment variables (a local `.env` file is
loaded automatically). See `.env.example` for the full list.
"""
import os

from dotenv import load_dotenv

load_dotenv()

# --- Groq / LLM ------------------------------------------------------------
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

# Primary model required by the assignment brief.
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "gemma2-9b-it")

# Larger model suggested by the brief "for context" – used automatically if
# the primary model is unavailable (e.g. decommissioned) or fails a request.
GROQ_FALLBACK_MODEL: str = os.getenv("GROQ_FALLBACK_MODEL", "llama-3.3-70b-versatile")

LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0"))

# --- Database ---------------------------------------------------------------
# Per the assignment spec use Postgres or MySQL, e.g.:
#   postgresql+psycopg2://crm:crm@localhost:5432/hcp_crm
#   mysql+pymysql://crm:crm@localhost:3306/hcp_crm
# SQLite is the zero-setup default so the project runs out of the box.
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./hcp_crm.db")

# --- API --------------------------------------------------------------------
CORS_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if o.strip()
]
