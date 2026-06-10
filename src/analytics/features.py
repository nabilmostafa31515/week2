import pandas as pd
import numpy as np
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "extraction"))
sys.path.append(str(Path(__file__).resolve().parents[1] / "preprocessing"))

from src.extraction.load_all import load_everything
from src.preprocessing.clean import clean_all
from src.analytics.model import build_model

# ══════════════════════════════════════════════════════
#  1. ATTENDANCE FEATURES
# ══════════════════════════════════════════════════════

def compute_attendance_features(attendance: pd.DataFrame) -> pd.DataFrame:
    print("\n── Computing attendance features ──")

    # per student
    student_att = attendance.groupby("student_id").agg(
        attendance_rate   = ("status", "mean"),
        total_sessions    = ("status", "count"),
        sessions_attended = ("status", "sum"),
        sessions_absent   = ("status", lambda x: (x == 0).sum()),
    ).reset_index()
    student_att["attendance_rate"] = (
        student_att["attendance_rate"] * 100
    ).round(2)

    # per group
    group_att = attendance.groupby("group_id").agg(
        group_attendance_rate = ("status", "mean"),
        total_sessions        = ("status", "count"),
    ).reset_index()
    group_att["group_attendance_rate"] = (
        group_att["group_attendance_rate"] * 100
    ).round(2)

    # platform average
    platform_avg = round(attendance["status"].mean() * 100, 2)
    group_att["platform_avg_attendance"] = platform_avg
    group_att["below_platform_avg"] = (
        group_att["group_attendance_rate"] < platform_avg
    )

    # monthly attendance trend per student
    monthly = attendance.groupby(
        ["student_id", "month"]
    )["status"].mean().reset_index()
    monthly["monthly_att_rate"] = (monthly["status"] * 100).round(2)
    monthly = monthly.drop(columns="status")

    print(f"   student_att shape : {student_att.shape}")
    print(f"   group_att shape   : {group_att.shape}")
    print(f"   platform avg att  : {platform_avg}%")
    print(f"   groups below avg  : {group_att['below_platform_avg'].sum()}")

    return student_att, group_att, monthly

# ══════════════════════════════════════════════════════
#  2. GRADE FEATURES
# ══════════════════════════════════════════════════════

def compute_grade_features(grades: pd.DataFrame) -> pd.DataFrame:
    print("\n── Computing grade features ──")

    valid = grades[~grades["invalid_score"] & grades["score_pct"].notna()]

    # per student — overall + per type
    student_grades = valid.groupby("student_id").agg(
        avg_grade          = ("score_pct", "mean"),
        total_assessments  = ("score_pct", "count"),
        grade_std          = ("score_pct", "std"),
    ).round(2).reset_index()

    # per assessment type
    for atype in ["quiz", "assignment", "exam", "practical"]:
        sub = valid[valid["type"] == atype].groupby("student_id")["score_pct"].mean()
        student_grades = student_grades.merge(
            sub.rename(f"avg_{atype}").reset_index(),
            on="student_id", how="left"
        )

    # per course
    course_grades = valid.groupby("course_id").agg(
        course_avg_grade = ("score_pct", "mean"),
        course_grade_std = ("score_pct", "std"),
        course_min_grade = ("score_pct", "min"),
        course_max_grade = ("score_pct", "max"),
    ).round(2).reset_index()

    # per assessment type distribution
    type_dist = valid.groupby("type").agg(
        avg_score  = ("score_pct", "mean"),
        std_score  = ("score_pct", "std"),
        min_score  = ("score_pct", "min"),
        max_score  = ("score_pct", "max"),
        count      = ("score_pct", "count"),
    ).round(2).reset_index()

    # grade trend per group across assessments
    # (grades already carries group_id, so no extra merge is needed —
    #  merging again would collide and rename the column to group_id_x/_y)
    grade_trend = valid.groupby(
        ["group_id", "assessment_id"]
    )["score_pct"].mean().reset_index()
    grade_trend.columns = ["group_id", "assessment_id", "avg_score"]

    print(f"   student_grades shape : {student_grades.shape}")
    print(f"   course_grades shape  : {course_grades.shape}")
    print(f"   type_dist shape      : {type_dist.shape}")

    return student_grades, course_grades, type_dist, grade_trend

# ══════════════════════════════════════════════════════
#  3. ENGAGEMENT FEATURES
# ══════════════════════════════════════════════════════

