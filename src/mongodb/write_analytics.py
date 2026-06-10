import sys
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

# Force UTF-8 console output so emoji in log prints (✅ → 📡) don't crash
# with UnicodeEncodeError on Windows' default cp1252 code page.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass
from src.extraction.load_all import load_everything
from src.preprocessing.clean import clean_all
from src.analytics.model import build_model
from src.analytics.features import compute_all_features
from src.clustering.segment import run_clustering
from src.mongodb.atlas_client import get_db

# ══════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════

def df_to_docs(df: pd.DataFrame) -> list:
    """
    Convert DataFrame to list of MongoDB documents.
    Handles NaN, numpy types, and timestamps.
    """
    records = df.copy()

    # convert timestamps to strings
    for col in records.select_dtypes(include=["datetime64[ns]",
                                               "datetime64[ns, UTC]"]).columns:
        records[col] = records[col].astype(str)

    # convert period columns
    for col in records.columns:
        if hasattr(records[col], "dt") and hasattr(records[col].dt, "to_timestamp"):
            records[col] = records[col].astype(str)

    docs = records.to_dict(orient="records")

    # clean each document
    clean_docs = []
    for doc in docs:
        clean_doc = {}
        for k, v in doc.items():
            if isinstance(v, float) and np.isnan(v):
                clean_doc[k] = None
            elif isinstance(v, (np.integer,)):
                clean_doc[k] = int(v)
            elif isinstance(v, (np.floating,)):
                clean_doc[k] = float(v)
            elif isinstance(v, (np.bool_,)):
                clean_doc[k] = bool(v)
            elif isinstance(v, (np.ndarray,)):
                clean_doc[k] = v.tolist()
            else:
                clean_doc[k] = v
        clean_docs.append(clean_doc)

    return clean_docs

def upsert_collection(
    db,
    collection_name: str,
    docs: list,
    key_field: str = None
):
    """
    Drop and re-insert collection.
    If key_field given, uses replace_one with upsert for idempotency.
    """
    col = db[collection_name]

    if key_field:
        inserted = 0
        for doc in docs:
            col.replace_one(
                {key_field: doc[key_field]},
                doc,
                upsert=True
            )
            inserted += 1
        print(f"   ✅ {collection_name:<30} "
              f"upserted {inserted} docs (key={key_field})")
    else:
        col.drop()
        if docs:
            col.insert_many(docs)
        print(f"   ✅ {collection_name:<30} "
              f"inserted {len(docs)} docs")

# ══════════════════════════════════════════════════════
#  WRITE — ANALYTICS SUMMARY
# ══════════════════════════════════════════════════════

def write_analytics_summary(db, features: dict):
    print("\n── Writing analytics_summary ──")

    summary = {
        "generated_at":         datetime.utcnow().isoformat(),
        "total_students":        int(features["student_att"]["student_id"].nunique()),
        "total_groups":          int(features["group_att"]["group_id"].nunique()),
        "platform_avg_attendance": float(
            features["group_att"]["group_attendance_rate"].mean()
        ),
        "platform_avg_grade":    float(
            features["student_grades"]["avg_grade"].mean()
        ),
        "platform_avg_engagement": float(
            features["eng"]["engagement_score"].mean()
        ),
        "total_at_risk":         int(
            features["risk_df"]["is_at_risk"].sum()
        ),
        "worst_concept":         str(
            features["concept_fail"].iloc[0]["concept_name"]
        ),
        "worst_concept_fail_rate": float(
            features["concept_fail"].iloc[0]["failure_rate"]
        ),
        "groups_below_avg_attendance": int(
            features["group_att"]["below_platform_avg"].sum()
        ),
    }

    db["analytics_summary"].drop()
    db["analytics_summary"].insert_one(summary)
    print(f"   ✅ analytics_summary inserted (1 doc)")
    return summary

# ══════════════════════════════════════════════════════
#  WRITE — GROUP METRICS
# ══════════════════════════════════════════════════════

def write_group_metrics(db, features: dict, model: dict):
    print("\n── Writing group_metrics ──")

    # merge group_att + group_size + group_summary
    df = features["group_att"].merge(
        features["group_size"][[
            "group_id", "group_name", "course_id",
            "stated_num_students", "true_count",
            "discrepancy", "flag", "instructor"
        ]],
        on="group_id", how="left"
    ).merge(
        model["group_summary"][[
            "group_id", "avg_grade",
            "avg_engagement", "avg_failed_concepts"
        ]],
        on="group_id", how="left"
    )

    docs = df_to_docs(df)
    upsert_collection(db, "group_metrics", docs, key_field="group_id")

# ══════════════════════════════════════════════════════
#  WRITE — COURSE METRICS
# ══════════════════════════════════════════════════════

