import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# ── كل sheet ليها encoding مختلف للـ status ──────────────────────
# هنعمل mapping لكل sheet عشان نوحّد الـ status في 1 و 0
SHEET_STATUS_MAP = {
    "2025-12": {"attended": 1, "Atttended": 1, "absent": 0},
    "2026-01": {"Present": 1, "Absent": 0},
    "2026-02": {1: 1, 0: 0},          # integers
    "2026-03": {"P": 1, "A": 0},
    "2026-04": {"yes": 1, "no": 0},
    "2026-05": {True: 1, False: 0},   # booleans
}

def _load_single_sheet(xl: pd.ExcelFile, sheet: str) -> pd.DataFrame:
    df = xl.parse(sheet)

    # بعض الـ sheets بتسمي العمود datetime بدل session_datetime
    if "datetime" in df.columns and "session_datetime" not in df.columns:
        df = df.rename(columns={"datetime": "session_datetime"})

    # نوحّد الـ status باستخدام الـ mapping الخاص بكل sheet
    status_map = SHEET_STATUS_MAP[sheet]
    df["status"] = df["status"].map(status_map)

    # نضيف عمود للـ month عشان نعرف مصدر كل row
    df["month"] = sheet

    return df

def load_attendance() -> pd.DataFrame:
    xl = pd.ExcelFile(DATA_DIR / "attendance.xlsx")

    sheets = []
    for sheet in xl.sheet_names:
        df_sheet = _load_single_sheet(xl, sheet)
        sheets.append(df_sheet)
        print(f"   📄 {sheet} → {df_sheet.shape[0]} rows | "
              f"status nulls: {df_sheet['status'].isna().sum()}")

    # stack all 6 sheets into one dataframe
    df = pd.concat(sheets, ignore_index=True)

    # fix dtypes
    df["session_datetime"] = pd.to_datetime(df["session_datetime"], errors="coerce")
    df["status"]           = pd.to_numeric(df["status"], errors="coerce")

    print(f"\n✅ attendance.xlsx → {df.shape[0]} total rows, {df.shape[1]} cols")
    print(f"   Sheets merged        : {df['month'].nunique()}")
    print(f"   Unique students      : {df['student_id'].nunique()}")
    print(f"   Status values        : {sorted(df['status'].dropna().unique().tolist())}")
    print(f"   Status null rows     : {df['status'].isna().sum()}")
    print(f"   Date range           : {df['session_datetime'].min()} → "
          f"{df['session_datetime'].max()}")

    return df

if __name__ == "__main__":
    df = load_attendance()
    print("\n── Sample (one row per sheet) ──")
    print(df.groupby("month").first()[
        ["student_id", "session_type", "status", "session_datetime"]
    ].to_string())