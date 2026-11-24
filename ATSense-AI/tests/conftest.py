"""Shared test setup.

- Forces the deterministic pipeline (no LLM calls) for reproducibility.
- Stubs the sentence-transformer so unit tests don't download/load a model;
  the stub is a cheap token-overlap ratio, good enough for assertions.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("LLM_EXTRACTION_ENABLED", "false")
os.environ.pop("GROQ_API_KEY", None)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest


def _fake_similarity(resume_text: str, job_description: str) -> float:
    a = set(resume_text.lower().split())
    b = set(job_description.lower().split())
    if not a or not b:
        return 0.0
    return round(len(a & b) / len(a | b) * 100, 2)


@pytest.fixture(autouse=True)
def _stub_embeddings(monkeypatch):
    monkeypatch.setattr(
        "backend.matcher.calculate_semantic_similarity", _fake_similarity
    )