def write_course_metrics(db, features: dict, model: dict):
    print("\n── Writing course_metrics ──")

    df = features["course_grades"].merge(
        model["courses"][[
            "course_id", "course_name",
            "category", "difficulty_level", "duration_weeks"
        ]],
        on="course_id", how="left"
    )

    docs = df_to_docs(df)
    upsert_collection(db, "course_metrics", docs, key_field="course_id")

# ══════════════════════════════════════════════════════
#  WRITE — STUDENT RISK SCORES
# ══════════════════════════════════════════════════════

def write_student_risk_scores(db, features: dict):
    print("\n── Writing student_risk_scores ──")

    docs = df_to_docs(features["risk_df"])
    upsert_collection(
        db, "student_risk_scores",
        docs, key_field="student_id"
    )

# ══════════════════════════════════════════════════════
#  WRITE — CLUSTERS
# ══════════════════════════════════════════════════════

def write_clusters(db, cluster_results: dict):
    print("\n── Writing clusters ──")

    # cluster metadata
    docs = df_to_docs(cluster_results["cluster_doc"])
    upsert_collection(
        db, "clusters",
        docs, key_field="cluster_id"
    )

    # student cluster assignments
    student_cluster_df = cluster_results["df_clustered"][[
        "student_id", "full_name", "group_id",
        "cluster", "cluster_label",
        "avg_grade", "attendance_rate",
        "engagement_score", "failed_concepts",
    ]]
    docs2 = df_to_docs(student_cluster_df)
    upsert_collection(
        db, "student_clusters",
        docs2, key_field="student_id"
    )

# ══════════════════════════════════════════════════════
#  WRITE — CONCEPT FAILURES
# ══════════════════════════════════════════════════════

def write_concept_failures(db, features: dict):
    print("\n── Writing concept_failures ──")

    docs = df_to_docs(features["concept_fail"])
    upsert_collection(
        db, "concept_failures",
        docs, key_field="concept_id"
    )

    # concept trend
    trend_docs = df_to_docs(features["concept_trend"])
    upsert_collection(
        db, "concept_trends",
        trend_docs
    )

# ══════════════════════════════════════════════════════
#  WRITE — TIME SERIES
# ══════════════════════════════════════════════════════

def write_time_series(db, features: dict):
    print("\n── Writing time series ──")

    # monthly attendance
    att_docs = df_to_docs(features["monthly_att"])
    upsert_collection(db, "monthly_attendance", att_docs)

    # monthly engagement
    eng_docs = df_to_docs(features["monthly_eng"])
    upsert_collection(db, "monthly_engagement", eng_docs)

    # grade trend per group
    grade_docs = df_to_docs(features["grade_trend"])
    upsert_collection(db, "grade_trends", grade_docs)

# ══════════════════════════════════════════════════════
#  WRITE — STUDENT SUMMARY
# ══════════════════════════════════════════════════════

def write_student_summary(db, model: dict):
    print("\n── Writing student_summary ──")

    docs = df_to_docs(model["student_summary"])
    upsert_collection(
        db, "student_summary",
        docs, key_field="student_id"
    )

# ══════════════════════════════════════════════════════
#  WRITE — AGE & SUBMISSION STATS
# ══════════════════════════════════════════════════════

def write_supporting_stats(db, features: dict):
    print("\n── Writing supporting stats ──")

    upsert_collection(
        db, "age_stats",
        df_to_docs(features["age_stats"])
    )
    upsert_collection(
        db, "delay_distribution",
        df_to_docs(features["delay_dist"])
    )
    upsert_collection(
        db, "assessment_type_distribution",
        df_to_docs(features["type_dist"])
    )

# ══════════════════════════════════════════════════════
#  MASTER WRITE FUNCTION
# ══════════════════════════════════════════════════════

def write_all_to_atlas(
    model: dict,
    features: dict,
    cluster_results: dict
):
    print("\n" + "=" * 55)
    print("  KAYFA — Writing all analytics to MongoDB Atlas")
    print("=" * 55)

    db = get_db()

    write_analytics_summary(db, features)
    write_group_metrics(db, features, model)
    write_course_metrics(db, features, model)
    write_student_risk_scores(db, features)
    write_clusters(db, cluster_results)
    write_concept_failures(db, features)
    write_time_series(db, features)
    write_student_summary(db, model)
    write_supporting_stats(db, features)

    # list all collections + doc counts
    print("\n" + "=" * 55)
    print("  ✅ All data written to Atlas")
    print("=" * 55)
    print(f"\n{'Collection':<35} {'Docs':>8}")
    print("-" * 45)
    for col_name in sorted(db.list_collection_names()):
        count = db[col_name].count_documents({})
        print(f"{col_name:<35} {count:>8,}")

    return db


if __name__ == "__main__":
    dfs             = load_everything()
    cleaned         = clean_all(dfs)
    model           = build_model(cleaned)
    features        = compute_all_features(model)
    cluster_results = run_clustering(model)
    db              = write_all_to_atlas(model, features, cluster_results)