# ATSense AI

AI-powered Resume & Job Compatibility Analyzer.

## Pipeline

```
Resume (PDF/DOCX/TXT)
→ text extraction (backend/parser.py)
→ structured resume extraction (backend/extractor.py)         ── dictionary + optional LLM
→ job-description analysis (backend/jd_analyzer.py)            ── required vs. preferred, clause-aware
→ skill + keyword matching (backend/matcher.py)
→ embedding-based semantic similarity (backend/embeddings.py)
→ deterministic ATS scoring (backend/scorer.py)
→ resume quality evaluation (backend/quality.py)
→ recommendations (backend/recommender.py)
→ Groq/Qwen qualitative AI analysis (backend/llm.py)
```

With the default settings the numerical ATS score is computed
deterministically: the same resume and JD always give the same score. The
LLM adds a qualitative summary/strengths/gaps/recommendations layer on top.
Setting `LLM_EXTRACTION_ENABLED=true` additionally lets the LLM contribute
skills/years/education to the parsed profile; that output then feeds the
score, so scores can vary between runs. The deterministic parser is always
the floor and the fallback.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional: add GROQ_API_KEY for the AI layer
uvicorn backend.main:app --reload
```

Open http://127.0.0.1:8000/ — it redirects to the web UI at `/app/`.
The frontend (`frontend-web/`) is static HTML/JS/Tailwind with no build
step; FastAPI serves it via `StaticFiles`.

## Configuration (`.env`, see `.env.example`)

| Variable | Default | Purpose |
| --- | --- | --- |
| `GROQ_API_KEY` | — | Enables the AI analysis layer and LLM extraction. Without it the pipeline still runs fully. |
| `GROQ_MODEL` | `qwen/qwen3.8-27b` | Groq model id (see console.groq.com for options). `GET /api/health/groq` reports whether it is available. |
| `GROQ_TIMEOUT` | `30` | Per-request timeout (seconds). |
| `LLM_EXTRACTION_ENABLED` | `false` | Use the LLM to help extract skills/years/education. Makes the score non-deterministic; deterministic fallback always applies. |
| `MAX_UPLOAD_BYTES` | `5242880` | Resume upload size limit. |
| `MAX_JD_CHARS` | `50000` | Job-description length limit. |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins. |

Never commit `.env` — only `.env.example` with placeholders. `*.db` is
also gitignored.

## API

| Endpoint | Purpose |
| --- | --- |
| `POST /api/resume/parse` | Parse a resume into a structured profile (skills, years, education level, sections). |
| `POST /api/job/analyze` | Analyze a job description into required / preferred skills + required years/education. |
| `POST /api/ats/score` | Full pipeline (score, quality, recommendations, AI analysis); persisted to history. |
| `POST /api/skills/gap` | Matched / partial / missing / preferred skills + coverage score. |
| `POST /api/recommendations` | Recommendations, job-category suggestions, AI analysis. |
| `GET /api/history` | List stored analyses. |
| `GET /api/history/{id}` | Retrieve one stored analysis. |
| `GET /api/health` | Health check (also reports whether LLM extraction is active). |
| `GET /api/health/groq` | Test Groq connectivity. |

Resume endpoints use `multipart/form-data` with a `resume` file field
(PDF/DOCX/TXT); job-description endpoints use a `job_description` form field.

## Scoring

Deterministic weighted sum (`backend/scorer.py`, `WEIGHTS`):

| Factor | Weight | Source |
| --- | --- | --- |
| Skills coverage | 30% | Share of required *skills* matched (canonical sets, half credit for same-family partials). |
| Experience | 20% | Candidate years vs. years the JD asks for (presence-based when the JD is silent). |
| Education | 10% | Candidate degree level vs. JD requirement. |
| Keyword match | 20% | Share of the JD's important *terms* present verbatim in the resume text. |
| Semantic similarity | 20% | `all-MiniLM-L6-v2` cosine, resume vs. JD. Text is embedded in ~150-word windows and averaged, so the whole resume counts (the model alone truncates at 256 tokens). |

Skills coverage and keyword match are computed from different inputs so
they are independent signals (the earlier version double-counted them).

## Tests

```bash
pytest                              # unit + API tests (backend/*)
python -m tests.evaluate            # scoring evaluation over labeled cases
python -m tests.evaluate --fast     # same, with the embedding model stubbed
python -m tests.evaluate --show-fails
```

`tests/test_cases.json` holds diverse labeled cases (band, score range,
must-match / must-miss skills). `tests/evaluate.py` runs the deterministic
pipeline over them and reports band accuracy, score MAE, and skill recall;
it exits non-zero if band accuracy drops below 70% so CI can gate on it.
