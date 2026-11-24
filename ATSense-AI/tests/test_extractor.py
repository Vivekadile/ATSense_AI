from backend.extractor import extract_resume_information

RESUME = """Jane Smith
jane.smith@example.com
+44 20 7946 0958

Summary
Data scientist with 5 years of experience in machine learning.

Experience
ML Engineer, DataCorp  Jan 2020 - Present
- Built NLP pipelines with PyTorch and Hugging Face
- Deployed models on GCP

Education
Master of Science in Statistics

Skills
Python, PyTorch, NLP, SQL, GCP, Docker
"""


def test_contact_details():
    data = extract_resume_information(RESUME, use_llm=False)
    assert data["name"] == "Jane Smith"
    assert data["email"] == "jane.smith@example.com"
    assert data["phone"] is not None


def test_skills_are_canonical():
    data = extract_resume_information(RESUME, use_llm=False)
    assert {"python", "pytorch", "natural language processing", "sql", "gcp", "docker"} <= set(
        data["skills"]
    )


def test_years_and_education_level():
    data = extract_resume_information(RESUME, use_llm=False)
    assert data["years_experience"] == 5.0
    assert data["education_level"] == 4  # master


def test_sections_split():
    data = extract_resume_information(RESUME, use_llm=False)
    assert "DataCorp" in data["experience"]
    assert "Statistics" in data["education"]
    assert data["skill_source"] == "dictionary"


def test_fresher_degree_dates_are_not_experience():
    resume = """Priya Nair
priya@example.com
+91 98765 43210

Education
B.Tech Computer Science, 2019 - 2023

Experience
Software Intern, Jan 2023 - Jun 2023
"""
    data = extract_resume_information(resume, use_llm=False)
    assert data["years_experience"] < 1
