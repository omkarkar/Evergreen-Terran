import pandas as pd, duckdb, re
from pathlib import Path

RAW_XLSX = Path("data") / "nasa_power_annual_2013_2023_asia_locations.xlsx"
CLEAN_CSV = Path("data") / "climate_nasa_power_clean.csv"

# load with no header, well detect it
df0 = pd.read_excel(RAW_XLSX, header=None)

# find header row (contains something like country + year)
header_row = None
for i in range(min(10, len(df0))):
    row_vals = [str(x).strip().lower() for x in df0.iloc[i].tolist()]
    if any("country" in v for v in row_vals) and any(v in ("year","yr","year_","calendar_year") for v in row_vals):
        header_row = i
        break

if header_row is None:
    # fallback: assume first non-empty row is header
    header_row = 0

# promote header
df = pd.read_excel(RAW_XLSX, header=header_row)
# drop unnamed columns
df = df.loc[:, ~df.columns.astype(str).str.match(r"^unnamed", flags=re.I)]
# strip whitespace from col names
df.columns = [str(c).strip() for c in df.columns]

# try to identify key columns
def pick(cands):
    for c in cands:
        if c in df.columns:
            return c
    return None

country_col = pick(["country","Country","COUNTRY","nation"])
year_col    = pick(["year","Year","YEAR","yr","YR","calendar_year"])

# NASA-like fields (annual)
rain_col = pick(["PRECTOTCORR","prectotcorr","Rainfall","rainfall_mm","rain_mm","precip_mm"])
tavg_col = pick(["T2M","t2m","tavg","TAVG"])
tmin_col = pick(["T2M_MIN","t2m_min","tmin","TMIN"])
tmax_col = pick(["T2M_MAX","t2m_max","tmax","TMAX"])

if not country_col or not year_col:
    raise SystemExit(f" Could not detect country/year columns. Found columns: {df.columns.tolist()}")

# build standardized frame
out = pd.DataFrame()
out["country"] = df[country_col].astype(str).str.strip()
out["year"]    = pd.to_numeric(df[year_col], errors="coerce").astype("Int64")

if rain_col: out["rain_mm_year"] = pd.to_numeric(df[rain_col], errors="coerce")
if tavg_col: out["tavg"]         = pd.to_numeric(df[tavg_col], errors="coerce")
if tmin_col: out["tmin"]         = pd.to_numeric(df[tmin_col], errors="coerce")
if tmax_col: out["tmax"]         = pd.to_numeric(df[tmax_col], errors="coerce")

# drop rows without year or country
out = out.dropna(subset=["country","year"])

# save cleaned CSV
out.to_csv(CLEAN_CSV, index=False)
print(f" Cleaned climate saved -> {CLEAN_CSV}")

# load into DuckDB
con = duckdb.connect("agri_fin.duckdb")
con.execute(f"CREATE OR REPLACE TABLE climate_clean AS SELECT * FROM read_csv_auto('{CLEAN_CSV.as_posix()}', IGNORE_ERRORS=true);")
print(con.execute("SELECT * FROM climate_clean LIMIT 5").fetchdf())
con.close()
