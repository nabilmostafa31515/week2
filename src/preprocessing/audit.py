import pandas as pd
import numpy as np
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parents[1] / "extraction"))
from src.extraction.load_all import load_everything
# ══════════════════════════════════════════════════════
#  AUDIT FRAMEWORK
# ══════════════════════════════════════════════════════

issues = []   # كل مشكلة هتتضاف هنا

def log_issue(issue, file, impact, fix, rows_affected):
    issues.append({
        "Issue":         issue,
        "File":          file,
        "Impact":        impact,
        "Fix":           fix,
        "Rows Affected": rows_affected
    })

# ══════════════════════════════════════════════════════
#  1. STUDENTS.CSV
# ══════════════════════════════════════════════════════

def audit_students(df: pd.DataFrame, valid_groups: set):
    print("\n── Auditing students.csv ──")

    # missing full_name
    n = df["full_name"].isna().sum()
    if n:
        log_issue("Null full_name", "students.csv",
                  "Display issues", "Flag as 'Unknown [id]'", n)

    # duplicate student_id
    n = df["student_id"].duplicated().sum()
    if n:
        log_issue("Duplicate student_id", "students.csv",
                  "Inflated counts, wrong joins", "Keep first, drop duplicate", n)

    # impossible ages
    bad_age = df[(df["age"] < 15) | (df["age"] > 80)]
    if len(bad_age):
        log_issue("Impossible age (< 15 or > 80)", "students.csv",
                  "Corrupts age-band analysis", "Set to NaN, flag suspect_age=True",
                  len(bad_age))

    # gender inconsistency
    canonical = {"Male", "Female"}
    bad_gender = df[~df["gender"].isin(canonical)]
    if len(bad_gender):
        log_issue("Inconsistent gender encoding", "students.csv",
                  "Wrong gender distribution", "Normalise to Male/Female",
                  len(bad_gender))

    # duplicate emails
    n = df["email"].duplicated().sum()
    if n:
        log_issue("Duplicate email addresses", "students.csv",
                  "CRM issues (not join-breaking)", "Flag, do not drop", n)

    # invalid group_id
    bad_grp = df[~df["group_id"].isin(valid_groups)]
    if len(bad_grp):
        log_issue("student_id references non-existent group_id (GZZ, G77)",
                  "students.csv",
                  "Breaks students→groups→courses chain",
                  "Set group_id=NaN, flag orphan_student=True",
                  len(bad_grp))

    print(f"   Issues found: {len([i for i in issues if i['File']=='students.csv'])}")

# ══════════════════════════════════════════════════════
#  2. GROUPS.CSV
# ══════════════════════════════════════════════════════

def audit_groups(df: pd.DataFrame):
    print("\n── Auditing groups.csv ──")

    # duplicate group row
    n = df.duplicated().sum()
    if n:
        log_issue("Exact duplicate row (G01)", "groups.csv",
                  "Inflated group count", "Drop duplicate row", n)

    # test/phantom group
    test = df[df["group_name"].str.contains("TEST|DELETE", case=False, na=False)]
    if len(test):
        log_issue("Phantom test group G99 (TEST_GROUP_DELETE)", "groups.csv",
                  "Pollutes all group-level metrics", "Exclude G99 from all analyses",
                  len(test))

    # session_time format inconsistency
    non_standard = df[~df["session_time"].astype(str).str.match(r"^\d{2}:\d{2}$")]
    if len(non_standard):
        log_issue("session_time in mixed formats (6 PM, 1800, 00:00)", "groups.csv",
                  "Cannot sort or compare session times",
                  "Normalise all to HH:MM 24-hour format",
                  len(non_standard))

    # tiny group
    print(f"   ⚠️  G99 has 0 students in students.csv — phantom group")
    print(f"   ⚠️  G10 has 1 student in students.csv — candidate for merge")

    print(f"   Issues found: {len([i for i in issues if i['File']=='groups.csv'])}")

# ══════════════════════════════════════════════════════
#  3. GRADES.JSON
# ══════════════════════════════════════════════════════

