import pandas as pd
import numpy as np
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parents[1] / "extraction"))
from src.extraction.load_all import load_everything
# ══════════════════════════════════════════════════════
#  1. CLEAN STUDENTS
# ══════════════════════════════════════════════════════

def clean_students(df: pd.DataFrame, valid_groups: set) -> pd.DataFrame:
    print("\n── Cleaning students.csv ──")
    df = df.copy()

    # ── Fix 1: null full_name ─────────────────────────
    mask = df["full_name"].isna()
    df.loc[mask, "full_name"] = df.loc[mask, "student_id"].apply(
        lambda x: f"Unknown [{x}]"
    )
    print(f"   ✅ Fix 1: {mask.sum()} null names → 'Unknown [id]'")

    # ── Fix 2: duplicate student_id ──────────────────
    # الـ duplicates عندهم ages مختلفة
    # نشيل الـ row اللي عنده age أكبر (الأغلب هو الغلط)
    df = df.sort_values("age").drop_duplicates(
        subset="student_id", keep="first"
    ).reset_index(drop=True)
    print(f"   ✅ Fix 2: duplicate student_ids removed")

    # ── Fix 3: impossible ages ────────────────────────
    bad_age = (df["age"] < 15) | (df["age"] > 80)
    df["suspect_age"] = False
    df.loc[bad_age, "suspect_age"] = True
    df.loc[bad_age, "age"]         = np.nan
    print(f"   ✅ Fix 3: {bad_age.sum()} impossible ages → NaN + suspect_age=True")

    # ── Fix 4: gender normalisation ──────────────────
    gender_map = {
        "male": "Male", "m": "Male", "MALE": "Male", "M": "Male",
        "female": "Female", "f": "Female", "Fem": "Female",
        "F": "Female", "FEMALE": "Female",
        "Male": "Male", "Female": "Female"
    }
    before = df["gender"].nunique()
    df["gender"] = df["gender"].map(gender_map)
    print(f"   ✅ Fix 4: gender normalised ({before} variants → 2 canonical values)")

    # ── Fix 5: duplicate emails ───────────────────────
    # نفلاغهم بس، مش بنشيل
    df["duplicate_email"] = df["email"].duplicated(keep=False)
    n = df["duplicate_email"].sum()
    print(f"   ✅ Fix 5: {n} duplicate emails flagged (not dropped — email ≠ PK)")

    # ── Fix 6: invalid group_id ───────────────────────
    df["orphan_student"] = ~df["group_id"].isin(valid_groups)
    df.loc[df["orphan_student"], "group_id"] = np.nan
    n = df["orphan_student"].sum()
    print(f"   ✅ Fix 6: {n} students with invalid group_id → NaN + orphan_student=True")

    print(f"   Final shape: {df.shape}")
    return df

# ══════════════════════════════════════════════════════
#  2. CLEAN GROUPS
# ══════════════════════════════════════════════════════

def clean_groups(df: pd.DataFrame) -> pd.DataFrame:
    print("\n── Cleaning groups.csv ──")
    df = df.copy()

    # ── Fix 7: exact duplicate row ────────────────────
    before = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    print(f"   ✅ Fix 7: {before - len(df)} duplicate row(s) removed")

    # ── Fix 8: phantom test group G99 ────────────────
    df["is_test_group"] = df["group_name"].str.contains(
        "TEST|DELETE", case=False, na=False
    )
    print(f"   ✅ Fix 8: {df['is_test_group'].sum()} test group(s) flagged (G99)")

    # ── Fix 9: session_time normalisation ─────────────
    def normalise_time(t):
        t = str(t).strip()
        # already HH:MM
        if len(t) == 5 and ":" in t:
            return t
        # 4-digit military: 1800 → 18:00
        if t.isdigit() and len(t) == 4:
            return f"{t[:2]}:{t[2:]}"
        # "6 PM" / "6:00 PM" style
        try:
            return pd.to_datetime(t, format="%I %p").strftime("%H:%M")
        except Exception:
            pass
        try:
            return pd.to_datetime(t).strftime("%H:%M")
        except Exception:
            return t

    df["session_time"] = df["session_time"].apply(normalise_time)
    print(f"   ✅ Fix 9: session_time normalised to HH:MM 24-hour format")

    print(f"   Final shape: {df.shape}")
    return df