def compute_engagement_features(engagement: pd.DataFrame) -> pd.DataFrame:
    print("\n── Computing engagement features ──")

    valid = engagement[
        ~engagement["out_of_term"] &
        ~engagement["invalid_duration"]
    ].copy()

    valid["event_datetime"] = pd.to_datetime(valid["event_datetime"])
    valid["month"] = valid["event_datetime"].dt.to_period("M").astype(str)

    # login frequency
    logins = valid[valid["event_type"] == "login"].groupby(
        "student_id"
    ).size().reset_index(name="login_count")

    # total watch time
    watch = valid[valid["event_type"] == "video_watch"].groupby(
        "student_id"
    )["duration_seconds"].sum().reset_index()
    watch["total_watch_hours"] = (
        watch["duration_seconds"] / 3600
    ).round(2)

    # forum posts
    forum = valid[valid["event_type"] == "forum_post"].groupby(
        "student_id"
    ).size().reset_index(name="forum_posts")

    # resource downloads
    downloads = valid[valid["event_type"] == "resource_download"].groupby(
        "student_id"
    ).size().reset_index(name="resource_downloads")

    # quiz attempts
    quiz_att = valid[valid["event_type"] == "quiz_attempt"].groupby(
        "student_id"
    ).size().reset_index(name="quiz_attempts")

    # merge all
    eng = logins \
        .merge(watch[["student_id","total_watch_hours"]], on="student_id", how="outer") \
        .merge(forum,     on="student_id", how="outer") \
        .merge(downloads, on="student_id", how="outer") \
        .merge(quiz_att,  on="student_id", how="outer") \
        .fillna(0)

    # engagement score (weighted)
    # login=1, watch=2, forum=3, download=1.5, quiz_attempt=2
    eng["engagement_score"] = (
        eng["login_count"]          * 1.0 +
        eng["total_watch_hours"]    * 2.0 +
        eng["forum_posts"]          * 3.0 +
        eng["resource_downloads"]   * 1.5 +
        eng["quiz_attempts"]        * 2.0
    ).round(2)

    # monthly engagement trend (platform-wide)
    monthly_eng = valid.groupby("month").agg(
        total_events    = ("event_id", "count"),
        unique_students = ("student_id", "nunique"),
        total_logins    = ("event_type", lambda x: (x == "login").sum()),
        total_watch_sec = ("duration_seconds", "sum"),
    ).reset_index()
    monthly_eng["avg_watch_hours"] = (
        monthly_eng["total_watch_sec"] / 3600
    ).round(2)

    # device split
    device_split = valid.groupby(
        ["student_id", "device"]
    ).size().unstack(fill_value=0).reset_index()
    device_split.columns.name = None

    print(f"   engagement shape      : {eng.shape}")
    print(f"   monthly_eng shape     : {monthly_eng.shape}")
    print(f"   avg engagement score  : {eng['engagement_score'].mean():.2f}")

    return eng, monthly_eng, device_split

# ══════════════════════════════════════════════════════
#  4. CONCEPT FEATURES
# ══════════════════════════════════════════════════════

def compute_concept_features(concepts: pd.DataFrame) -> pd.DataFrame:
    print("\n── Computing concept features ──")

    valid = concepts[concepts["score_pct"].notna()].copy()

    # concept failure rate platform-wide
    concept_fail = valid.groupby(
        ["concept_id", "concept_name", "course_id"]
    ).agg(
        total_attempts  = ("mastery_status", "count"),
        failed_count    = ("mastery_status", lambda x: (x == "failed").sum()),
        avg_score       = ("score_pct", "mean"),
    ).reset_index()
    concept_fail["failure_rate"] = (
        concept_fail["failed_count"] /
        concept_fail["total_attempts"] * 100
    ).round(2)
    concept_fail = concept_fail.sort_values(
        "failure_rate", ascending=False
    )

    # per student concept summary
    student_concepts = valid.groupby("student_id").agg(
        failed_concepts   = ("mastery_status", lambda x: (x == "failed").sum()),
        passed_concepts   = ("mastery_status", lambda x: (x == "passed").sum()),
        total_concepts    = ("mastery_status", "count"),
        concept_pass_rate = ("mastery_status", lambda x: (x == "passed").mean() * 100),
        avg_concept_score = ("score_pct", "mean"),
    ).round(2).reset_index()

    # worst concept trend over time
    # group by concept + timestamp to track mastery progression
    valid["timestamp"] = pd.to_datetime(valid["timestamp"])
    valid["month"] = valid["timestamp"].dt.to_period("M").astype(str)

    concept_trend = valid.groupby(
        ["concept_id", "concept_name", "month"]
    ).agg(
        pass_rate  = ("mastery_status", lambda x: (x == "passed").mean() * 100),
        avg_score  = ("score_pct", "mean"),
        attempts   = ("mastery_status", "count"),
    ).round(2).reset_index()

    print(f"   concept_fail shape    : {concept_fail.shape}")
    print(f"   student_concepts shape: {student_concepts.shape}")
    print(f"   worst concept         : {concept_fail.iloc[0]['concept_name']}")
    print(f"   worst failure rate    : {concept_fail.iloc[0]['failure_rate']}%")

    return concept_fail, student_concepts, concept_trend

