from backend import skills_db


def test_aliases_normalize_to_canonical():
    assert skills_db.normalize_skill("JS") == "javascript"
    assert skills_db.normalize_skill("sklearn") == "scikit-learn"
    assert skills_db.normalize_skill("k8s") == "kubernetes"
    assert skills_db.normalize_skill("Amazon Web Services") == "aws"


def test_unknown_skill_is_kept_lowercased():
    assert skills_db.normalize_skill("Elixir") == "elixir"


def test_normalize_skills_dedupes_and_sorts():
    out = skills_db.normalize_skills(["Python", "py", "TensorFlow", "keras"])
    assert out == ["python", "tensorflow"]


def test_extract_skills_from_text_word_boundaries():
    found = skills_db.extract_skills_from_text(
        "Experienced in Python and React; also touched Rust."
    )
    assert {"python", "react", "rust"} <= set(found)
    # 'r' alias must not fire inside 'Rust'
    assert "r" not in found


def test_related_skills_same_family():
    assert "pytorch" in skills_db.related_skills("tensorflow")
    assert "gcp" in skills_db.related_skills("aws")
    assert skills_db.related_skills("python") & {"java", "go"}