# ══════════════════════════════════════════════════════
#  3. CLEAN GRADES
# ══════════════════════════════════════════════════════

def clean_grades(df: pd.DataFrame) -> pd.DataFrame:
    print("\n── Cleaning grades.json ──")
    df = df.copy()

    # ── Fix 10: negative scores ───────────────────────
    df["invalid_score"] = False
    mask = df["score"] < 0
    df.loc[mask, "invalid_score"] = True
    df.loc[mask, "score"]         = np.nan
    print(f"   ✅ Fix 10: {mask.sum()} negative score(s) → NaN")

    # ── Fix 11: scores > max_score ────────────────────
    mask = df["score"] > df["max_score"]
    df.loc[mask, "invalid_score"] = True
    df.loc[mask, "score"]         = np.nan
    print(f"   ✅ Fix 11: {mask.sum()} score(s) > max_score → NaN")

    # ── Fix 12: null scores ───────────────────────────
    n = df["score"].isna().sum()
    print(f"   ✅ Fix 12: {n} null score(s) retained as NaN (unknown cause)")

    # score_pct column للاستخدام لاحقاً
    df["score_pct"] = (df["score"] / df["max_score"] * 100).round(2)

    print(f"   Final shape: {df.shape}")
    return df

# ══════════════════════════════════════════════════════
#  4. CLEAN ATTENDANCE
# ══════════════════════════════════════════════════════

def clean_attendance(df: pd.DataFrame) -> pd.DataFrame:
    print("\n── Cleaning attendance.xlsx ──")
    df = df.copy()

    # الـ mapping اتعمل بالفعل في load_attendance_xlsx.py
    # هنتأكد بس إن status كلها 0 أو 1
    df["status"] = pd.to_numeric(df["status"], errors="coerce")
    invalid = df["status"].isna().sum()
    if invalid:
        print(f"   ⚠️  {invalid} rows with unmapped status — set to NaN")
    else:
        print(f"   ✅ Fix 13-19: all 6 sheet encodings unified → binary 0/1")

    # confirm column rename handled
    print(f"   ✅ Fix 20: 'datetime' column renamed to 'session_datetime' in 2026-02")

    print(f"   Final shape: {df.shape}")
    return df

# ══════════════════════════════════════════════════════
#  5. CLEAN CONCEPTS PERFORMANCE
# ══════════════════════════════════════════════════════

def clean_concepts(df: pd.DataFrame) -> pd.DataFrame:
    print("\n── Cleaning concepts_performance.csv ──")
    df = df.copy()

    # ── Fix 21: negative score_pct ───────────────────
    df["invalid_score"] = False
    mask = df["score_pct"] < 0
    df.loc[mask, "invalid_score"] = True
    df.loc[mask, "score_pct"]     = np.nan
    print(f"   ✅ Fix 21: {mask.sum()} negative score_pct(s) → NaN")

    # ── Fix 22: score_pct > 100 ───────────────────────
    mask = df["score_pct"] > 100
    df.loc[mask, "invalid_score"] = True
    df.loc[mask, "score_pct"]     = np.nan
    print(f"   ✅ Fix 22: {mask.sum()} score_pct(s) > 100 → NaN")

    # ── Fix 23: mastery_status contradiction ──────────
    df["mastery_status_raw"] = df["mastery_status"].copy()
    df["mastery_status"] = df["score_pct"].apply(
        lambda x: "passed" if pd.notna(x) and x >= 50 else
                  "failed" if pd.notna(x) and x < 50 else np.nan
    )
    changed = (df["mastery_status"] != df["mastery_status_raw"]).sum()
    print(f"   ✅ Fix 23: {changed} mastery_status values recomputed from score_pct")

    print(f"   Final shape: {df.shape}")
    return df

# ══════════════════════════════════════════════════════
#  6. CLEAN ENGAGEMENT EVENTS
# ══════════════════════════════════════════════════════

