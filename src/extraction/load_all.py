from .load_csvs import load_all_csvs
from .load_grades_json import load_grades
from .load_attendance_xlsx import load_attendance
def load_everything() -> dict:
    print("=" * 50)
    print("  KAYFA — Loading all data sources")
    print("=" * 50)

    dfs = load_all_csvs()
    dfs["grades"]     = load_grades()
    dfs["attendance"] = load_attendance()

    print("\n" + "=" * 50)
    print("  ✅ All 8 files loaded successfully")
    print("=" * 50)

    # summary table
    print(f"\n{'Source':<20} {'Rows':>8} {'Cols':>6}")
    print("-" * 36)
    for name, df in dfs.items():
        print(f"{name:<20} {df.shape[0]:>8,} {df.shape[1]:>6}")

    return dfs

if __name__ == "__main__":
    data = load_everything()