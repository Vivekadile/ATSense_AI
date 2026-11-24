"""Compare a parsed resume against an analyzed job description.

Produces two *distinct* lexical signals so the scorer isn't double-counting:
  - ``skills_coverage_score`` — share of required *skills* the candidate has
    (canonical set comparison, with half credit for same-family partials).
  - ``keyword_match_score`` — share of the JD's important *terms* that appear
    verbatim in the resume text (includes non-taxonomy words like domain
    nouns, tools, and phrases).
"""
import re
from collections import Counter

from backend.embeddings import calculate_semantic_similarity
from backend.skills_db import related_skills

_STOPWORDS = {
    "the", "and", "for", "with", "you", "our", "are", "will", "have", "this",
    "that", "your", "from", "not", "who", "all", "can", "was", "has",
    "job", "work", "team", "role", "years", "year", "experience", "skills",
    "ability", "strong", "good", "plus", "etc", "including", "such", "must",
    "should", "would", "using", "used", "use", "well", "like", "help", "into",
    "across", "within", "their", "them", "they", "what", "when", "how",
    "requirements", "responsibilities", "qualifications", "preferred",
}


def _keyword_terms(job_data: dict) -> set[str]:
    terms = set(job_data.get("required_skills", [])) | set(job_data.get("preferred_skills", []))
    tokens = re.findall(r"[a-zA-Z][a-zA-Z+#.\-]{3,}", job_data.get("raw_text", "").lower())
    # sentence punctuation ("python.") must not split a term from its plain form
    tokens = (t.rstrip(".-") for t in tokens)
    counts = Counter(t for t in tokens if len(t) >= 4 and t not in _STOPWORDS)
    for term, freq in counts.most_common(40):
        if freq >= 2:
            terms.add(term)
    return {t for t in terms if t}


def match_resume_with_job(
    resume_data: dict,
    job_data: dict,
    resume_text: str,
    job_description: str,
) -> dict:
    resume_skills = set(resume_data.get("skills", []))
    required_skills = set(job_data.get("required_skills", []))
    preferred_skills = set(job_data.get("preferred_skills", []))

    matched = resume_skills & required_skills
    missing = required_skills - resume_skills
    preferred_matched = resume_skills & preferred_skills

    partial = {
        skill for skill in missing
        if resume_skills & related_skills(skill)
    }
    missing -= partial

    total_required = len(required_skills)
    skills_coverage = (
        (len(matched) + 0.5 * len(partial)) / total_required * 100
        if total_required else 100.0
    )

    resume_lower = resume_text.lower()
    terms = _keyword_terms(job_data)
    hit = {t for t in terms if re.search(rf"(?<!\w){re.escape(t)}(?!\w)", resume_lower)}
    keyword_score = (len(hit) / len(terms) * 100) if terms else 100.0

    semantic_score = calculate_semantic_similarity(resume_text, job_description)

    return {
        "matched_skills": sorted(matched),
        "partially_matched_skills": sorted(partial),
        "missing_skills": sorted(missing),
        "preferred_matched_skills": sorted(preferred_matched),
        "skills_coverage_score": round(skills_coverage, 2),
        "keyword_match_score": round(keyword_score, 2),
        "matched_keywords": sorted(hit),
        "missing_keywords": sorted(terms - hit),
        "semantic_similarity_score": semantic_score,
    }
