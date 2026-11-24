"""Resume quality heuristics — independent of any specific job."""
import re

_ACTION_VERBS = {
    "built", "led", "designed", "developed", "implemented", "created",
    "launched", "improved", "reduced", "increased", "optimized", "shipped",
    "architected", "migrated", "automated", "delivered", "owned", "drove",
}


def analyze_resume_quality(text: str, resume_data: dict) -> dict:
    words = text.split()
    word_count = len(words)

    sections = ["education", "experience", "projects", "certifications", "achievements"]
    present_sections = [s for s in sections if resume_data.get(s)]
    section_score = round(len(present_sections) / len(sections) * 100, 2)

    bullet_lines = [
        ln for ln in text.splitlines()
        if ln.strip().startswith(("-", "*", "•", "●", "▪"))
    ]
    quantified = len(re.findall(r"\b\d+(?:\.\d+)?\s*(?:%|percent|x|k\b|million|billion|\+)", text.lower()))
    action_verb_hits = sum(1 for w in words if w.lower().strip(".,") in _ACTION_VERBS)

    contact_fields = [resume_data.get("name"), resume_data.get("email"), resume_data.get("phone")]
    contact_complete = all(contact_fields)

    issues = []
    if word_count < 150:
        issues.append("Resume is very short — add detail to experience and projects.")
    elif word_count > 1200:
        issues.append("Resume is long — tighten to the most relevant content.")
    if not contact_complete:
        issues.append("Add complete contact details (name, email, phone).")
    if quantified == 0:
        issues.append("Add measurable outcomes (numbers, %, scale) to bullet points.")
    if action_verb_hits < 3:
        issues.append("Start bullet points with strong action verbs.")
    if len(present_sections) < 3:
        issues.append("Add the standard sections: experience, education, projects, skills.")

    return {
        "word_count": word_count,
        "section_score": section_score,
        "present_sections": present_sections,
        "bullet_points": len(bullet_lines),
        "quantified_results": quantified,
        "action_verbs": action_verb_hits,
        "contact_complete": contact_complete,
        "readability": "Good" if 150 <= word_count <= 1200 else "Review length",
        "structure": "Good" if len(present_sections) >= 3 else "Needs improvement",
        "issues": issues,
    }
