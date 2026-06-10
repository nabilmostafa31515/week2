# Kayfa — Student Analytics Dashboard

An end-to-end analytics project for the **Kayfa (كيف)** learning platform, built for
the *AI & Data Analytics Internship — Month 1, Week 2 Evaluation*.

It takes raw, messy educational data (CSV / JSON / Excel), runs a full
**ETL → feature-engineering → ML** pipeline, stores the precomputed results in
**MongoDB Atlas**, and serves them through an interactive **Streamlit** dashboard that
answers 15 business questions plus a student-segmentation model.

---

## Architecture

The project is split into **two phases** that are deliberately decoupled:

```
                ┌──────────────────────── PHASE 1: OFFLINE PIPELINE ────────────────────────┐
   data/        extraction        preprocessing      analytics + clustering        mongodb
 (8 raw files) ──────────▶  load ──────────▶ clean ──────────▶ model / features / KMeans ──▶ Atlas
                                              (30 fixes)        (15 questions, 4 segments)   (collections)

                ┌──────────────────────── PHASE 2: DASHBOARD ───────────────────────────────┐
   Atlas ──────▶ read_analytics.load_dashboard_data() ──▶ app.py (router) ──▶ page_*.render()
 (collections)        (cached once per session)            (sidebar nav)       (Streamlit + Plotly)
```

**Why two phases?** All heavy computation happens once, offline, and is written to Atlas.
The dashboard only *reads* ready-made results, so it loads fast and does zero
recomputation on each page view.

---

## Project structure

```
project/
├── app.py                       # Streamlit entry point: layout, CSS, sidebar router
├── requirements.txt
├── .env                         # MONGO_URI (git-ignored — never commit)
├── .env.example                 # template for the above
├── data/                        # raw source files (8)
│   ├── students.csv  groups.csv  courses.csv
│   ├── grades.json   attendance.xlsx
│   ├── concepts_performance.csv  engagement_events.csv
│   └── assignment_submissions.csv
└── src/
    ├── extraction/              # load CSV / JSON / Excel into DataFrames
    │   └── load_all.py
    ├── preprocessing/
    │   └── clean.py             # 30 numbered data-quality fixes
    ├── analytics/
    │   ├── model.py             # join "spine" + student/group summary tables
    │   ├── features.py          # attendance, grades, engagement, concepts,
    │   │                        #   submissions, age bands, at-risk scores
    │   └── questions.py         # the 15 analytical Plotly figures (offline)
    ├── clustering/
    │   └── segment.py           # KMeans (k=4) student segmentation
    ├── mongodb/
    │   ├── atlas_client.py      # Atlas connection (reads MONGO_URI)
    │   ├── write_analytics.py   # writes all collections to Atlas
    │   └── read_analytics.py    # reads collections for the dashboard
    └── dashboard/
        ├── page_home.py  page_final.py
        ├── page_q1.py … page_q15.py   # one page per question
        └── page_qN.py               # blank page template
```

---

## Setup

### 1. Prerequisites
- Python 3.12 (the project was developed against CPython 3.12)
- A MongoDB Atlas cluster (free tier is enough)

### 2. Install dependencies

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure the database connection

```bash
cp .env.example .env        # Windows: copy .env.example .env
```

Then edit `.env` and set your own Atlas connection string:

```
MONGO_URI=mongodb+srv://<user>:<password>@<cluster-host>/?appName=Cluster0
```

> **Security:** `.env` is git-ignored. Never commit real credentials. If a password
> ever leaks, rotate it in the Atlas dashboard immediately.

---

## Running the project

### Step 1 — Build the analytics and write them to Atlas (offline, run once)

```bash
python -m src.mongodb.write_analytics
```

This runs the full pipeline (load → clean → model → features → clustering) and upserts
~15 collections into the `kayfa_analytics` database. You only need to re-run it when the
raw data in `data/` changes.

You can also run each stage independently for debugging — each module has a `__main__`
block:

```bash
python -m src.extraction.load_all
python -m src.preprocessing.clean
python -m src.analytics.model
python -m src.analytics.features
python -m src.clustering.segment
```

### Step 2 — Launch the dashboard

```bash
streamlit run app.py
```

