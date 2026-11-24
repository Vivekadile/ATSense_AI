// ---------- Theme ----------
const root = document.documentElement;
const darkQuery = window.matchMedia("(prefers-color-scheme: dark)");

function currentTheme() {
  return root.dataset.theme || (darkQuery.matches ? "dark" : "light");
}

document.getElementById("theme-toggle").addEventListener("click", () => {
  const next = currentTheme() === "dark" ? "light" : "dark";
  root.dataset.theme = next;
  try {
    localStorage.setItem("atsense-theme", next);
  } catch {}
});

// ---------- Icons ----------
const ICONS = {
  check: '<svg viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>',
  alert: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" /><path d="M12 8v4.5M12 16h.01" /></svg>',
  arrow: '<svg viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6" /></svg>',
  print: '<svg viewBox="0 0 24 24"><path d="M7 9V3h10v6" /><rect x="3" y="9" width="18" height="8" rx="2" /><path d="M7 14h10v7H7z" /></svg>',
  plus: '<svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" /></svg>',
};

// ---------- Form ----------
const dropzone = document.getElementById("dropzone");
const resumeInput = document.getElementById("resume-input");
const dzEmpty = document.getElementById("dropzone-empty");
const dzFilled = document.getElementById("dropzone-filled");
const filenameLabel = document.getElementById("filename-label");
const filesizeLabel = document.getElementById("filesize-label");
const jdInput = document.getElementById("jd-input");
const analyzeBtn = document.getElementById("analyze-btn");
const formError = document.getElementById("form-error");
const resumeError = document.getElementById("resume-error");
const jdError = document.getElementById("jd-error");
const jdCount = document.getElementById("jd-count");
const loadingCard = document.getElementById("loading-card");
const loadingSteps = document.querySelectorAll("#loading-steps li");
const resultsSection = document.getElementById("results");

const MAX_RESUME_BYTES = 5 * 1024 * 1024; // keep in sync with backend MAX_UPLOAD_BYTES
const ALLOWED_EXTENSIONS = ["pdf", "docx", "txt"];
const MIN_JD_CHARS = 30;

const SAMPLE_JD = `Backend Software Engineer

We are looking for a Backend Engineer to design and build scalable APIs for our hiring platform.

Requirements:
- 2+ years of experience building backend services in Python
- Hands-on experience with FastAPI or Django
- Strong knowledge of SQL and PostgreSQL
- Experience with Docker and REST API design
- Familiarity with Git and CI/CD workflows

Preferred:
- Experience with AWS or another cloud platform
- Exposure to Kubernetes and Redis is a plus
- Bachelor's degree in Computer Science or a related field`;

let resumeFile = null;

function showFieldError(el, message) {
  el.textContent = message || "";
  el.classList.toggle("hidden", !message);
}

function formatSize(bytes) {
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function validateResumeFile(file) {
  const ext = file.name.includes(".") ? file.name.split(".").pop().toLowerCase() : "";
  if (!ALLOWED_EXTENSIONS.includes(ext)) return "Unsupported file type. Please upload a PDF, DOCX or TXT file.";
  if (file.size > MAX_RESUME_BYTES) return `File is too large (${formatSize(file.size)}). The limit is 5 MB.`;
  if (file.size === 0) return "This file is empty.";
  return null;
}

function setResumeFile(file) {
  const problem = file ? validateResumeFile(file) : null;
  resumeFile = problem ? null : file;
  showFieldError(resumeError, problem);

  const hasFile = Boolean(resumeFile);
  dzEmpty.classList.toggle("hidden", hasFile);
  dzFilled.classList.toggle("hidden", !hasFile);
  dropzone.classList.toggle("has-file", hasFile);
  if (hasFile) {
    filenameLabel.textContent = resumeFile.name;
    filesizeLabel.textContent = formatSize(resumeFile.size);
  }
  updateSubmitState();
}

function updateSubmitState() {
  const len = jdInput.value.trim().length;
  jdCount.textContent = `${jdInput.value.length.toLocaleString()} character${jdInput.value.length === 1 ? "" : "s"}`;
  showFieldError(jdError, len > 0 && len < MIN_JD_CHARS ? `Please paste the full posting (at least ${MIN_JD_CHARS} characters).` : null);
  analyzeBtn.disabled = !(resumeFile && len >= MIN_JD_CHARS);
}

dropzone.addEventListener("click", () => resumeInput.click());
dropzone.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    resumeInput.click();
  }
});
resumeInput.addEventListener("change", (e) => {
  if (e.target.files[0]) setResumeFile(e.target.files[0]);
  resumeInput.value = "";
});

