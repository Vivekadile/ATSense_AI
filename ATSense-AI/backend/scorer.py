"""Deterministic ATS score.

Weights (must sum to 1.0). These are implementation choices, documented in
the README and exercised by ``tests/evaluate.py``:

    skills coverage      0.30   required-skill match (canonical sets)
    experience           0.20   candidate years vs. years the JD asks for
    education            0.10   candidate degree level vs. JD requirement
    keyword match        0.20   JD important-term presence in resume text
    semantic similarity  0.20   embedding cosine, resume vs. JD

``skills coverage`` and ``keyword match`` are computed from different inputs
in ``matcher.py`` so they are genuinely independent signals.
"""
WEIGHTS = {
    "skills": 0.30,
    "experience": 0.20,
    "education": 0.10,
    "keyword": 0.20,
    "semantic": 0.20,
}


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def calculate_experience_score(resume_data: dict, job_data: dict) -> float:
    have = float(resume_data.get("years_experience", 0) or 0)
    need = float(job_data.get("required_years_experience", 0) or 0)
    has_section = bool(resume_data.get("experience"))

    if need <= 0:
        if have >= 1 or has_section:
            return 100.0
        return 55.0

    if have >= need:
        return 100.0
    ratio = have / need
    floor = 45.0 if has_section else 20.0
    return _clamp(floor + (100.0 - floor) * ratio)


def calculate_education_score(resume_data: dict, job_data: dict) -> float:
    have = int(resume_data.get("education_level", 0) or 0)
    need = int(job_data.get("required_education_level", 0) or 0)
    has_section = bool(resume_data.get("education"))

    if need <= 0:
        if have >= 3:
            return 100.0
        if have >= 1 or has_section:
            return 75.0
        return 55.0

    if have >= need:
        return 100.0
    if have <= 0:
        return 50.0 if has_section else 30.0
    return _clamp(40.0 + 60.0 * (have / need))


def calculate_ats_score(matching_result: dict, resume_data: dict, job_data: dict) -> dict:
    skills_score = matching_result["skills_coverage_score"]
    experience_score = calculate_experience_score(resume_data, job_data)
    education_score = calculate_education_score(resume_data, job_data)
    keyword_score = matching_result["keyword_match_score"]
    semantic_score = matching_result["semantic_similarity_score"]

    overall = (
        WEIGHTS["skills"] * skills_score
        + WEIGHTS["experience"] * experience_score
        + WEIGHTS["education"] * education_score
        + WEIGHTS["keyword"] * keyword_score
        + WEIGHTS["semantic"] * semantic_score
    )

    return {
        "overall_score": round(_clamp(overall), 2),
        "skills_match_score": round(skills_score, 2),
        "experience_match_score": round(experience_score, 2),
        "education_match_score": round(education_score, 2),
        "keyword_match_score": round(keyword_score, 2),
        "semantic_similarity_score": round(semantic_score, 2),
        "weights": WEIGHTS,
    }
