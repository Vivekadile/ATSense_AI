"""Deterministic parsing of experience duration and education level.

Used by the scorer so experience/education contribute a real signal rather
than a flat "section present" boolean.
"""
import re
from datetime import date

# Degree patterns run against lowercased text. Word boundaries / required
# context keep everyday words from matching: "you will be building" is not a
# B.E., "Scrum Master" is not a master's degree, "Associate Engineer" is not
# an associate degree.
DEGREE_PATTERNS = [
    (5, r"\bph\.?\s?d\b|\bdoctorate\b"),
    (4, r"\bmaster'?s\b|\bmasters?\s+(?:of|in|degree)\b|\bm\.\s?s\.?(?!\w)"
        r"|\bm\.?\s?sc\b|\bm\.?\s?tech\b|\bmba\b"),
    (3, r"\bbachelor|\bb\.\s?s\.?(?!\w)|\bb\.?\s?sc\b|\bb\.?\s?tech\b"
        r"|\bb\.\s?e\.?(?!\w)"),
    (2, r"\bassociate'?s?\s+(?:degree|of|in)\b|\bdiploma\b"),
    (1, r"\bhigh school\b"),
]
_DEGREE_RES = [(level, re.compile(pattern)) for level, pattern in DEGREE_PATTERNS]

_YEARS_PHRASE = re.compile(
    r"(\d{1,2})(?:\s*\+)?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp)",
    re.IGNORECASE,
)

_MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
_MONTH = r"(?:(" + "|".join(_MONTHS) + r")[a-z]*\.?\s*)?"
_DATE_RANGE = re.compile(
    _MONTH + r"(\d{4})\s*(?:-|–|—|to)\s*" + _MONTH + r"(present|current|now|\d{4})",
    re.IGNORECASE,
)


def _month_index(year: int, month: str) -> int:
    """Months since year 0; a missing month counts as January."""
    return year * 12 + (_MONTHS.index(month.lower()[:3]) if month else 0)


def _merged_months(spans: list[tuple[int, int]]) -> int:
    """Total months covered, counting overlapping roles only once."""
    total = 0
    cur_start = cur_end = None
    for start, end in sorted(spans):
        if cur_end is None or start > cur_end:
            if cur_end is not None:
                total += cur_end - cur_start
            cur_start, cur_end = start, end
        else:
            cur_end = max(cur_end, end)
    if cur_end is not None:
        total += cur_end - cur_start
    return total


def estimate_years_experience(text: str, dated_text: str | None = None) -> float:
    """Best-effort total years of professional experience from resume text.

    An explicit "N years of experience" phrase anywhere in ``text`` wins.
    Otherwise date ranges are read from ``dated_text`` (the experience
    section, when the caller has one) so education dates aren't counted.
    """
    explicit = [int(m) for m in _YEARS_PHRASE.findall(text)]
    if explicit:
        return float(max(explicit))

    today = date.today()
    now = today.year * 12 + today.month - 1
    spans = []
    for start_month, start, end_month, end in _DATE_RANGE.findall(dated_text or text):
        start_year = int(start)
        if end.isdigit():
            end_idx = _month_index(int(end), end_month)
        else:
            end_idx = now
        start_idx = _month_index(start_year, start_month)
        if 1970 <= start_year <= today.year and start_idx <= end_idx <= now:
            spans.append((start_idx, end_idx))
    if spans:
        return round(min(_merged_months(spans) / 12, 40.0), 1)
    return 0.0


def detect_education_level(text: str) -> int:
    """0 = none detected, 1 = high school … 5 = PhD."""
    lowered = text.lower()
    for level, pattern in _DEGREE_RES:
        if pattern.search(lowered):
            return level
    return 0


def required_years_from_job(job_text: str) -> float:
    matches = [int(m) for m in _YEARS_PHRASE.findall(job_text)]
    return float(min(matches)) if matches else 0.0


def required_education_from_job(job_text: str) -> int:
    return detect_education_level(job_text)
