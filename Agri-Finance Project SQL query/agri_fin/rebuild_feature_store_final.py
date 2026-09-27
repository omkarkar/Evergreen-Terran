import pandas as pd, duckdb
from pathlib import Path

RAW_XLSX = Path("data") / "nasa_power_annual_2013_2023_asia_locations.xlsx"
CLEAN_CSV = Path("data") / "climate_nasa_power_clean.csv"

# Load with headers (they're already correct)
df = pd.read_excel(RAW_XLSX, header=0)

# Keep only the columns we need
df = df[["country", "year", "t2m_mean_c", "precip_total_mm"]].copy()
df.rename(columns={
    "t2m_mean_c": "temp_mean_year",
    "precip_total_mm": "rain_mm_year"
}, inplace=True)

# Drop missing values
df = df.dropna(subset=["country", "year"])

# Save cleaned CSV
df.to_csv(CLEAN_CSV, index=False)
print(f" Cleaned climate saved -> {CLEAN_CSV}")

# Load into DuckDB
con = duckdb.connect("agri_fin.duckdb")
con.execute(f"""
CREATE OR REPLACE TABLE climate_clean AS
SELECT * FROM read_csv_auto('{CLEAN_CSV.as_posix()}', IGNORE_ERRORS=true);
""")
print(" Loaded climate_clean table:")
print(con.execute("SELECT * FROM climate_clean LIMIT 5").fetchdf())

# Create stg_climate view
con.execute("""
CREATE OR REPLACE VIEW stg_climate AS
SELECT
  CAST(country AS TEXT) AS region_key,
  CAST(year AS INT) AS year_key,
  rain_mm_year,
  temp_mean_year
FROM climate_clean;
""")

# Rebuild feature_store with yield + soil + climate
con.execute("""
CREATE OR REPLACE VIEW feature_store AS
SELECT
  y.region_key,
  y.year_key,
  y.crop,
  y.target_yield,
  s.soil_pH,
  s.soil_soc,
  s.soil_nitrogen,
  c.rain_mm_year,
  c.temp_mean_year
FROM stg_crop_yield y
LEFT JOIN stg_soil s
  ON s.region_key = y.region_key
LEFT JOIN stg_climate c
  ON c.region_key = y.region_key AND c.year_key = y.year_key;
""")

print("\n Feature store preview:")
print(con.execute("SELECT * FROM feature_store LIMIT 10").fetchdf())

# Create final training table
con.execute("""
CREATE OR REPLACE TABLE training_yield AS
SELECT
  region_key, year_key, crop,
  target_yield,
  soil_pH, soil_soc, soil_nitrogen,
  rain_mm_year, temp_mean_year
FROM feature_store
WHERE target_yield IS NOT NULL;
""")

print("\n Training table row count:")
print(con.execute("SELECT COUNT(*) AS rows FROM training_yield").fetchdf())

# Export
con.execute("COPY (SELECT * FROM training_yield) TO 'training_yield.csv' (HEADER, DELIMITER ',')")
con.execute("COPY (SELECT * FROM training_yield) TO 'training_yield.parquet' (FORMAT PARQUET)")

print("\n Rebuilt training_yield.csv and training_yield.parquet with climate data.")
con.close()
