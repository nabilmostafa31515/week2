import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "extraction"))
sys.path.append(str(Path(__file__).resolve().parents[1] / "preprocessing"))

from src.extraction.load_all import load_everything
from src.preprocessing.clean import clean_all
# ══════════════════════════════════════════════════════
#  STEP 1 — BUILD CORE SPINE
#  students → groups → courses
# ══════════════════════════════════════════════════════

def build_spine(students, groups, courses):
    """
    الـ spine هو الجدول الأساسي اللي كل حاجة بتتجوين عليه
    students → groups → courses
    """
    print("\n── Step 1: Building core spine ──")

    # بنشيل الـ test group G99 من الـ groups
    groups_clean = groups[~groups["is_test_group"]].copy()

    # students → groups
    spine = students.merge(
        groups_clean[[
            "group_id", "group_name", "course_id",
            "stated_num_students", "session_day",
            "session_time", "instructor"
        ]],
        on="group_id",
        how="left"       # left عشان نحتفظ بالـ orphan students كـ NaN
    )

    # groups → courses
    spine = spine.merge(
        courses[[
            "course_id", "course_name",
            "category", "difficulty_level", "duration_weeks"
        ]],
        on="course_id",
        how="left"
    )

    print(f"   students          : {len(students):>6,}")
    print(f"   spine (with joins): {len(spine):>6,}")
    print(f"   orphan students   : {spine['course_id'].isna().sum():>6}")
    print(f"   cols              : {list(spine.columns)}")

    return spine

# ══════════════════════════════════════════════════════
#  STEP 2 — JOIN GRADES
# ══════════════════════════════════════════════════════

def join_grades(spine, grades):
    print("\n── Step 2: Joining grades ──")

    df = spine.merge(
        grades[[
            "student_id", "assessment_id", "assessment_title",
            "type", "score", "score_pct", "max_score",
            "date", "invalid_score"
        ]],
        on="student_id",
        how="left"
    )

    print(f"   spine rows        : {len(spine):>6,}")
    print(f"   after grade join  : {len(df):>6,}")
    print(f"   null scores       : {df['score'].isna().sum():>6,}")

    return df

# ══════════════════════════════════════════════════════
#  STEP 3 — JOIN ATTENDANCE
# ══════════════════════════════════════════════════════

def join_attendance(spine, attendance):
    print("\n── Step 3: Joining attendance ──")

    df = spine.merge(
        attendance[[
            "student_id", "group_id", "session_type",
            "session_datetime", "status", "month"
        ]],
        on=["student_id", "group_id"],
        how="left"
    )

    print(f"   spine rows        : {len(spine):>6,}")
    print(f"   after att. join   : {len(df):>6,}")
    print(f"   null status       : {df['status'].isna().sum():>6,}")

    return df

# ══════════════════════════════════════════════════════
#  STEP 4 — JOIN CONCEPTS PERFORMANCE
# ══════════════════════════════════════════════════════

def join_concepts(spine, concepts):
    print("\n── Step 4: Joining concepts performance ──")

    df = spine.merge(
        concepts[[
            "student_id", "course_id", "assessment_id",
            "concept_id", "concept_name", "score_pct",
            "mastery_status", "mastery_status_raw",
            "timestamp", "invalid_score"
        ]],
        on=["student_id", "course_id"],
        how="left",
        suffixes=("", "_concept")
    )

    print(f"   spine rows        : {len(spine):>6,}")
    print(f"   after concept join: {len(df):>6,}")

    return df

# ══════════════════════════════════════════════════════
#  STEP 5 — JOIN ENGAGEMENT
# ══════════════════════════════════════════════════════

def join_engagement(spine, engagement):
    print("\n── Step 5: Joining engagement events ──")

    df = spine.merge(
        engagement[[
            "student_id", "event_type", "event_datetime",
            "duration_seconds", "device",
            "out_of_term", "invalid_duration"
        ]],
        on="student_id",
        how="left"
    )

    print(f"   spine rows        : {len(spine):>6,}")
    print(f"   after eng. join   : {len(df):>6,}")

    return df

