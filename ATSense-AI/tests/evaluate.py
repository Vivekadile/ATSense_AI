"""Offline evaluation of the deterministic ATS pipeline.

Runs every labeled case in ``tests/test_cases.json`` through the real
pipeline (LLM disabled) and reports:

  * score-band accuracy (predicted band vs. expected band)
  * mean absolute error between predicted score and the expected range
  * skill precision/recall against ``must_match`` / ``must_miss`` labels

Usage:
    python -m tests.evaluate                # full run (loads embedding model)
    python -m tests.evaluate --fast         # stub embeddings for a quick pass
    python -m tests.evaluate --show-fails   # print every failing case
"""
import argparse
import json
import os
import sys
from pathlib import Path

os.environ["LLM_EXTRACTION_ENABLED"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CASES_PATH = Path(__file__).resolve().parent / "test_cases.json"

BANDS = {"low": (0, 49), "medium": (50, 74), "high": (75, 100)}


def band_of(score: float) -> str:
    for name, (lo, hi) in BANDS.items():
        if lo <= score <= hi:
            return name
    return "high" if score > 100 else "low"


def _maybe_stub_embeddings(fast: bool) -> None:
    if not fast:
        return
    import backend.matcher as matcher

    def _fake(resume_text: str, job_description: str) -> float:
        a, b = set(resume_text.lower().split()), set(job_description.lower().split())
        return round(len(a & b) / len(a | b) * 100, 2) if a and b else 0.0

    matcher.calculate_semantic_similarity = _fake


def run_case(case: dict) -> dict:
    from backend.extractor import extract_resume_information
    from backend.jd_analyzer import analyze_job_description
    from backend.matcher import match_resume_with_job
    from backend.scorer import calculate_ats_score

    resume_text = case["resume"]
    jd_text = case["job_description"]

    resume_data = extract_resume_information(resume_text, use_llm=False)
    job_data = analyze_job_description(jd_text, use_llm=False)
    matching = match_resume_with_job(resume_data, job_data, resume_text, jd_text)
    scores = calculate_ats_score(matching, resume_data, job_data)

    exp = case.get("expected", {})
    score = scores["overall_score"]
    pred_band = band_of(score)
    exp_band = exp.get("band")

    lo = exp.get("min_score", BANDS.get(exp_band, (0, 100))[0])
    hi = exp.get("max_score", BANDS.get(exp_band, (0, 100))[1])
    range_err = 0.0 if lo <= score <= hi else min(abs(score - lo), abs(score - hi))

    matched = set(matching["matched_skills"]) | set(matching["partially_matched_skills"])
    missing = set(matching["missing_skills"])
    must_match = set(exp.get("must_match_skills", []))
    must_miss = set(exp.get("must_miss_skills", []))

    match_hits = must_match & matched
    miss_hits = must_miss & missing

    return {
        "id": case.get("id"),
        "title": case.get("title", ""),
        "score": score,
        "pred_band": pred_band,
        "exp_band": exp_band,
        "band_ok": exp_band is None or pred_band == exp_band,
        "range_err": round(range_err, 2),
        "match_recall": (len(match_hits) / len(must_match)) if must_match else None,
        "miss_recall": (len(miss_hits) / len(must_miss)) if must_miss else None,
        "missing_expected_matches": sorted(must_match - matched),
        "missing_expected_misses": sorted(must_miss - missing),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true", help="stub the embedding model")
    ap.add_argument("--show-fails", action="store_true", help="print failing cases")
    args = ap.parse_args()

    _maybe_stub_embeddings(args.fast)
    cases = json.loads(CASES_PATH.read_text())
    results = [run_case(c) for c in cases]

    n = len(results)
    band_acc = sum(r["band_ok"] for r in results) / n
    mae = sum(r["range_err"] for r in results) / n
    mr = [r["match_recall"] for r in results if r["match_recall"] is not None]
    xr = [r["miss_recall"] for r in results if r["miss_recall"] is not None]

    print(f"cases evaluated      : {n}")
    print(f"band accuracy        : {band_acc:.0%}")
    print(f"score range MAE       : {mae:.2f}")
    if mr:
        print(f"must-match recall    : {sum(mr) / len(mr):.0%}")
    if xr:
        print(f"must-miss recall     : {sum(xr) / len(xr):.0%}")

    fails = [r for r in results if not r["band_ok"] or r["range_err"] > 0
             or (r["match_recall"] not in (None, 1.0))
             or (r["miss_recall"] not in (None, 1.0))]
    print(f"cases with issues    : {len(fails)}")

    if args.show_fails:
        for r in fails:
            print(f"\n[{r['id']}] {r['title']}")
            print(f"  score={r['score']} pred={r['pred_band']} exp={r['exp_band']} "
                  f"range_err={r['range_err']}")
            if r["missing_expected_matches"]:
                print(f"  expected-but-not-matched: {r['missing_expected_matches']}")
            if r["missing_expected_misses"]:
                print(f"  expected-but-not-missing: {r['missing_expected_misses']}")

    # non-zero exit if the pipeline regressed badly, so CI can gate on it
    return 0 if band_acc >= 0.7 else 1


if __name__ == "__main__":
    raise SystemExit(main())
