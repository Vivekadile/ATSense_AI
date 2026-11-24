from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from starlette.concurrency import run_in_threadpool

from backend import config
from backend.parser import extract_resume_text
from backend.extractor import extract_resume_information
from backend.jd_analyzer import analyze_job_description
from backend.matcher import match_resume_with_job
from backend.scorer import calculate_ats_score
from backend.quality import analyze_resume_quality
from backend.recommender import generate_recommendations, suggest_job_categories
from backend.database import save_analysis, get_history, get_analysis
from backend.llm import get_ai_analysis, test_groq_connection, GroqNotConfiguredError

router = APIRouter(prefix="/api", tags=["ATS Analysis"])


async def _read_resume_text(resume: UploadFile) -> str:
    if not resume.filename:
        raise HTTPException(status_code=400, detail="Resume file is required.")
    try:
        return await extract_resume_text(resume)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


def _validate_jd(job_description: str) -> str:
    text = (job_description or "").strip()
    if len(text) < 30:
        raise HTTPException(
            status_code=400,
            detail="Job description is too short — paste the full posting.",
        )
    if len(text) > config.MAX_JD_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"Job description exceeds {config.MAX_JD_CHARS} characters.",
        )
    return text


def _run_ai_analysis(resume_data: dict, job_data: dict, ats_report: dict) -> dict:
    try:
        return get_ai_analysis(resume_data, job_data, ats_report)
    except GroqNotConfiguredError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        return {"error": f"AI analysis unavailable: {exc}"}


def _run_pipeline(resume_text: str, job_description: str) -> dict:
    resume_data = extract_resume_information(resume_text)
    job_data = analyze_job_description(job_description)
    matching = match_resume_with_job(resume_data, job_data, resume_text, job_description)
    scores = calculate_ats_score(matching, resume_data, job_data)
    quality = analyze_resume_quality(resume_text, resume_data)

    resume_data["_quality_issues"] = quality.get("issues", [])
    recommendations = generate_recommendations(matching, resume_data, job_data)
    resume_data.pop("_quality_issues", None)

    ats_report = {
        "overall_ats_score": scores["overall_score"],
        "scores": scores,
        "matched_skills": matching["matched_skills"],
        "partially_matched_skills": matching["partially_matched_skills"],
        "missing_skills": matching["missing_skills"],
        "preferred_matched_skills": matching["preferred_matched_skills"],
        "matched_keywords": matching["matched_keywords"],
        "missing_keywords": matching["missing_keywords"],
    }

    return {
        "ats_report": ats_report,
        "resume_data": resume_data,
        "job_data": {k: v for k, v in job_data.items() if k != "raw_text"},
        "quality": quality,
        "matching": matching,
        "recommendations": recommendations,
        "job_category_suggestions": suggest_job_categories(resume_data.get("skills", [])),
    }


@router.post("/resume/parse")
async def parse_resume(resume: UploadFile = File(...)):
    resume_text = await _read_resume_text(resume)
    try:
        return await run_in_threadpool(extract_resume_information, resume_text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Resume parsing failed: {exc}")


@router.post("/job/analyze")
async def analyze_job(job_description: str = Form(...)):
    job_description = _validate_jd(job_description)
    try:
        job_data = await run_in_threadpool(analyze_job_description, job_description)
        return {k: v for k, v in job_data.items() if k != "raw_text"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Job analysis failed: {exc}")


@router.post("/ats/score")
async def score_ats(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
):
    resume_text = await _read_resume_text(resume)
    job_description = _validate_jd(job_description)

    try:
        pipeline = await run_in_threadpool(_run_pipeline, resume_text, job_description)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ATS scoring failed: {exc}")

    pipeline["ai_analysis"] = await run_in_threadpool(
        _run_ai_analysis,
        pipeline["resume_data"], pipeline["job_data"], pipeline["ats_report"],
    )
    result = {k: v for k, v in pipeline.items() if k != "matching"}
    result["analysis_id"] = await run_in_threadpool(
        save_analysis, resume.filename, pipeline["ats_report"]["overall_ats_score"], result
    )
    return result


@router.post("/skills/gap")
async def skills_gap(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
):
    resume_text = await _read_resume_text(resume)
    job_description = _validate_jd(job_description)

    try:
        pipeline = await run_in_threadpool(_run_pipeline, resume_text, job_description)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Skill gap analysis failed: {exc}")

    m = pipeline["matching"]
    return {
        "matched_skills": m["matched_skills"],
        "partially_matched_skills": m["partially_matched_skills"],
        "missing_skills": m["missing_skills"],
        "preferred_matched_skills": m["preferred_matched_skills"],
        "skills_coverage_score": m["skills_coverage_score"],
    }


@router.post("/recommendations")
async def recommendations(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
):
    resume_text = await _read_resume_text(resume)
    job_description = _validate_jd(job_description)

    try:
        pipeline = await run_in_threadpool(_run_pipeline, resume_text, job_description)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Recommendation generation failed: {exc}")

    return {
        "recommendations": pipeline["recommendations"],
        "job_category_suggestions": pipeline["job_category_suggestions"],
        "ai_analysis": await run_in_threadpool(
            _run_ai_analysis,
            pipeline["resume_data"], pipeline["job_data"], pipeline["ats_report"],
        ),
    }


@router.get("/history")
def history():
    return get_history()


@router.get("/history/{analysis_id}")
def history_item(analysis_id: int):
    record = get_analysis(analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return record


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "llm_extraction": config.LLM_EXTRACTION_ENABLED and config.groq_configured(),
    }


@router.get("/health/groq")
def health_groq():
    return test_groq_connection()
