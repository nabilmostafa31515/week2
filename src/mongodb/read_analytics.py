import pandas as pd
from .atlas_client import get_db


# ══════════════════════════════════════════════════════

def _col_to_df(db, collection_name: str) -> pd.DataFrame:
    docs = list(db[collection_name].find({}, {"_id": 0}))
    return pd.DataFrame(docs)

def read_summary(db)          -> dict:
    return db["analytics_summary"].find_one({}, {"_id": 0}) or {}

def read_group_metrics(db)    -> pd.DataFrame:
    return _col_to_df(db, "group_metrics")

def read_course_metrics(db)   -> pd.DataFrame:
    return _col_to_df(db, "course_metrics")

def read_risk_scores(db)      -> pd.DataFrame:
    return _col_to_df(db, "student_risk_scores")

def read_clusters(db)         -> pd.DataFrame:
    return _col_to_df(db, "clusters")

def read_student_clusters(db) -> pd.DataFrame:
    return _col_to_df(db, "student_clusters")

def read_concept_failures(db) -> pd.DataFrame:
    return _col_to_df(db, "concept_failures")

def read_concept_trends(db)   -> pd.DataFrame:
    return _col_to_df(db, "concept_trends")

def read_monthly_attendance(db) -> pd.DataFrame:
    return _col_to_df(db, "monthly_attendance")

def read_monthly_engagement(db) -> pd.DataFrame:
    return _col_to_df(db, "monthly_engagement")

def read_grade_trends(db)     -> pd.DataFrame:
    return _col_to_df(db, "grade_trends")

def read_student_summary(db)  -> pd.DataFrame:
    return _col_to_df(db, "student_summary")

def read_age_stats(db)        -> pd.DataFrame:
    return _col_to_df(db, "age_stats")

def read_delay_dist(db)       -> pd.DataFrame:
    return _col_to_df(db, "delay_distribution")

def read_type_dist(db)        -> pd.DataFrame:
    return _col_to_df(db, "assessment_type_distribution")

# ══════════════════════════════════════════════════════
#
# ══════════════════════════════════════════════════════

def load_dashboard_data() -> dict:
    print("📡 Loading dashboard data from MongoDB Atlas...")
    db = get_db()

    data = {
        "summary":            read_summary(db),
        "group_metrics":      read_group_metrics(db),
        "course_metrics":     read_course_metrics(db),
        "risk_scores":        read_risk_scores(db),
        "clusters":           read_clusters(db),
        "student_clusters":   read_student_clusters(db),
        "concept_failures":   read_concept_failures(db),
        "concept_trends":     read_concept_trends(db),
        "monthly_att":        read_monthly_attendance(db),
        "monthly_eng":        read_monthly_engagement(db),
        "grade_trends":       read_grade_trends(db),
        "student_summary":    read_student_summary(db),
        "age_stats":          read_age_stats(db),
        "delay_dist":         read_delay_dist(db),
        "type_dist":          read_type_dist(db),
    }

    print(f"✅ Loaded {len(data)} collections from Atlas\n")
    return data