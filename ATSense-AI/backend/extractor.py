"""Structured extraction from raw resume text.

Deterministic first: regex contact details, a dictionary skill scan, and
header-based sectioning. When LLM extraction is enabled the skills / years /
education signals are merged with the model's output (union for skills,
max for the numeric signals) — the deterministic result is always the floor.
"""
import re

from backend import experience
from backend.llm import extract_entities
from backend.skills_db import extract_skills_from_text, normalize_skills

SECTION_ALIASES = {
    "summary": ["summary", "professional summary", "objective", "profile"],
    "education": ["education", "academic background", "academics", "qualifications"],
    "experience": [
        "experience", "work experience", "professional experience",
        "employment history", "work history",
    ],
    "projects": ["projects", "academic projects", "personal projects", "key projects"],
    "skills": ["skills", "technical skills", "core competencies", "technologies"],
    "certifications": ["certifications", "certificates", "licenses"],
    "achievements": ["achievements", "awards", "honors", "accomplishments"],
}

_NORMALIZED_HEADERS = {
    alias: canonical
    for canonical, aliases in SECTION_ALIASES.items()
    for alias in aliases
}


def extract_resume_information(text: str, *, use_llm: bool = True) -> dict:
    sections = extract_sections(text)

    dict_skills = extract_skills_from_text(text)
    # date ranges come from the experience section; without one, drop the
    # education section so degree dates aren't counted as work history
    dated_text = sections.get("experience") or text.replace(sections.get("education") or "\0", "")
    years = experience.estimate_years_experience(text, dated_text)
    edu_level = experience.detect_education_level(text)
    skill_source = "dictionary"

    if use_llm:
        entities = extract_entities(text)
        if entities:
            dict_skills = sorted(set(dict_skills) | set(entities["skills"]))
            years = max(years, entities["years_experience"])
            edu_level = max(edu_level, entities["education_level"])
            skill_source = "dictionary+llm"

    return {
        "name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "skills": normalize_skills(dict_skills),
        "years_experience": round(years, 1),
        "education_level": edu_level,
        "skill_source": skill_source,
        "summary": sections.get("summary", ""),
        "education": sections.get("education", ""),
        "experience": sections.get("experience", ""),
        "projects": sections.get("projects", ""),
        "skills_section": sections.get("skills", ""),
        "certifications": sections.get("certifications", ""),
        "achievements": sections.get("achievements", ""),
    }


def extract_name(text: str):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines[:5]:
        if "@" in line or re.search(r"\d{7,}", line):
            continue
        if 1 <= len(line.split()) <= 5 and not _NORMALIZED_HEADERS.get(line.lower().rstrip(":")):
            return line
    return None


def extract_email(text: str):
    match = re.search(r"[\w.+'-]+@[\w.-]+\.\w+", text)
    return match.group(0) if match else None


def extract_phone(text: str):
    cleaned = re.sub(r"[()]", "", text)
    match = re.search(r"(?:\+\d{1,3}[\s-]?)?(?:\d[\s-]?){9,12}\d", cleaned)
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group(0))
    return match.group(0).strip() if 10 <= len(digits) <= 15 else None


def extract_sections(text: str) -> dict:
    sections = {}
    current = None
    buffer = []

    for line in text.splitlines():
        stripped = line.strip()
        key = stripped.lower().rstrip(":").strip()

        if key in _NORMALIZED_HEADERS and len(stripped) <= 40:
            if current:
                sections[current] = "\n".join(buffer).strip()
            current = _NORMALIZED_HEADERS[key]
            buffer = []
        elif current:
            buffer.append(stripped)

    if current:
        sections[current] = "\n".join(buffer).strip()

    return sections
