import pandas as pd
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

def load_grades() -> pd.DataFrame:
    with open(DATA_DIR / "grades.json", "r", encoding="utf-8") as f:
        raw = json.load(f)

    # flatten nested structure
    # كل student عنده array من grades
    # json_normalize بتفرد كل grade في row مستقل
    # وتحط student_id, course_id, group_id في كل row
    df = pd.json_normalize(
        raw,
        record_path="grades",
        meta=["student_id", "course_id", "group_id"],
        errors="raise"
    )

    # رتب الأعمدة بشكل منطقي
    cols = ["student_id", "course_id", "group_id",
            "grade_id", "assessment_id", "assessment_title",
            "type", "score", "max_score", "date"]
    df = df[cols]

    # fix dtypes
    df["score"]    = pd.to_numeric(df["score"],    errors="coerce")
    df["max_score"]= pd.to_numeric(df["max_score"],errors="coerce")
    df["date"]     = pd.to_datetime(df["date"],     errors="coerce")

    print(f"✅ grades.json → {df.shape[0]} rows, {df.shape[1]} cols")
    print(f"   Students with grades : {df['student_id'].nunique()}")
    print(f"   Assessment types     : {df['type'].unique().tolist()}")
    print(f"   Score range          : {df['score'].min()} → {df['score'].max()}")
    print(f"   Null scores          : {df['score'].isna().sum()}")

    return df

if __name__ == "__main__":
    df = load_grades()
    print("\n── Sample ──")
    print(df.head(5).to_string())