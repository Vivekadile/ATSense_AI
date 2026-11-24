from backend.matcher import match_resume_with_job


def _job(required, preferred=(), raw=""):
    return {
        "required_skills": list(required),
        "preferred_skills": list(preferred),
        "raw_text": raw or " ".join(required),
    }


def test_full_coverage():
    resume = {"skills": ["python", "sql", "docker"]}
    job = _job(["python", "sql", "docker"])
    m = match_resume_with_job(resume, job, "python sql docker", "python sql docker")
    assert m["skills_coverage_score"] == 100.0
    assert m["missing_skills"] == []


def test_partial_family_credit():
    resume = {"skills": ["pytorch"]}
    job = _job(["tensorflow"])
    m = match_resume_with_job(resume, job, "pytorch", "tensorflow")
    assert "tensorflow" in m["partially_matched_skills"]
    assert m["missing_skills"] == []
    assert m["skills_coverage_score"] == 50.0  # half credit


def test_missing_skill_reported():
    resume = {"skills": ["python"]}
    job = _job(["python", "kubernetes"])
    m = match_resume_with_job(resume, job, "python", "python kubernetes")
    assert m["missing_skills"] == ["kubernetes"]
    assert m["skills_coverage_score"] == 50.0


def test_keyword_score_is_text_based_not_skill_based():
    resume = {"skills": ["python", "sql"]}
    job = _job(
        ["python", "sql"],
        raw="python python sql sql fintech fintech payments payments ledger ledger",
    )
    m = match_resume_with_job(resume, job, "python and sql only", job["raw_text"])
    # skills fully covered, but domain keywords missing -> scores diverge
    assert m["skills_coverage_score"] == 100.0
    assert m["keyword_match_score"] < 100.0


def test_no_required_skills_is_full_coverage_not_zero():
    m = match_resume_with_job({"skills": []}, _job([]), "text", "text")
    assert m["skills_coverage_score"] == 100.0


def test_keywords_ignore_trailing_punctuation():
    from backend.matcher import _keyword_terms

    terms = _keyword_terms({"raw_text": "Experience with python. We use python daily. Kubernetes, kubernetes."})
    assert {"python", "kubernetes"} <= terms
    assert not any(t.endswith(".") for t in terms)