# ══════════════════════════════════════════════════════
#  STEP 6 — JOIN SUBMISSIONS
# ══════════════════════════════════════════════════════

def join_submissions(spine, submissions):
    print("\n── Step 6: Joining submissions ──")

    df = spine.merge(
        submissions[[
            "student_id", "course_id", "assessment_id",
            "deadline", "submitted_at", "is_late",
            "is_late_raw", "time_spent_minutes",
            "attempts", "submission_delay_hours",
            "invalid_time"
        ]],
        on=["student_id", "course_id"],
        how="left"
    )

    print(f"   spine rows        : {len(spine):>6,}")
    print(f"   after sub. join   : {len(df):>6,}")

    return df

# ══════════════════════════════════════════════════════
#  STEP 7 — BUILD STUDENT SUMMARY TABLE
#  هنا بنعمل aggregation للـ student-level features
#  اللي هيتبنى عليها كل التحليل
# ══════════════════════════════════════════════════════

def build_student_summary(
    spine, grades, attendance, concepts, engagement, submissions
) -> pd.DataFrame:

    print("\n── Step 7: Building student summary table ──")

    # ── Grades features ───────────────────────────────
    grade_feats = grades[~grades["invalid_score"]].groupby("student_id").agg(
        avg_grade        = ("score_pct", "mean"),
        avg_quiz         = ("score_pct", lambda x:
                            x[grades.loc[x.index, "type"] == "quiz"].mean()),
        avg_assignment   = ("score_pct", lambda x:
                            x[grades.loc[x.index, "type"] == "assignment"].mean()),
        avg_exam         = ("score_pct", lambda x:
                            x[grades.loc[x.index, "type"] == "exam"].mean()),
        avg_practical    = ("score_pct", lambda x:
                            x[grades.loc[x.index, "type"] == "practical"].mean()),
        total_assessments= ("score_pct", "count"),
    ).round(2).reset_index()

    # ── Attendance features ───────────────────────────
    att_feats = attendance.groupby("student_id").agg(
        attendance_rate  = ("status", "mean"),
        total_sessions   = ("status", "count"),
    ).round(4).reset_index()
    att_feats["attendance_rate"] = (att_feats["attendance_rate"] * 100).round(2)

    # ── Engagement features ───────────────────────────
    eng_valid = engagement[~engagement["out_of_term"] & ~engagement["invalid_duration"]]

    login_freq = eng_valid[eng_valid["event_type"] == "login"] \
        .groupby("student_id").size().reset_index(name="login_count")

    watch_time = eng_valid[eng_valid["event_type"] == "video_watch"] \
        .groupby("student_id")["duration_seconds"] \
        .sum().reset_index(name="total_watch_seconds")
    watch_time["total_watch_hours"] = (
        watch_time["total_watch_seconds"] / 3600
    ).round(2)

    forum_posts = eng_valid[eng_valid["event_type"] == "forum_post"] \
        .groupby("student_id").size().reset_index(name="forum_posts")

    downloads = eng_valid[eng_valid["event_type"] == "resource_download"] \
        .groupby("student_id").size().reset_index(name="resource_downloads")

    eng_feats = login_freq \
        .merge(watch_time[["student_id", "total_watch_hours"]], on="student_id", how="outer") \
        .merge(forum_posts,  on="student_id", how="outer") \
        .merge(downloads,    on="student_id", how="outer") \
        .fillna(0)

    # engagement score = weighted combination
    eng_feats["engagement_score"] = (
        eng_feats["login_count"]         * 1.0 +
        eng_feats["total_watch_hours"]   * 2.0 +
        eng_feats["forum_posts"]         * 3.0 +
        eng_feats["resource_downloads"]  * 1.5
    ).round(2)

    # ── Concepts features ─────────────────────────────
    concept_feats = concepts[concepts["score_pct"].notna()].groupby("student_id").agg(
        failed_concepts  = ("mastery_status", lambda x: (x == "failed").sum()),
        total_concepts   = ("mastery_status", "count"),
        concept_pass_rate= ("mastery_status", lambda x: (x == "passed").mean() * 100),
    ).round(2).reset_index()

    # ── Submission features ───────────────────────────
    sub_feats = submissions.groupby("student_id").agg(
        late_submission_rate   = ("is_late", "mean"),
        avg_submission_delay   = ("submission_delay_hours", "mean"),
        avg_time_spent         = ("time_spent_minutes", "mean"),
        avg_attempts           = ("attempts", "mean"),
    ).round(2).reset_index()
    sub_feats["late_submission_rate"] = (
        sub_feats["late_submission_rate"] * 100
    ).round(2)

    # ── Merge everything onto spine ───────────────────
    summary = spine[[
        "student_id", "full_name", "age", "gender",
        "city", "group_id", "group_name",
        "course_id", "course_name", "category",
        "difficulty_level", "instructor",
        "orphan_student", "suspect_age"
    ]].drop_duplicates("student_id")

    for feats in [
        grade_feats, att_feats, eng_feats,
        concept_feats, sub_feats
    ]:
        summary = summary.merge(feats, on="student_id", how="left")

    summary = summary.fillna({
        "avg_grade":            np.nan,
        "attendance_rate":      np.nan,
        "engagement_score":     0,
        "failed_concepts":      0,
        "late_submission_rate": 0,
    })

    print(f"   Student summary shape: {summary.shape}")
    print(f"   Columns: {list(summary.columns)}")

    return summary