# ══════════════════════════════════════════════════════
#  5. SUBMISSION FEATURES
# ══════════════════════════════════════════════════════

def compute_submission_features(submissions: pd.DataFrame) -> pd.DataFrame:
    print("\n── Computing submission features ──")

    valid = submissions[submissions["submitted_at"].notna()].copy()

    student_subs = valid.groupby("student_id").agg(
        late_submission_rate   = ("is_late",                "mean"),
        avg_submission_delay   = ("submission_delay_hours", "mean"),
        avg_time_spent         = ("time_spent_minutes",     "mean"),
        avg_attempts           = ("attempts",               "mean"),
        total_submissions      = ("submission_id",          "count"),
    ).round(2).reset_index()
    student_subs["late_submission_rate"] = (
        student_subs["late_submission_rate"] * 100
    ).round(2)

    # late vs on-time score comparison (join with grades needed)
    late_summary = valid.groupby("is_late").agg(
        count             = ("submission_id",          "count"),
        avg_delay_hours   = ("submission_delay_hours", "mean"),
        avg_time_spent    = ("time_spent_minutes",     "mean"),
        avg_attempts      = ("attempts",               "mean"),
    ).round(2).reset_index()

    # submission delay buckets
    valid["delay_bucket"] = pd.cut(
        valid["submission_delay_hours"],
        bins=[-np.inf, -48, -24, 0, 24, 48, np.inf],
        labels=["2+ days early", "1-2 days early",
                "Same day early", "Up to 1 day late",
                "1-2 days late", "2+ days late"]
    )

    delay_dist = valid.groupby(
        "delay_bucket", observed=True
    ).size().reset_index(name="count")

    print(f"   student_subs shape : {student_subs.shape}")
    print(f"   late rate overall  : {valid['is_late'].mean()*100:.1f}%")

    return student_subs, late_summary, delay_dist

# ══════════════════════════════════════════════════════
#  6. AGE BAND FEATURES
# ══════════════════════════════════════════════════════

def compute_age_features(student_summary: pd.DataFrame) -> pd.DataFrame:
    print("\n── Computing age band features ──")

    df = student_summary[
        student_summary["age"].notna() &
        ~student_summary["suspect_age"]
    ].copy()

    df["age_band"] = pd.cut(
        df["age"],
        bins=[14, 20, 25, 30, 35, 45, 80],
        labels=["15-20", "21-25", "26-30",
                "31-35", "36-45", "46+"]
    )

    age_stats = df.groupby("age_band", observed=True).agg(
        student_count    = ("student_id",       "count"),
        avg_grade        = ("avg_grade",         "mean"),
        avg_attendance   = ("attendance_rate",   "mean"),
        avg_engagement   = ("engagement_score",  "mean"),
        avg_failed_conc  = ("failed_concepts",   "mean"),
    ).round(2).reset_index()

    print(f"   age_stats shape  : {age_stats.shape}")
    print(f"   age bands        : {age_stats['age_band'].tolist()}")

    return age_stats

# ══════════════════════════════════════════════════════
#  7. AT-RISK SCORE
# ══════════════════════════════════════════════════════

