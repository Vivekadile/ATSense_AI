import io

import pytest
from fastapi.testclient import TestClient

RESUME_TXT = b"""Alex Kim
alex.kim@example.com
+1 206 555 0142

Summary
Full stack developer with 4 years of experience.

Experience
Software Engineer, WebCo  2021 - Present
- Built React and Node.js apps backed by PostgreSQL
- Set up CI/CD with GitHub Actions and Docker

Education
Bachelor of Science in Computer Science

Skills
JavaScript, TypeScript, React, Node.js, PostgreSQL, Docker, AWS
"""

JD = """Frontend Engineer

Requirements:
- 3+ years of experience with JavaScript and React
- Strong HTML and CSS
- Experience with TypeScript

Preferred:
- Next.js
- AWS exposure is a plus
"""


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from backend import database

    # save_analysis / get_history read DB_PATH from the module at call time
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    database.init_db()

    from backend.main import app

    with TestClient(app) as c:
        yield c


def _files():
    return {"resume": ("resume.txt", io.BytesIO(RESUME_TXT), "text/plain")}


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_resume_parse(client):
    r = client.post("/api/resume/parse", files=_files())
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "alex.kim@example.com"
    assert "react" in body["skills"]


def test_job_analyze(client):
    r = client.post("/api/job/analyze", data={"job_description": JD})
    assert r.status_code == 200
    body = r.json()
    assert "javascript" in body["required_skills"]
    assert "next.js" in body["preferred_skills"]
    assert "raw_text" not in body


def test_ats_score_end_to_end(client):
    r = client.post("/api/ats/score", files=_files(), data={"job_description": JD})
    assert r.status_code == 200
    body = r.json()
    assert 0 <= body["ats_report"]["overall_ats_score"] <= 100
    assert body["ats_report"]["scores"]["weights"]
    assert isinstance(body["recommendations"], list)
    assert "analysis_id" in body

    hist = client.get("/api/history")
    assert hist.status_code == 200
    assert len(hist.json()) >= 1


def test_ats_score_rejects_short_jd(client):
    r = client.post("/api/ats/score", files=_files(), data={"job_description": "too short"})
    assert r.status_code == 400


def test_ats_score_rejects_bad_file_type(client):
    files = {"resume": ("resume.exe", io.BytesIO(b"x" * 100), "application/octet-stream")}
    r = client.post("/api/ats/score", files=files, data={"job_description": JD})
    assert r.status_code == 400


def test_ai_analysis_omits_contact_details(monkeypatch):
    from backend import config, llm

    sent = {}

    def fake_chat(system_prompt, user_payload, *, timeout):
        sent["payload"] = user_payload
        return {"summary": "", "strengths": [], "gaps": [], "recommendations": []}

    monkeypatch.setattr(config, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(llm, "_chat", fake_chat)
    llm.get_ai_analysis(
        {"name": "Alex Kim", "email": "alex@example.com", "phone": "+1 206", "skills": ["react"]},
        {}, {},
    )
    assert "alex@example.com" not in sent["payload"]
    assert "Alex Kim" not in sent["payload"]
    assert "react" in sent["payload"]