# ══════════════════════════════════════════════════════
#  STEP 8 — BUILD GROUP SUMMARY TABLE
# ══════════════════════════════════════════════════════

def build_group_summary(student_summary, groups, students_raw) -> pd.DataFrame:
    print("\n── Step 8: Building group summary table ──")

    # true headcount from students.csv
    true_counts = students_raw[
        students_raw["group_id"].notna()
    ]["group_id"].value_counts().reset_index()
    true_counts.columns = ["group_id", "true_student_count"]

    grp = student_summary.groupby("group_id").agg(
        avg_grade        = ("avg_grade",        "mean"),
        avg_attendance   = ("attendance_rate",   "mean"),
        avg_engagement   = ("engagement_score",  "mean"),
        avg_failed_concepts = ("failed_concepts","mean"),
    ).round(2).reset_index()

    grp = grp.merge(
        groups[["group_id", "group_name", "course_id",
                "stated_num_students", "instructor",
                "session_day", "session_time"]],
        on="group_id", how="left"
    ).merge(true_counts, on="group_id", how="left")

    grp["headcount_discrepancy"] = (
        grp["stated_num_students"] - grp["true_student_count"]
    )

    print(f"   Group summary shape: {grp.shape}")
    return grp

# ══════════════════════════════════════════════════════
#  BUILD FULL MODEL
# ══════════════════════════════════════════════════════

def build_model(cleaned: dict) -> dict:
    print("\n" + "=" * 55)
    print("  KAYFA — Building analytics model")
    print("=" * 55)

    spine = build_spine(
        cleaned["students"],
        cleaned["groups"],
        cleaned["courses"]
    )

    student_summary = build_student_summary(
        spine,
        cleaned["grades"],
        cleaned["attendance"],
        cleaned["concepts"],
        cleaned["engagement"],
        cleaned["submissions"]
    )

    group_summary = build_group_summary(
        student_summary,
        cleaned["groups"],
        cleaned["students"]
    )

    model = {
        "spine":           spine,
        "grades":          cleaned["grades"],
        "attendance":      cleaned["attendance"],
        "concepts":        cleaned["concepts"],
        "engagement":      cleaned["engagement"],
        "submissions":     cleaned["submissions"],
        "student_summary": student_summary,
        "group_summary":   group_summary,
        "courses":         cleaned["courses"],
        "groups":          cleaned["groups"],
    }

    print("\n" + "=" * 55)
    print("  ✅ Analytics model ready")
    print("=" * 55)

    print(f"\n{'Table':<22} {'Rows':>8} {'Cols':>6}")
    print("-" * 38)
    for name, df in model.items():
        print(f"{name:<22} {df.shape[0]:>8,} {df.shape[1]:>6}")

    return model


if __name__ == "__main__":
    dfs     = load_everything()
    cleaned = clean_all(dfs)
    model   = build_model(cleaned)