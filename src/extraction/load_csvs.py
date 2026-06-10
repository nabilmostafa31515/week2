import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

def load_courses() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "courses.csv")
    print(f"✅ courses.csv        → {df.shape[0]} rows, {df.shape[1]} cols")
    return df

def load_groups() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "groups.csv")
    print(f"✅ groups.csv         → {df.shape[0]} rows, {df.shape[1]} cols")
    return df

def load_students() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "students.csv")
    print(f"✅ students.csv       → {df.shape[0]} rows, {df.shape[1]} cols")
    return df

def load_concepts_performance() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "concepts_performance.csv")
    print(f"✅ concepts_perf.csv  → {df.shape[0]} rows, {df.shape[1]} cols")
    return df

def load_engagement_events() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "engagement_events.csv")
    print(f"✅ engagement.csv     → {df.shape[0]} rows, {df.shape[1]} cols")
    return df

def load_assignment_submissions() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "assignment_submissions.csv")
    print(f"✅ submissions.csv    → {df.shape[0]} rows, {df.shape[1]} cols")
    return df

def load_all_csvs() -> dict[str, pd.DataFrame]:
    return {
        "courses":      load_courses(),
        "groups":       load_groups(),
        "students":     load_students(),
        "concepts":     load_concepts_performance(),
        "engagement":   load_engagement_events(),
        "submissions":  load_assignment_submissions(),
    }

if __name__ == "__main__":
    dfs = load_all_csvs()
    print("\n📦 All CSVs loaded successfully.")