Open the URL Streamlit prints (default <http://localhost:8501>). Use the left sidebar to
navigate between Home, the 15 questions, and the Final Solution summary.

---

## MongoDB collections

The pipeline writes the following collections to the `kayfa_analytics` database:

| Collection | Description | Write strategy |
|---|---|---|
| `analytics_summary` | platform-wide KPIs (one document) | replace |
| `group_metrics` | attendance, grade & size per group | upsert by `group_id` |
| `course_metrics` | grade stats per course | upsert by `course_id` |
| `student_risk_scores` | composite at-risk score per student | upsert by `student_id` |
| `clusters` | the 4 segment definitions | upsert by `cluster_id` |
| `student_clusters` | each student's segment assignment | upsert by `student_id` |
| `concept_failures` | failure rate per concept | upsert by `concept_id` |
| `concept_trends` | concept pass-rate over time | replace |
| `monthly_attendance` | attendance trend per student/month | replace |
| `monthly_engagement` | engagement trend per month | replace |
| `grade_trends` | grade trend per group/assessment | replace |
| `student_summary` | full per-student feature table | upsert by `student_id` |
| `age_stats` | metrics by age band | replace |
| `delay_distribution` | submission-timing buckets | replace |
| `assessment_type_distribution` | score stats per assessment type | replace |

---

## The 15 questions

| # | Question | Primary metric |
|---|---|---|
| Q1 | Attendance rate per group | group attendance vs platform avg |
| Q2 | Score distribution by assessment type | volatility / hardest type |
| Q3 | Course performance comparison | avg grade ± std per course |
| Q4 | Attendance vs grade | Pearson correlation |
| Q5 | Engagement vs performance | engagement & watch-time vs grade |
| Q6 | Concept failure rates | failure rate per concept |
| Q7 | Concept mastery trends | pass rate over time |
| Q8 | Submission behaviour | early / late distribution |
| Q9 | Cohort trends | monthly attendance & engagement |
| Q10 | Age band analysis | outcomes per age band |
| Q11 | Student segmentation | KMeans personas |
| Q12 | Group size validation | stated vs true headcount |
| Q13 | Group merge recommendation | profile similarity |
| Q14 | At-risk student ranking | composite risk score |
| Q15 | Group grade trends | improving vs declining groups |

### At-risk score

A composite, min-max normalized score per student (higher = more at risk):

```
at_risk_score = 0.35 · grade_risk
              + 0.30 · attendance_risk
              + 0.20 · engagement_risk
              + 0.15 · concept_risk
```

Students in the top 20% are flagged `is_at_risk`.

### Student segmentation

KMeans on four features — `attendance_rate`, `avg_grade`, `engagement_score`,
`failed_concepts`. Optimal *k* is explored via the elbow + silhouette methods, then
fixed at **k = 4** so the clusters map cleanly to four business personas:

- 🏆 **High Achievers** — on track; offer stretch goals.
- 🚨 **At Risk** — urgent instructor outreach.
- 😴 **Passive Learners** — present but disengaged; activation nudges.
- 💪 **Engaged Strugglers** — high effort, low grades; foundation review.

---

## Data cleaning

`src/preprocessing/clean.py` applies **30 numbered fixes** across the 8 raw sources,
including: null / placeholder names, duplicate student IDs, impossible ages, gender
normalization, orphaned group references, invalid or out-of-range scores, recomputed
`is_late` from timestamps, out-of-term engagement events, and unified attendance
encodings. Each fix prints a one-line audit to the console when the pipeline runs.

---

## Tech stack

`pandas` · `numpy` · `scikit-learn` · `plotly` · `streamlit` · `pymongo` ·
`python-dotenv` · `openpyxl`

---

## Troubleshooting

- **`MONGO_URI is not set`** — copy `.env.example` to `.env` and fill in your URI.
- **Atlas connection timeout** — add your IP to the Atlas Network Access allowlist, and
  confirm the cluster is running.
- **Bad / malformed URI** — if your password contains `@ : / # ? & %`, URL-encode those
  characters in the connection string (e.g. `#` → `%23`).
- **Dashboard shows "No data available"** — run `python -m src.mongodb.write_analytics`
  first to populate Atlas.
- **`statsmodels` errors on scatter plots** — not required; the dashboard computes
  trendlines with `numpy.polyfit` instead of Plotly's OLS option.
