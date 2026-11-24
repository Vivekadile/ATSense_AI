"""Skill taxonomy: canonical skills, their aliases, and category groupings.

This is the deterministic backbone of extraction and matching. The LLM
layer can add skills on top, but everything is normalized back through
``normalize_skill`` so resume and job-description skills stay comparable.
"""
import re

# canonical name -> list of aliases (all lowercase, matched as whole tokens)
SKILL_ALIASES = {
    # --- languages ---
    "python": ["python", "py"],
    "javascript": ["javascript", "js", "ecmascript"],
    "typescript": ["typescript", "ts"],
    "java": ["java"],
    "c": ["c language", "c programming"],
    "c++": ["c++", "cpp"],
    "c#": ["c#", "c sharp", "csharp", ".net"],
    "go": ["golang", "go lang"],
    "rust": ["rust"],
    "ruby": ["ruby"],
    "php": ["php"],
    "swift": ["swift"],
    "kotlin": ["kotlin"],
    "scala": ["scala"],
    "r": ["r language", "r programming"],
    "matlab": ["matlab"],
    "bash": ["bash", "shell scripting", "shell script"],
    "sql": ["sql"],

    # --- web / frontend ---
    "react": ["react", "react.js", "reactjs"],
    "next.js": ["next.js", "nextjs"],
    "vue": ["vue", "vue.js", "vuejs"],
    "angular": ["angular", "angular.js", "angularjs"],
    "svelte": ["svelte", "sveltekit"],
    "html": ["html", "html5"],
    "css": ["css", "css3"],
    "tailwind": ["tailwind", "tailwindcss", "tailwind css"],
    "sass": ["sass", "scss"],
    "redux": ["redux"],
    "jquery": ["jquery"],
    "webpack": ["webpack"],
    "vite": ["vite"],

    # --- backend / api ---
    "node.js": ["node.js", "nodejs", "node"],
    "express": ["express", "express.js", "expressjs"],
    "fastapi": ["fastapi"],
    "flask": ["flask"],
    "django": ["django"],
    "spring": ["spring", "spring boot", "springboot"],
    "rails": ["rails", "ruby on rails"],
    "graphql": ["graphql"],
    "rest": ["rest", "rest api", "restful", "restful api"],
    "grpc": ["grpc"],
    "microservices": ["microservices", "microservice"],

    # --- data / ml / ai ---
    "machine learning": ["machine learning", "ml"],
    "deep learning": ["deep learning", "dl"],
    "natural language processing": ["natural language processing", "nlp"],
    "computer vision": ["computer vision", "cv", "opencv"],
    "data science": ["data science", "data scientist"],
    "data analysis": ["data analysis", "data analytics", "data analyst"],
    "data engineering": ["data engineering", "data engineer"],
    "tensorflow": ["tensorflow", "tf", "keras"],
    "pytorch": ["pytorch", "torch"],
    "scikit-learn": ["scikit-learn", "sklearn", "scikit learn"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "matplotlib": ["matplotlib", "seaborn"],
    "spark": ["spark", "pyspark", "apache spark"],
    "hadoop": ["hadoop"],
    "airflow": ["airflow", "apache airflow"],
    "kafka": ["kafka", "apache kafka"],
    "dbt": ["dbt"],
    "tableau": ["tableau"],
    "power bi": ["power bi", "powerbi"],
    "excel": ["excel", "microsoft excel", "ms excel"],
    "llm": ["llm", "large language model", "large language models", "genai", "generative ai"],
    "langchain": ["langchain"],
    "hugging face": ["hugging face", "huggingface", "transformers library"],

    # --- databases ---
    "postgresql": ["postgresql", "postgres", "psql"],
    "mysql": ["mysql"],
    "mongodb": ["mongodb", "mongo"],
    "redis": ["redis"],
    "elasticsearch": ["elasticsearch", "elastic search"],
    "sqlite": ["sqlite"],
    "dynamodb": ["dynamodb"],
    "snowflake": ["snowflake"],
    "bigquery": ["bigquery", "big query"],
    "cassandra": ["cassandra"],

    # --- cloud / devops ---
    "aws": ["aws", "amazon web services"],
    "azure": ["azure", "microsoft azure"],
    "gcp": ["gcp", "google cloud", "google cloud platform"],
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s"],
    "terraform": ["terraform"],
    "ansible": ["ansible"],
    "jenkins": ["jenkins"],
    "ci/cd": ["ci/cd", "ci cd", "cicd", "continuous integration", "continuous delivery"],
    "github actions": ["github actions"],
    "gitlab ci": ["gitlab ci", "gitlab-ci"],
    "linux": ["linux", "unix"],
    "nginx": ["nginx"],
    "prometheus": ["prometheus"],
    "grafana": ["grafana"],

    # --- tools / practices ---
    "git": ["git"],
    "github": ["github"],
    "gitlab": ["gitlab"],
    "bitbucket": ["bitbucket"],
    "jira": ["jira"],
    "agile": ["agile", "scrum", "kanban"],
    "unit testing": ["unit testing", "unit test", "unit tests"],
    "pytest": ["pytest"],
    "jest": ["jest"],
    "selenium": ["selenium"],
    "cypress": ["cypress"],
    "figma": ["figma"],
    "postman": ["postman"],

    # --- soft / domain ---
    "communication": ["communication", "communication skills"],
    "leadership": ["leadership", "team lead", "tech lead"],
    "project management": ["project management", "project manager"],
    "problem solving": ["problem solving", "problem-solving"],
}

# category -> canonical skills it contains (used for "partial" family matches)
SKILL_CATEGORIES = {
    "backend languages": {"python", "java", "go", "ruby", "php", "c#", "scala", "rust", "node.js"},
    "frontend frameworks": {"react", "next.js", "vue", "angular", "svelte"},
    "backend frameworks": {"fastapi", "flask", "django", "express", "spring", "rails"},
    "ml frameworks": {"tensorflow", "pytorch", "scikit-learn"},
    "ml fields": {"machine learning", "deep learning", "natural language processing", "computer vision"},
    "cloud providers": {"aws", "azure", "gcp"},
    "relational databases": {"postgresql", "mysql", "sqlite", "sql"},
    "nosql databases": {"mongodb", "redis", "dynamodb", "cassandra", "elasticsearch"},
    "data processing": {"spark", "hadoop", "kafka", "airflow", "dbt"},
    "bi tools": {"tableau", "power bi", "excel"},
    "iac tools": {"terraform", "ansible"},
    "ci tools": {"jenkins", "github actions", "gitlab ci", "ci/cd"},
    "vcs hosting": {"github", "gitlab", "bitbucket"},
}

# reverse lookup: alias -> canonical
ALIAS_TO_CANONICAL = {
    alias: canonical
    for canonical, aliases in SKILL_ALIASES.items()
    for alias in aliases
}

# canonical -> set of canonical skills in the same category
_FAMILY = {}
for _members in SKILL_CATEGORIES.values():
    for _skill in _members:
        _FAMILY.setdefault(_skill, set()).update(_members - {_skill})


def canonical_skills() -> list[str]:
    return sorted(SKILL_ALIASES)


def normalize_skill(raw: str) -> str:
    """Map an arbitrary skill string onto a canonical name when possible."""
    cleaned = raw.strip().lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if cleaned in ALIAS_TO_CANONICAL:
        return ALIAS_TO_CANONICAL[cleaned]
    if cleaned in SKILL_ALIASES:
        return cleaned
    # tolerate trailing punctuation / plurals like "apis"
    stripped = cleaned.rstrip(".,;:").removesuffix("s")
    return ALIAS_TO_CANONICAL.get(stripped, cleaned)


def normalize_skills(raw_skills) -> list[str]:
    seen = {}
    for raw in raw_skills or []:
        if not isinstance(raw, str) or not raw.strip():
            continue
        norm = normalize_skill(raw)
        seen.setdefault(norm, norm)
    return sorted(seen)


def related_skills(skill: str) -> set[str]:
    """Canonical skills that belong to the same family as ``skill``."""
    return set(_FAMILY.get(normalize_skill(skill), set()))


def extract_skills_from_text(text: str) -> list[str]:
    """Deterministic dictionary scan for known skills in free text."""
    lowered = text.lower()
    found = []
    for canonical, aliases in SKILL_ALIASES.items():
        for alias in aliases:
            pattern = rf"(?<!\w){re.escape(alias)}(?!\w)"
            if re.search(pattern, lowered):
                found.append(canonical)
                break
    return sorted(set(found))
