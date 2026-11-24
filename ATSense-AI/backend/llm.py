"""Groq/Qwen LLM layer.

Two independent uses, both optional and both with safe fallbacks:
  1. ``extract_entities`` — pull skills / years / education from raw text.
  2. ``get_ai_analysis`` — qualitative summary on top of deterministic ATS
     results. Never influences the numeric score.
"""
import json

import requests

from backend import config

ANALYSIS_SYSTEM_PROMPT = (
    "You are an ATS resume reviewer. Base your assessment only on the "
    "supplied resume data, job description data, and ATS results. Do not "
    "invent skills, experience, or qualifications that are not present in "
    "the evidence. Respond with a single JSON object containing exactly "
    "these keys: summary (string), strengths (array of strings), gaps "
    "(array of strings), recommendations (array of strings)."
)

EXTRACTION_SYSTEM_PROMPT = (
    "You extract structured facts from a piece of text (a resume or a job "
    "description). Respond with a single JSON object with keys: "
    "skills (array of short lowercase technology/skill names), "
    "years_experience (number, 0 if unknown), "
    "education_level (one of: none, high school, associate, bachelor, master, phd). "
    "Only report skills that are explicitly present. Do not infer or invent."
)

_EDU_MAP = {
    "none": 0, "high school": 1, "associate": 2,
    "bachelor": 3, "master": 4, "phd": 5,
}


_CONTACT_FIELDS = {"name", "email", "phone"}


class GroqNotConfiguredError(RuntimeError):
    pass


def _headers():
    return {"Authorization": f"Bearer {config.GROQ_API_KEY}"}


def _chat(system_prompt: str, user_payload, *, timeout: int) -> dict:
    response = requests.post(
        config.GROQ_CHAT_URL,
        headers=_headers(),
        json={
            "model": config.GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_payload},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        },
        timeout=timeout,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)


# --- extraction ---------------------------------------------------------------

def extract_entities(text: str) -> dict | None:
    """Return ``{"skills": [...], "years_experience": float, "education_level": int}``.

    Returns ``None`` when extraction is disabled, unconfigured, or fails, so
    callers can fall back to deterministic parsing.
    """
    if not config.LLM_EXTRACTION_ENABLED or not config.groq_configured():
        return None
    try:
        parsed = _chat(
            EXTRACTION_SYSTEM_PROMPT,
            text[:12_000],
            timeout=config.GROQ_TIMEOUT,
        )
    except (requests.RequestException, ValueError, KeyError):
        return None

    skills = parsed.get("skills", [])
    if not isinstance(skills, list):
        skills = []

    try:
        years = float(parsed.get("years_experience", 0) or 0)
    except (TypeError, ValueError):
        years = 0.0

    edu_raw = str(parsed.get("education_level", "none")).strip().lower()

    return {
        "skills": [s for s in skills if isinstance(s, str)],
        "years_experience": max(0.0, years),
        "education_level": _EDU_MAP.get(edu_raw, 0),
    }


# --- qualitative analysis ---------------------------------------------------

def get_ai_analysis(resume_data: dict, job_data: dict, ats_report: dict) -> dict:
    if not config.groq_configured():
        raise GroqNotConfiguredError("GROQ_API_KEY is not configured.")

    # contact details add nothing to the assessment; keep them off the wire
    resume = {k: v for k, v in resume_data.items() if k not in _CONTACT_FIELDS}
    user_prompt = json.dumps({
        "resume": resume,
        "job_description": job_data,
        "ats_results": ats_report,
    })
    parsed = _chat(ANALYSIS_SYSTEM_PROMPT, user_prompt, timeout=config.GROQ_TIMEOUT)

    return {
        "summary": parsed.get("summary", ""),
        "strengths": parsed.get("strengths", []),
        "gaps": parsed.get("gaps", []),
        "recommendations": parsed.get("recommendations", []),
    }


def test_groq_connection() -> dict:
    if not config.groq_configured():
        return {"connected": False, "detail": "GROQ_API_KEY is not configured."}
    try:
        response = requests.get(
            config.GROQ_MODELS_URL, headers=_headers(), timeout=10
        )
        response.raise_for_status()
        available = {m.get("id") for m in response.json().get("data", [])}
    except (requests.RequestException, ValueError) as exc:
        return {"connected": False, "detail": str(exc)}
    if config.GROQ_MODEL not in available:
        return {
            "connected": False,
            "model": config.GROQ_MODEL,
            "detail": f"Model '{config.GROQ_MODEL}' is not available on Groq. Set GROQ_MODEL in .env.",
        }
    return {"connected": True, "model": config.GROQ_MODEL}