def compute_at_risk_scores(student_summary: pd.DataFrame) -> pd.DataFrame:
    print("\n── Computing at-risk scores ──")

    df = student_summary.copy()

    # normalise each dimension 0-1 (higher = more at risk)
    def norm_inv(col):
        # invert: low value = high risk
        mn, mx = df[col].min(), df[col].max()
        return 1 - (df[col] - mn) / (mx - mn + 1e-9)

    def norm(col):
        # direct: high value = high risk
        mn, mx = df[col].min(), df[col].max()
        return (df[col] - mn) / (mx - mn + 1e-9)

    df["risk_attendance"]  = norm_inv("attendance_rate")
    df["risk_grade"]       = norm_inv("avg_grade")
    df["risk_engagement"]  = norm_inv("engagement_score")
    df["risk_concepts"]    = norm("failed_concepts")

    # weighted at-risk score
    df["at_risk_score"] = (
        df["risk_attendance"]  * 0.30 +
        df["risk_grade"]       * 0.35 +
        df["risk_engagement"]  * 0.20 +
        df["risk_concepts"]    * 0.15
    ).round(4)

    # at-risk flag (top 20%)
    threshold = df["at_risk_score"].quantile(0.80)
    df["is_at_risk"] = df["at_risk_score"] >= threshold

    risk_df = df[[
        "student_id", "full_name", "group_name",
        "course_name", "instructor",
        "attendance_rate", "avg_grade",
        "engagement_score", "failed_concepts",
        "risk_attendance", "risk_grade",
        "risk_engagement", "risk_concepts",
        "at_risk_score", "is_at_risk"
    ]].sort_values("at_risk_score", ascending=False)

    print(f"   total students   : {len(df)}")
    print(f"   at-risk students : {df['is_at_risk'].sum()}")
    print(f"   risk threshold   : {threshold:.4f}")
    print(f"\n   Top 10 at-risk students:")
    print(risk_df.head(10)[[
        "student_id","full_name","attendance_rate",
        "avg_grade","at_risk_score"
    ]].to_string(index=False))

    return risk_df

# ══════════════════════════════════════════════════════
#  8. GROUP SIZE VALIDATION
# ══════════════════════════════════════════════════════

def compute_group_size_validation(
    students: pd.DataFrame,
    groups: pd.DataFrame
) -> pd.DataFrame:
    print("\n── Computing group size validation ──")

    # true count from students.csv (source of truth)
    true_counts = students[
        students["group_id"].notna()
    ]["group_id"].value_counts().reset_index()
    true_counts.columns = ["group_id", "true_count"]

    grp = groups[~groups["is_test_group"]].merge(
        true_counts, on="group_id", how="left"
    )
    grp["true_count"]    = grp["true_count"].fillna(0).astype(int)
    grp["discrepancy"]   = grp["stated_num_students"] - grp["true_count"]
    grp["discrepancy_pct"] = (
        grp["discrepancy"] / grp["stated_num_students"] * 100
    ).round(1)
    grp["flag"] = grp["discrepancy"].abs() > 3

    print(f"   groups with discrepancy : {grp['flag'].sum()}")
    print(grp[[
        "group_id","group_name","stated_num_students",
        "true_count","discrepancy","flag"
    ]].to_string(index=False))

    return grp

# ══════════════════════════════════════════════════════
#  RUN ALL FEATURES
# ══════════════════════════════════════════════════════

def compute_all_features(model: dict) -> dict:
    print("\n" + "=" * 55)
    print("  KAYFA — Computing all features")
    print("=" * 55)

    student_att, group_att, monthly_att = compute_attendance_features(
        model["attendance"]
    )
    student_grades, course_grades, type_dist, grade_trend = compute_grade_features(
        model["grades"]
    )
    eng, monthly_eng, device_split = compute_engagement_features(
        model["engagement"]
    )
    concept_fail, student_concepts, concept_trend = compute_concept_features(
        model["concepts"]
    )
    student_subs, late_summary, delay_dist = compute_submission_features(
        model["submissions"]
    )
    age_stats = compute_age_features(
        model["student_summary"]
    )
    risk_df = compute_at_risk_scores(
        model["student_summary"]
    )
    group_size = compute_group_size_validation(
        model["spine"],
        model["groups"]
    )

    features = {
        # attendance
        "student_att":       student_att,
        "group_att":         group_att,
        "monthly_att":       monthly_att,
        # grades
        "student_grades":    student_grades,
        "course_grades":     course_grades,
        "type_dist":         type_dist,
        "grade_trend":       grade_trend,
        # engagement
        "eng":               eng,
        "monthly_eng":       monthly_eng,
        "device_split":      device_split,
        # concepts
        "concept_fail":      concept_fail,
        "student_concepts":  student_concepts,
        "concept_trend":     concept_trend,
        # submissions
        "student_subs":      student_subs,
        "late_summary":      late_summary,
        "delay_dist":        delay_dist,
        # aggregates
        "age_stats":         age_stats,
        "risk_df":           risk_df,
        "group_size":        group_size,
    }

    print("\n" + "=" * 55)
    print("  ✅ All features computed")
    print("=" * 55)

    print(f"\n{'Feature Table':<22} {'Rows':>8} {'Cols':>6}")
    print("-" * 38)
    for name, df in features.items():
        print(f"{name:<22} {df.shape[0]:>8,} {df.shape[1]:>6}")

    return features


if __name__ == "__main__":
    dfs      = load_everything()
    cleaned  = clean_all(dfs)
    model    = build_model(cleaned)
    features = compute_all_features(model)