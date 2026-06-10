from load_csvs import load_all_csvs

dfs = load_all_csvs()

for name, df in dfs.items():
    print(f"\n── {name} ──")
    print(df.dtypes)
    print(df.head(2))
    