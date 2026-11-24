"""Rule-based recommendations and job-category suggestions."""
from backend.skills_db import SKILL_CATEGORIES

JOB_CATEGORY_SKILLS = {
    "Machine Learning / AI Engineer": {
        "machine learning", "deep learning", "tensorflow", "pytorch",
        "scikit-learn", "computer vision", "natural language processing", "llm",
    },
    "Data Scientist": {
        "python", "machine learning", "pandas", "numpy", "scikit-learn",
        "matplotlib", "sql", "data science",
    },
    "Data Analyst": {
        "sql", "excel", "tableau", "power bi", "python", "pandas", "data analysis",
    },
    "Data Engineer": {
        "python", "sql", "spark", "airflow", "kafka", "dbt", "snowflake",
        "bigquery", "data engineering",
    },
    "Backend Developer": {
        "python", "java", "go", "node.js", "fastapi", "django", "flask",
        "express", "spring", "postgresql", "rest", "microservices",
    },
    "Frontend Developer": {
        "javascript", "typescript", "react", "vue", "angular", "next.js",
        "html", "css", "tailwind", "redux",
    },
    "Full Stack Developer": {
        "javascript", "typescript", "react", "node.js", "express", "postgresql",
        "mongodb", "rest", "python", "django",
    },
    "DevOps / Cloud Engineer": {
        "docker", "kubernetes", "aws", "azure", "gcp", "terraform", "ansible",
        "jenkins", "ci/cd", "linux", "prometheus",
    },
}


def suggest_job_categories(resume_skills):
    skills = set(resume_skills)
    scored = [
        (len(skills & keywords) / len(keywords), category)
        for category, keywords in JOB_CATEGORY_SKILLS.items()
        if len(skills & keywords) >= 2
    ]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [category for _, category in scored[:3]]


def _group_missing(missing):
    """Bucket missing skills by category for a more actionable message."""
    grouped = {}
    for skill in missing:
        for category, members in SKILL_CATEGORIES.items():
            if skill in members:
                grouped.setdefault(category, []).append(skill)
                break
        else:
            grouped.setdefault("other", []).append(skill)
    return grouped


def generate_recommendations(matching_result, resume_data, job_data):
    recommendations = []

    missing = matching_result.get("missing_skills", [])
    if missing:
        grouped = _group_missing(missing)
        for category, skills in grouped.items():
            label = "" if category == "other" else f" ({category})"
            recommendations.append(
                f"If you have relevant experience, make these skills explicit{label}: "
                + ", ".join(skills) + "."
            )

    if matching_result.get("partially_matched_skills"):
        recommendations.append(
            "You have adjacent skills for: "
            + ", ".join(matching_result["partially_matched_skills"])
            + ". Name the exact tools the job asks for if you've used them."
        )

    if matching_result["semantic_similarity_score"] < 60:
        recommendations.append(
            "Mirror the job description's wording in your experience bullets "
            "so the resume reads as a closer match."
        )

    need_years = job_data.get("required_years_experience", 0)
    have_years = resume_data.get("years_experience", 0)
    if need_years and have_years < need_years:
        recommendations.append(
            f"The role asks for ~{need_years:g} years; your resume shows ~{have_years:g}. "
            "Surface earlier roles, internships, or freelance work to close the gap."
        )

    if not resume_data.get("projects"):
        recommendations.append("Add relevant projects with technologies and measurable outcomes.")

    if not resume_data.get("experience"):
        recommendations.append(
            "Highlight internships, research, freelance, or other practical experience."
        )

    for issue in resume_data.get("_quality_issues", []):
        recommendations.append(issue)

    if not recommendations:
        recommendations.append(
            "The resume is well aligned. Focus on measurable achievements and "
            "keeping the most relevant skills prominent."
        )

    # de-dupe while preserving order
    seen = set()
    return [r for r in recommendations if not (r in seen or seen.add(r))]