["dragenter", "dragover"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add("drag-over");
  })
);
["dragleave", "drop"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove("drag-over");
  })
);
dropzone.addEventListener("drop", (e) => {
  if (e.dataTransfer.files[0]) setResumeFile(e.dataTransfer.files[0]);
});

jdInput.addEventListener("input", updateSubmitState);
document.getElementById("sample-jd").addEventListener("click", () => {
  jdInput.value = SAMPLE_JD;
  updateSubmitState();
  jdInput.focus();
});

// ---------- Loading progress ----------
let loadingTimer = null;

function startLoading() {
  let step = 0;
  const paint = () =>
    loadingSteps.forEach((li, i) => {
      li.classList.toggle("done", i < step);
      li.classList.toggle("active", i === step);
    });
  paint();
  loadingTimer = setInterval(() => {
    if (step < loadingSteps.length - 1) {
      step += 1;
      paint();
    }
  }, 1100);
}

function stopLoading() {
  clearInterval(loadingTimer);
}

analyzeBtn.addEventListener("click", async () => {
  formError.classList.add("hidden");
  resultsSection.classList.add("hidden");
  resultsSection.innerHTML = "";
  loadingCard.classList.remove("hidden");
  analyzeBtn.disabled = true;
  analyzeBtn.textContent = "Analyzing…";
  startLoading();

  const formData = new FormData();
  formData.append("resume", resumeFile);
  formData.append("job_description", jdInput.value.trim());

  try {
    const res = await fetch("/api/ats/score", { method: "POST", body: formData });
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new Error(errBody.detail || `Request failed (${res.status}).`);
    }
    renderResults(await res.json());
    refreshHistoryQuietly();
  } catch (err) {
    formError.textContent = err.message || "Something went wrong. Please try again.";
    formError.classList.remove("hidden");
  } finally {
    stopLoading();
    loadingCard.classList.add("hidden");
    analyzeBtn.textContent = "Analyze resume";
    updateSubmitState();
  }
});

// ---------- Helpers ----------
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

// bands match tests/evaluate.py: high >= 75, medium 50-74, low < 50
function scoreBand(score) {
  if (score >= 75) return { tone: "good", label: "Strong match", color: "var(--good)" };
  if (score >= 50) return { tone: "warn", label: "Moderate match", color: "var(--warn)" };
  return { tone: "bad", label: "Weak match", color: "var(--bad)" };
}

