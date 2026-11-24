from backend.scorer import (
    WEIGHTS,
    calculate_ats_score,
    calculate_education_score,
    calculate_experience_score,
)


def test_weights_sum_to_one():
    assert round(sum(WEIGHTS.values()), 6) == 1.0


def test_experience_meets_requirement():
    assert calculate_experience_score({"years_experience": 6}, {"required_years_experience": 4}) == 100.0


def test_experience_below_requirement_scales_with_floor():
    score = calculate_experience_score(
        {"years_experience": 1, "experience": "some job"},
        {"required_years_experience": 5},
    )
    assert 45.0 <= score < 100.0


def test_experience_no_requirement_presence_based():
    assert calculate_experience_score({"experience": "x"}, {}) == 100.0
    assert calculate_experience_score({}, {}) == 55.0


def test_education_levels():
    assert calculate_education_score({"education_level": 4}, {"required_education_level": 3}) == 100.0
    assert calculate_education_score({"education_level": 0, "education": "x"}, {"required_education_level": 4}) == 50.0


def test_overall_score_uses_distinct_skill_and_keyword_inputs():
    matching = {
        "skills_coverage_score": 100.0,
        "keyword_match_score": 40.0,
        "semantic_similarity_score": 50.0,
    }
    resume = {"years_experience": 5, "education_level": 3, "experience": "x", "education": "x"}
    job = {"required_years_experience": 3, "required_education_level": 3}
    result = calculate_ats_score(matching, resume, job)
    expected = (
        0.30 * 100 + 0.20 * 100 + 0.10 * 100 + 0.20 * 40 + 0.20 * 50
    )
    assert result["overall_score"] == round(expected, 2)


def test_score_is_clamped_0_100():
    matching = {"skills_coverage_score": 100, "keyword_match_score": 100, "semantic_similarity_score": 100}
    resume = {"years_experience": 20, "education_level": 5, "experience": "x", "education": "x"}
    job = {}
    assert calculate_ats_score(matching, resume, job)["overall_score"] <= 100.0