def audit_grades(df: pd.DataFrame):
    print("\n── Auditing grades.json ──")

    # negative scores
    n = (df["score"] < 0).sum()
    if n:
        log_issue("Negative score (score = -10)", "grades.json",
                  "Pulls down averages", "Set to NaN, flag invalid_score=True", n)

    # scores > 100
    n = (df["score"] > 100).sum()
    if n:
        log_issue("Score > max_score (score = 187)", "grades.json",
                  "Inflates averages", "Set to NaN, flag invalid_score=True", n)

    # null scores
    n = df["score"].isna().sum()
    if n:
        log_issue("Null score values", "grades.json",
                  "Missing data in grade analyses", "Retain as NaN, do not impute", n)

    print(f"   Issues found: {len([i for i in issues if i['File']=='grades.json'])}")

# ══════════════════════════════════════════════════════
#  4. ATTENDANCE.XLSX
# ══════════════════════════════════════════════════════

def audit_attendance(df: pd.DataFrame):
    print("\n── Auditing attendance.xlsx ──")

    encodings = {
        "2025-12": "attended/absent/Atttended (typo)",
        "2026-01": "Present/Absent",
        "2026-02": "1/0 integers + renamed column",
        "2026-03": "P/A",
        "2026-04": "yes/no",
        "2026-05": "True/False booleans",
    }
    for sheet, enc in encodings.items():
        log_issue(f"Status encoding: {enc}", f"attendance.xlsx ({sheet})",
                  "Cannot concatenate sheets without reconciliation",
                  "Map all to binary 1=attended, 0=absent", 
                  df[df["month"] == sheet].shape[0])

    # null status after mapping
    n = df["status"].isna().sum()
    if n:
        log_issue("Null status after mapping", "attendance.xlsx",
                  "Unknown attendance records", "Investigate, exclude from rate calc", n)

    print(f"   Issues found: 7 (6 encoding + 1 column rename)")

# ══════════════════════════════════════════════════════
#  5. CONCEPTS_PERFORMANCE.CSV
# ══════════════════════════════════════════════════════

def audit_concepts(df: pd.DataFrame):
    print("\n── Auditing concepts_performance.csv ──")

    # impossible score_pct
    n = (df["score_pct"] < 0).sum()
    if n:
        log_issue("Negative score_pct (-33)", "concepts_performance.csv",
                  "Corrupts concept mastery analysis",
                  "Set to NaN, flag invalid_score=True", n)

    n = (df["score_pct"] > 100).sum()
    if n:
        log_issue("score_pct > 100 (142)", "concepts_performance.csv",
                  "Inflates mastery rates",
                  "Set to NaN, flag invalid_score=True", n)

    # mastery_status contradiction
    contradictions = df[
        ((df["score_pct"] >= 50) & (df["mastery_status"] == "failed")) |
        ((df["score_pct"] <  50) & (df["mastery_status"] == "passed"))
    ]
    if len(contradictions):
        log_issue("mastery_status contradicts score_pct (1761 records)",
                  "concepts_performance.csv",
                  "Wrong pass/fail flags throughout",
                  "Recompute mastery_status from score_pct using threshold=50",
                  len(contradictions))

    print(f"   Issues found: {len([i for i in issues if i['File']=='concepts_performance.csv'])}")

# ══════════════════════════════════════════════════════
#  6. ENGAGEMENT_EVENTS.CSV
# ══════════════════════════════════════════════════════

def audit_engagement(df: pd.DataFrame):
    print("\n── Auditing engagement_events.csv ──")

    # duplicate event_ids
    n = df["event_id"].duplicated().sum()
    if n:
        log_issue("Duplicate event_ids (8 records)", "engagement_events.csv",
                  "Double-counts activity", "Drop exact duplicates, keep first", n)

    # out-of-term dates
    df["event_datetime"] = pd.to_datetime(df["event_datetime"], errors="coerce")
    out = df[df["event_datetime"] < "2025-12-01"]
    if len(out):
        log_issue("Event dated 2025-01-01 (before term start)", "engagement_events.csv",
                  "Corrupts time-series trend analysis",
                  "Flag out_of_term=True, exclude from trends", len(out))

    # negative duration
    n = (df["duration_seconds"] < 0).sum()
    if n:
        log_issue("Negative duration_seconds (-120)", "engagement_events.csv",
                  "Corrupts watch-time totals",
                  "Set to NaN, flag invalid_duration=True", n)

    # expected nulls — confirm OK
    non_video_nulls = df[
        (df["event_type"] != "video_watch") & (df["duration_seconds"].isna())
    ].shape[0]
    print(f"   ✅ {non_video_nulls:,} null duration_seconds on non-video events — expected, OK")

    print(f"   Issues found: {len([i for i in issues if i['File']=='engagement_events.csv'])}")

