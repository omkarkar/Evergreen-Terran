import duckdb

con = duckdb.connect("agri_fin.duckdb")

# rebuild views (reuse the same keys as before)
con.sql("""
CREATE OR REPLACE VIEW stg_climate AS
SELECT
  CAST(country AS TEXT) AS region_key,
  CAST(year    AS INT)  AS year_key,
  *
FROM climate_clean;
""")

con.sql("""
CREATE OR REPLACE VIEW feature_store AS
SELECT
  y.region_key,
  y.year_key,
  y.crop,
  y.target_yield,
  /* soil */
  s.soil_pH, s.soil_soc, s.soil_nitrogen,
  /* weather (annual) */
  c.rain_mm_year,
  COALESCE(c.tavg, (c.tmin + c.tmax)/2.0) AS temp_mean_year
FROM stg_crop_yield y
LEFT JOIN stg_soil s
  ON s.region_key = y.region_key
LEFT JOIN stg_climate c
  ON c.region_key = y.region_key AND c.year_key = y.year_key;
""")

print(con.sql("SELECT * FROM feature_store LIMIT 10").df())

con.sql("""
CREATE OR REPLACE TABLE training_yield AS
SELECT
  region_key, year_key, crop,
  target_yield,
  soil_pH, soil_soc, soil_nitrogen,
  rain_mm_year, temp_mean_year
FROM feature_store
WHERE target_yield IS NOT NULL;
""")

print(con.sql("SELECT COUNT(*) AS rows FROM training_yield").df())

con.sql("COPY (SELECT * FROM training_yield) TO 'training_yield.csv' (HEADER, DELIMITER ',')")
con.sql("COPY (SELECT * FROM training_yield) TO 'training_yield.parquet' (FORMAT PARQUET)")
print(" Rebuilt training_yield with weather added.")
con.close()
