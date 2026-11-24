"""Turn a job description into required vs. preferred skill sets.

Preferred detection is *clause aware*. The posting is split into clauses
(lines / sentences), each clause gets a polarity from the cue words it
contains ("required", "must have" … vs. "preferred", "nice to have",
"is a plus" …), and clauses with no cue inherit the polarity of the last
one that had a cue. This handles headed bullet lists, single-paragraph
blurbs, and trailing modifiers ("TensorFlow experience preferred.") alike
— the original code only handled headed lists and mislabelled everything
"preferred" whenever the word appeared once.
"""
import re

from backend import config, experience
from backend.llm import extract_entities
from backend.skills_db import extract_skills_from_text, normalize_skills

# split on newlines and after sentence punctuation followed by whitespace;
# the lookbehind keeps dotted tokens like "node.js" / "next.js" intact.
_CLAUSE_SPLIT = re.compile(r"\n+|(?<=[.;:])\s+")

_PREFERRED_CUES = [
    "preferred", "nice to have", "nice-to-have", "good to have",
    "good-to-have", "is a plus", "are a plus", "would be a plus", "a plus",
    "bonus", "desirable", "ideally", "would be nice", "would be great",
    "not required", "pluses",
]
_REQUIRED_CUES = [
    "required", "must have", "must-have", "requirement", "responsibilities",
    "minimum", "we need", "we're looking for", "we are looking for",
    "essential", "you must", "qualifications", "what you'll do",
]


def _polarity(clause: str) -> str | None:
    low = clause.lower()
    if any(cue in low for cue in _PREFERRED_CUES):
        return "preferred"
    if any(cue in low for cue in _REQUIRED_CUES):
        return "required"
    return None


def _split_skills(job_description: str) -> tuple[set[str], set[str]]:
    required: set[str] = set()
    preferred: set[str] = set()

    current = "required"
    for clause in _CLAUSE_SPLIT.split(job_description):
        if not clause.strip():
            continue
        polarity = _polarity(clause)
        if polarity:
            current = polarity
        bucket = preferred if current == "preferred" else required
        bucket.update(extract_skills_from_text(clause))

    preferred -= required
    for skill in extract_skills_from_text(job_description):
        if skill not in preferred:
            required.add(skill)
    return required, preferred


def analyze_job_description(job_description: str, *, use_llm: bool = True) -> dict:
    required, preferred = _split_skills(job_description)

    req_years = experience.required_years_from_job(job_description)
    req_edu = experience.required_education_from_job(job_description)

    if use_llm and config.LLM_EXTRACTION_ENABLED:
        entities = extract_entities(job_description)
        if entities:
            for skill in normalize_skills(entities["skills"]):
                if skill not in preferred:
                    required.add(skill)
            req_years = max(req_years, entities["years_experience"])
            req_edu = max(req_edu, entities["education_level"])

    return {
        "required_skills": normalize_skills(required),
        "preferred_skills": normalize_skills(preferred),
        "required_years_experience": round(req_years, 1),
        "required_education_level": req_edu,
        "raw_text": job_description,
    }