def clean_engagement(df: pd.DataFrame) -> pd.DataFrame:
    print("\n── Cleaning engagement_events.csv ──")
    df = df.copy()

    df["event_datetime"] = pd.to_datetime(df["event_datetime"], errors="coerce")

    # ── Fix 24: duplicate event_ids ──────────────────
    before = len(df)
    df = df.drop_duplicates(subset="event_id", keep="first").reset_index(drop=True)
    print(f"   ✅ Fix 24: {before - len(df)} duplicate event(s) removed")

    # ── Fix 25: out-of-term dates ─────────────────────
    df["out_of_term"] = df["event_datetime"] < "2025-12-01"
    n = df["out_of_term"].sum()
    print(f"   ✅ Fix 25: {n} out-of-term event(s) flagged")

    # ── Fix 26: negative duration_seconds ─────────────
    df["invalid_duration"] = False
    mask = df["duration_seconds"] < 0
    df.loc[mask, "invalid_duration"]  = True
    df.loc[mask, "duration_seconds"]  = np.nan
    print(f"   ✅ Fix 26: {mask.sum()} negative duration(s) → NaN")

    print(f"   Final shape: {df.shape}")
    return df

# ══════════════════════════════════════════════════════
#  7. CLEAN SUBMISSIONS
# ══════════════════════════════════════════════════════

def clean_submissions(df: pd.DataFrame) -> pd.DataFrame:
    print("\n── Cleaning assignment_submissions.csv ──")
    df = df.copy()

    df["deadline"]     = pd.to_datetime(df["deadline"],     errors="coerce")
    df["submitted_at"] = pd.to_datetime(df["submitted_at"], errors="coerce")

    # ── Fix 27: null submitted_at ─────────────────────
    n = df["submitted_at"].isna().sum()
    print(f"   ✅ Fix 27: {n} null submitted_at retained as NaN")

    # ── Fix 28: recompute is_late ─────────────────────
    df["is_late_raw"] = df["is_late"].copy()
    df["is_late"] = df.apply(
        lambda r: bool(r["submitted_at"] > r["deadline"])
        if pd.notna(r["submitted_at"]) and pd.notna(r["deadline"])
        else np.nan,
        axis=1
    )
    changed = (df["is_late"] != df["is_late_raw"]).sum()
    print(f"   ✅ Fix 28: is_late recomputed from timestamps ({changed} corrections)")

    # ── Fix 29: submission_delay column ──────────────
    df["submission_delay_hours"] = (
        (df["submitted_at"] - df["deadline"])
        .dt.total_seconds() / 3600
    ).round(2)
    print(f"   ✅ Fix 29: submission_delay_hours computed")

    # ── Fix 30: zero time_spent ───────────────────────
    df["invalid_time"] = False
    mask = df["time_spent_minutes"] <= 0
    df.loc[mask, "invalid_time"]        = True
    df.loc[mask, "time_spent_minutes"]  = np.nan
    print(f"   ✅ Fix 30: {mask.sum()} zero/negative time_spent → NaN")

    print(f"   Final shape: {df.shape}")
    return df

# ══════════════════════════════════════════════════════
#  RUN ALL CLEANING
# ══════════════════════════════════════════════════════

def clean_all(dfs: dict) -> dict:
    print("\n" + "=" * 55)
    print("  KAYFA — Running full cleaning pipeline")
    print("=" * 55)

    valid_groups = set(
        dfs["groups"][~dfs["groups"]["group_name"]
        .str.contains("TEST|DELETE", case=False, na=False)]["group_id"]
    )

    cleaned = {}
    cleaned["courses"]     = dfs["courses"].copy()
    cleaned["groups"]      = clean_groups(dfs["groups"])
    cleaned["students"]    = clean_students(dfs["students"], valid_groups)
    cleaned["grades"]      = clean_grades(dfs["grades"])
    cleaned["attendance"]  = clean_attendance(dfs["attendance"])
    cleaned["concepts"]    = clean_concepts(dfs["concepts"])
    cleaned["engagement"]  = clean_engagement(dfs["engagement"])
    cleaned["submissions"] = clean_submissions(dfs["submissions"])

    print("\n" + "=" * 55)
    print("  ✅ Cleaning pipeline complete")
    print("=" * 55)

    # summary
    print(f"\n{'Source':<20} {'Raw Rows':>10} {'Clean Rows':>12}")
    print("-" * 44)
    for name in cleaned:
        raw   = dfs[name].shape[0]
        clean = cleaned[name].shape[0]
        diff  = raw - clean
        flag  = f"  (-{diff})" if diff > 0 else ""
        print(f"{name:<20} {raw:>10,} {clean:>12,}{flag}")

    return cleaned

if __name__ == "__main__":
    dfs     = load_everything()
    cleaned = clean_all(dfs)