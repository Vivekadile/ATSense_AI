"""Centralized configuration, loaded once from the environment.

Everything tunable lives here so the rest of the codebase never touches
``os.getenv`` directly.
"""
import os

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


# --- Groq / LLM -----------------------------------------------------------
_PLACEHOLDER_KEYS = {"", "your_groq_api_key_here", "changeme"}
_raw_key = (os.getenv("GROQ_API_KEY") or "").strip()
GROQ_API_KEY = None if _raw_key in _PLACEHOLDER_KEYS else _raw_key
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"
GROQ_TIMEOUT = _int("GROQ_TIMEOUT", 30)

# Use the LLM to *extract* skills/experience in addition to the qualitative
# analysis layer. Off by default: when on, LLM output feeds the score, so the
# same resume can score differently between runs. Extraction always falls back
# to the deterministic parser when this is off, the key is missing, or the
# call fails.
LLM_EXTRACTION_ENABLED = _bool("LLM_EXTRACTION_ENABLED", False)

# --- Uploads ------------------------------------------------------------
MAX_UPLOAD_BYTES = _int("MAX_UPLOAD_BYTES", 5 * 1024 * 1024)  # 5 MB
MAX_JD_CHARS = _int("MAX_JD_CHARS", 50_000)

# --- CORS -------------------------------------------------------------------
# Comma-separated list of allowed origins. "*" allows all (dev default).
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "*").split(",")
    if origin.strip()
]


def groq_configured() -> bool:
    return bool(GROQ_API_KEY)
