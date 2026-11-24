from backend.jd_analyzer import analyze_job_description

JD = """Senior Backend Engineer

Requirements:
- 5+ years of experience with Python
- Solid SQL and PostgreSQL knowledge
- Experience running Docker in production

Preferred qualifications:
- Familiarity with Kubernetes
- React experience is a nice to have
- Kafka is a plus
"""


def test_required_vs_preferred_split():
    data = analyze_job_description(JD, use_llm=False)
    assert {"python", "sql", "postgresql", "docker"} <= set(data["required_skills"])
    assert {"kubernetes", "react", "kafka"} <= set(data["preferred_skills"])


def test_preferred_word_elsewhere_does_not_leak_everything():
    """Regression: the word 'preferred' in one section must not flip every
    skill to preferred (the original bug)."""
    data = analyze_job_description(JD, use_llm=False)
    assert "python" in data["required_skills"]
    assert "python" not in data["preferred_skills"]
    assert data["required_skills"]  # non-empty


def test_required_skill_also_mentioned_in_preferred_stays_required():
    jd = """Requirements:
- Must have Python and Docker

Nice to have:
- More Python and Docker exposure
"""
    data = analyze_job_description(jd, use_llm=False)
    assert "python" in data["required_skills"]
    assert "docker" in data["required_skills"]
    assert "python" not in data["preferred_skills"]


def test_single_line_unstructured_jd():
    """Regression: a one-paragraph JD with the word 'preferred' must not
    dump every skill into preferred."""
    jd = (
        "Backend Engineer. Requirements: 3+ years Python, PostgreSQL, Docker, "
        "REST APIs. Preferred: AWS is a plus, Kubernetes nice to have."
    )
    data = analyze_job_description(jd, use_llm=False)
    assert set(data["required_skills"]) == {"python", "postgresql", "docker", "rest"}
    assert set(data["preferred_skills"]) == {"aws", "kubernetes"}


def test_trailing_preferred_modifier():
    """Regression: 'X preferred' after the skill still marks X preferred."""
    jd = "Data scientist skilled in Python and pandas. TensorFlow experience preferred."
    data = analyze_job_description(jd, use_llm=False)
    assert "python" in data["required_skills"]
    assert "tensorflow" in data["preferred_skills"]
    assert "tensorflow" not in data["required_skills"]


def test_no_markers_everything_required():
    data = analyze_job_description(
        "Looking for React, TypeScript and CSS experience.", use_llm=False
    )
    assert set(data["required_skills"]) == {"react", "typescript", "css"}
    assert data["preferred_skills"] == []


def test_required_years_and_education():
    jd = "We need 3+ years of experience and a Bachelor degree in CS. Python required."
    data = analyze_job_description(jd, use_llm=False)
    assert data["required_years_experience"] == 3.0
    assert data["required_education_level"] == 3