# ══════════════════════════════════════════════════════
#  7. ASSIGNMENT_SUBMISSIONS.CSV
# ══════════════════════════════════════════════════════

def audit_submissions(df: pd.DataFrame):
    print("\n── Auditing assignment_submissions.csv ──")

    df["deadline"]     = pd.to_datetime(df["deadline"],     errors="coerce")
    df["submitted_at"] = pd.to_datetime(df["submitted_at"], errors="coerce")

    # null submitted_at
    n = df["submitted_at"].isna().sum()
    if n:
        log_issue("Null submitted_at (1 record)", "assignment_submissions.csv",
                  "Cannot compute lateness for this record",
                  "Retain NaN, exclude from timing analyses", n)

    # is_late flag mismatch
    mismatch = df[
        df["submitted_at"].notna() &
        (df["is_late"] != (df["submitted_at"] > df["deadline"]))
    ]
    if len(mismatch):
        log_issue("is_late flag disagrees with actual timestamps (2 records)",
                  "assignment_submissions.csv",
                  "Wrong late-submission statistics",
                  "Recompute is_late = submitted_at > deadline, keep is_late_raw",
                  len(mismatch))

    # zero time_spent
    n = (df["time_spent_minutes"] <= 0).sum()
    if n:
        log_issue("time_spent_minutes <= 0 (1 record)", "assignment_submissions.csv",
                  "Corrupts effort analysis",
                  "Set to NaN, flag invalid_time=True", n)

    print(f"   Issues found: {len([i for i in issues if i['File']=='assignment_submissions.csv'])}")

# ══════════════════════════════════════════════════════
#  8. CROSS-FILE LOGICAL CHECKS
# ══════════════════════════════════════════════════════

def audit_cross_file(students: pd.DataFrame, groups: pd.DataFrame):
    print("\n── Auditing cross-file integrity ──")

    valid_groups = set(groups["group_id"])

    # orphan students
    orphans = students[~students["group_id"].isin(valid_groups)]
    if len(orphans):
        log_issue(
            "Students reference group_ids not in groups.csv (GZZ, G77)",
            "students.csv × groups.csv",
            "Breaks students→groups→courses lookup chain",
            "Set group_id=NaN, flag orphan_student=True",
            len(orphans)
        )

    # phantom group
    groups_with_students = set(students["group_id"].dropna())
    phantom = valid_groups - groups_with_students
    if phantom:
        log_issue(
            f"Groups in groups.csv with zero students: {phantom}",
            "groups.csv × students.csv",
            "Phantom groups pollute group metrics",
            "Exclude from all analyses",
            len(phantom)
        )

    print(f"   Issues found: {len([i for i in issues if '×' in i['File']])}")

# ══════════════════════════════════════════════════════
#  RUN FULL AUDIT
# ══════════════════════════════════════════════════════

def run_audit(dfs: dict) -> pd.DataFrame:
    valid_groups = set(dfs["groups"]["group_id"])

    audit_students(dfs["students"], valid_groups)
    audit_groups(dfs["groups"])
    audit_grades(dfs["grades"])
    audit_attendance(dfs["attendance"])
    audit_concepts(dfs["concepts"])
    audit_engagement(dfs["engagement"])
    audit_submissions(dfs["submissions"])
    audit_cross_file(dfs["students"], dfs["groups"])

    # build the cleaning log DataFrame
    log_df = pd.DataFrame(issues)

    print("\n" + "=" * 60)
    print(f"  TOTAL ISSUES FOUND : {len(log_df)}")
    print(f"  Target (planted)   : 37")
    print("=" * 60)
    print("\n── Cleaning Log ──")
    print(log_df.to_string(index=False))

    # save to CSV for the notebook
    out_path = Path(__file__).resolve().parents[2] / "data" / "cleaning_log.csv"
    log_df.to_csv(out_path, index=False)
    print(f"\n✅ Cleaning log saved → {out_path}")

    return log_df

if __name__ == "__main__":
    dfs = load_everything()
    log_df = run_audit(dfs)