function formatDate(value) {
  const d = new Date(String(value).replace(" ", "T") + "Z");
  return isNaN(d) ? value : d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function animateNumber(el, target, duration = 900) {
  const start = performance.now();
  function tick(now) {
    const p = Math.min(1, (now - start) / duration);
    el.textContent = Math.round(target * (1 - Math.pow(1 - p, 3)));
    if (p < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

function chips(list, cls, emptyLabel) {
  if (!list || !list.length) return `<p class="empty">${emptyLabel}</p>`;
  return `<div class="chips">${list.map((s) => `<span class="chip ${cls}">${escapeHtml(s)}</span>`).join("")}</div>`;
}

function iconList(items, cls, icon) {
  if (!items || !items.length) return '<p class="empty">—</p>';
  return `<ul class="list ${cls}">${items.map((s) => `<li>${ICONS[icon]}<span>${escapeHtml(s)}</span></li>`).join("")}</ul>`;
}

const EDU_LABELS = ["Not detected", "High school", "Associate / Diploma", "Bachelor's", "Master's", "PhD"];
const eduLabel = (level) => EDU_LABELS[level] || EDU_LABELS[0];

function fact(label, value) {
  return `<div><p class="fact-label">${label}</p><p class="fact-value">${escapeHtml(String(value))}</p></div>`;
}

const FACTORS = [
  ["skills", "skills_match_score", "Skills coverage", "Required skills found in the resume"],
  ["experience", "experience_match_score", "Experience", "Years of experience vs. requirement"],
  ["education", "education_match_score", "Education", "Degree level vs. requirement"],
  ["keyword", "keyword_match_score", "Keyword match", "Important JD terms present in the resume"],
  ["semantic", "semantic_similarity_score", "Semantic similarity", "Overall meaning, via sentence embeddings"],
];

function breakdownTable(scores) {
  const weights = scores.weights || {};
  const rows = FACTORS.map(([key, field, name, desc]) => {
    const value = Number(scores[field] || 0);
    const weight = Number(weights[key] || 0);
    return `
      <tr>
        <td><div class="factor-name">${name}</div><div class="factor-desc">${desc}</div></td>
        <td class="num">${Math.round(weight * 100)}%</td>
        <td class="bar-cell"><div class="bar"><div class="bar-fill" data-target="${value}"></div></div></td>
        <td class="num">${value.toFixed(1)}</td>
        <td class="num">${(value * weight).toFixed(1)}</td>
      </tr>`;
  }).join("");
  return `
    <table class="breakdown">
      <thead><tr><th>Factor</th><th class="num">Weight</th><th class="col-bar"></th><th class="num">Score</th><th class="num">Points</th></tr></thead>
      <tbody>${rows}</tbody>
      <tfoot><tr><td>Overall ATS score</td><td class="num">100%</td><td class="bar-cell"></td><td></td><td class="num">${Number(scores.overall_score).toFixed(1)}</td></tr></tfoot>
    </table>`;
}

// ---------- Results ----------
function renderResults(data) {
  const ats = data.ats_report;
  const scores = ats.scores || {};
  const quality = data.quality || {};
  const ai = data.ai_analysis || {};
  const resume = data.resume_data || {};
  const job = data.job_data || {};
  const score = Number(ats.overall_ats_score) || 0;
  const band = scoreBand(score);
  const circumference = 2 * Math.PI * 58;

  const required = (job.required_skills || []).length;
  const matched = (ats.matched_skills || []).length;
  const partial = (ats.partially_matched_skills || []).length;
  const kwHit = (ats.matched_keywords || []).length;
  const kwTotal = kwHit + (ats.missing_keywords || []).length;

  resultsSection.innerHTML = `
    <div class="results-head fade-up">
      <div>
        <h2>Analysis report</h2>
        <p class="muted small">${data.analysis_id ? `Report #${data.analysis_id} · saved to history` : "Report"}</p>
      </div>
      <div class="results-actions">
        <button id="print-btn" class="btn" type="button">${ICONS.print}Print / save PDF</button>
        <button id="new-btn" class="btn" type="button">${ICONS.plus}New analysis</button>
      </div>
    </div>

    <div class="card fade-up">
      <div class="summary">
        <div class="score-block">
          <div class="ring">
            <svg viewBox="0 0 140 140">
              <circle class="track" cx="70" cy="70" r="58" />
              <circle id="score-circle" class="value" cx="70" cy="70" r="58" stroke="${band.color}"
                stroke-dasharray="${circumference}" stroke-dashoffset="${circumference}" />
            </svg>
            <div class="ring-label"><span id="score-number" class="ring-number">0</span><span class="ring-sub">out of 100</span></div>
          </div>
          <div>
            <span class="verdict tone-${band.tone}">${band.label}</span>
            <p class="score-title">ATS compatibility score</p>
            <p class="muted small">Weighted from five independent signals</p>
          </div>
        </div>
        <div class="stats">
          <div class="stat"><p class="stat-label">Required skills</p><p class="stat-value">${matched}/${required}</p><p class="stat-note">${partial ? `+${partial} partial` : "matched"}</p></div>
          <div class="stat"><p class="stat-label">Experience</p><p class="stat-value">${resume.years_experience ? `${resume.years_experience} yrs` : "—"}</p><p class="stat-note">${job.required_years_experience ? `${job.required_years_experience}+ yrs asked` : "not specified in JD"}</p></div>
          <div class="stat"><p class="stat-label">Education</p><p class="stat-value">${resume.education_level ? eduLabel(resume.education_level) : "—"}</p><p class="stat-note">${job.required_education_level ? `${eduLabel(job.required_education_level)} asked` : "not specified in JD"}</p></div>
          <div class="stat"><p class="stat-label">Keywords</p><p class="stat-value">${kwHit}/${kwTotal}</p><p class="stat-note">JD terms found</p></div>
        </div>
      </div>
    </div>

    <div class="card fade-up">
      <div class="title-row"><h3>Score breakdown</h3><span class="badge">Deterministic</span></div>
      ${breakdownTable(scores)}
      <p class="note">Points = score × weight. The AI review below never changes this score.</p>
    </div>

    <div class="card fade-up">
      <h3>Skill gap analysis</h3>
      <p class="section-label"><span class="legend-dot" style="background:var(--good)"></span>Matched</p>
      ${chips(ats.matched_skills, "chip-matched", "No required skills matched.")}
      <p class="section-label"><span class="legend-dot" style="background:var(--warn)"></span>Partial — related skill found</p>
      ${chips(ats.partially_matched_skills, "chip-partial", "None.")}
      <p class="section-label"><span class="legend-dot" style="background:var(--bad)"></span>Missing</p>
      ${chips(ats.missing_skills, "chip-missing", "None — all required skills are covered.")}
      <p class="section-label"><span class="legend-dot" style="background:var(--info)"></span>Preferred skills matched</p>
      ${chips(ats.preferred_matched_skills, "chip-preferred", "None.")}
      ${
        (ats.missing_keywords || []).length
          ? `<p class="section-label">Job keywords missing from the resume</p>${chips(ats.missing_keywords.slice(0, 20), "", "")}`
          : ""
      }
    </div>

    <div class="grid-2">
      <div class="card fade-up">
        <h3>Resume profile</h3>
        <p class="section-label">Extracted details</p>
        <div class="facts">
          ${fact("Name", resume.name || "—")}
          ${fact("Email", resume.email || "—")}
          ${fact("Phone", resume.phone || "—")}
          ${fact("Skill source", resume.skill_source === "dictionary+llm" ? "Dictionary + LLM" : "Skill dictionary")}
        </div>
        <p class="section-label">Detected skills</p>
        ${chips(resume.skills, "chip-neutral", "No known skills detected.")}
      </div>

      <div class="card fade-up">
        <h3>Job requirements</h3>
        <p class="section-label">Extracted details</p>
        <div class="facts">
          ${fact("Experience", job.required_years_experience ? `${job.required_years_experience}+ years` : "Not specified")}
          ${fact("Education", job.required_education_level ? eduLabel(job.required_education_level) : "Not specified")}
        </div>
        <p class="section-label">Required skills</p>
        ${chips(job.required_skills, "chip-neutral", "None detected.")}
        <p class="section-label">Preferred skills</p>
        ${chips(job.preferred_skills, "chip-preferred", "None detected.")}
      </div>
    </div>

    <div class="card fade-up">
      <div class="title-row"><h3>AI review</h3><span class="badge">Groq LLM</span></div>
      ${
        ai.error
          ? `<p class="empty">${escapeHtml(ai.error)}</p>`
          : `
        <p class="ai-summary">${escapeHtml(ai.summary)}</p>
        <div class="grid-2" style="margin-top:20px">
          <div><p class="section-label" style="margin-top:0">Strengths</p>${iconList(ai.strengths, "list-good", "check")}</div>
          <div><p class="section-label" style="margin-top:0">Gaps</p>${iconList(ai.gaps, "list-bad", "alert")}</div>
        </div>
        <p class="section-label">Suggestions</p>
        ${iconList(ai.recommendations, "list-info", "arrow")}`
      }
    </div>

    <div class="grid-2">
      <div class="card fade-up">
        <h3>Resume quality</h3>
        <p class="section-label">Metrics</p>
        <div class="metrics">
          <div class="metric"><span>Word count</span><span>${quality.word_count ?? "—"}</span></div>
          <div class="metric"><span>Sections</span><span>${Math.round(quality.section_score ?? 0)}%</span></div>
          <div class="metric"><span>Quantified results</span><span>${quality.quantified_results ?? "—"}</span></div>
          <div class="metric"><span>Action verbs</span><span>${quality.action_verbs ?? "—"}</span></div>
          <div class="metric"><span>Bullet points</span><span>${quality.bullet_points ?? "—"}</span></div>
          <div class="metric"><span>Contact info</span><span>${quality.contact_complete ? "Complete" : "Incomplete"}</span></div>
        </div>
        <p class="section-label">Issues</p>
        ${
          (quality.issues || []).length
            ? iconList(quality.issues, "list-bad", "alert")
            : iconList(["No structural issues found."], "list-good", "check")
        }
      </div>

      <div class="card fade-up">
        <h3>Suggested roles</h3>
        <p class="section-label">Based on detected skills</p>
        ${chips(data.job_category_suggestions, "chip-neutral", "Not enough skill signal — add more skills and projects.")}
      </div>
    </div>

    <div class="card fade-up">
      <h3>Action checklist</h3>
      <p class="section-label">Recommended improvements</p>
      <ol class="list checklist">
        ${(data.recommendations || []).map((r, i) => `<li><span class="num-badge">${i + 1}</span><span>${escapeHtml(r)}</span></li>`).join("")}
      </ol>
    </div>
  `;

  resultsSection.classList.remove("hidden");
  resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });

  document.getElementById("print-btn").addEventListener("click", () => window.print());
  document.getElementById("new-btn").addEventListener("click", () => {
    document.getElementById("analyze").scrollIntoView({ behavior: "smooth" });
  });

  requestAnimationFrame(() => {
    document.getElementById("score-circle").style.strokeDashoffset = circumference * (1 - score / 100);
    document.querySelectorAll(".bar-fill").forEach((bar) => {
      bar.style.width = `${Math.min(100, Math.max(0, parseFloat(bar.dataset.target)))}%`;
    });
  });
  animateNumber(document.getElementById("score-number"), Math.round(score));
}

// ---------- History ----------
const historyDrawer = document.getElementById("history-drawer");
const historyList = document.getElementById("history-list");

function openHistory() {
  historyDrawer.classList.remove("hidden");
  historyDrawer.setAttribute("aria-hidden", "false");
  loadHistory();
}

function closeHistory() {
  historyDrawer.classList.add("hidden");
  historyDrawer.setAttribute("aria-hidden", "true");
}

document.getElementById("history-btn").addEventListener("click", openHistory);
document.getElementById("history-backdrop").addEventListener("click", closeHistory);
document.getElementById("history-close").addEventListener("click", closeHistory);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeHistory();
});

async function loadHistory() {
  historyList.innerHTML = '<p class="empty">Loading…</p>';
  try {
    const res = await fetch("/api/history");
    const items = await res.json();
    if (!items.length) {
      historyList.innerHTML = '<p class="empty">No analyses yet. Run your first analysis to see it here.</p>';
      return;
    }
    historyList.innerHTML = items
      .map((item) => {
        const band = scoreBand(item.ats_score);
        return `
        <button data-id="${item.id}" class="history-item" type="button">
          <div class="history-main">
            <p class="history-file">${escapeHtml(item.filename)}</p>
            <p class="muted small">#${item.id} · ${escapeHtml(formatDate(item.created_at))}</p>
          </div>
          <span class="history-score tone-${band.tone}">${Math.round(item.ats_score)}</span>
        </button>`;
      })
      .join("");
    historyList.querySelectorAll("[data-id]").forEach((btn) =>
      btn.addEventListener("click", () => loadHistoryItem(btn.dataset.id))
    );
  } catch {
    historyList.innerHTML = '<p class="field-error">Could not load history.</p>';
  }
}

async function loadHistoryItem(id) {
  try {
    const res = await fetch(`/api/history/${id}`);
    if (!res.ok) throw new Error("Not found");
    const record = await res.json();
    closeHistory();
    renderResults({ ...record.result, analysis_id: record.id });
  } catch {
    historyList.insertAdjacentHTML("afterbegin", '<p class="field-error">Could not open that report.</p>');
  }
}

function refreshHistoryQuietly() {
  if (!historyDrawer.classList.contains("hidden")) loadHistory();
}
