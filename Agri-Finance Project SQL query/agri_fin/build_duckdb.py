import duckdb, pandas as pd
from pathlib import Path

DB = "agri_fin.duckdb"
DATA = Path("data")
con = duckdb.connect(DB)

def load_csv(table, filename):
    path = DATA / filename
    print(f"[CSV] {path.name} -> {table}")
    con.execute(f"""
        CREATE OR REPLACE TABLE {table} AS
        SELECT * FROM read_csv_auto('{path.as_posix()}', IGNORE_ERRORS=true);
    """)

def load_xlsx(table, filename, sheet=0):
    path = DATA / filename
    print(f"[XLSX] {path.name} (sheet={sheet}) -> {table}")
    df = pd.read_excel(path, sheet_name=sheet)
    con.register("tmp_df", df)
    con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM tmp_df;")
    con.unregister("tmp_df")

# ---- your exact files (from Get-ChildItem) ----
load_csv ("agri_finance_merged",         "AgriFinance_Merged_Final.csv")
load_xlsx("crop_yield",                  "Merged_Crop_Yield_Data.xlsx")
load_xlsx("soil_top30",                  "SoilGrids_Asia_AllCountries_top30.xlsx")
load_xlsx("climate_nasa_power",          "nasa_power_annual_2013_2023_asia_locations.xlsx")  # <-- XLSX
load_xlsx("fertilizer_price_use",        "Merged_Fertilizer_Use_Price_Data.xlsx")
load_xlsx("trade_asia",                  "Merged_Trade_Data_Asia.xlsx")
load_csv ("wdi_agri_valueadded",         "WDI_Agri_ValueAdded_Clean.csv")
load_csv ("imf_fas_clean",               "IMF_FAS_Clean.csv")  # <-- name you actually have

print("\n Tables loaded:")
print(con.sql("SHOW TABLES").df())

con.close()
print(f"\nDuckDB database created: {DB}")
