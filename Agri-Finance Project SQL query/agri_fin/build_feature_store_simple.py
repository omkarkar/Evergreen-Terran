import duckdb

con = duckdb.connect("agri_fin.duckdb")

# columns from your inspect_schema output
Y_REGION = "country"
Y_YEAR   = "year"
Y_CROP   = "crop"
S_REGION = "country"

# staging
con.sql(f"""
CREATE OR REPLACE VIEW stg_crop_yield AS
SELECT
  CAST({Y_REGION} AS TEXT) AS region_key,
  CAST({Y_YEAR}   AS INT)  AS year_key,
  LOWER(TRIM({Y_CROP}))    AS crop,
  *,
  yield_t_ha AS target_yield
FROM crop_yield;
""")

con.sql(f"""
CREATE OR REPLACE VIEW stg_soil AS
SELECT
  CAST({S_REGION} AS TEXT) AS region_key,
  *,
  ph_top30_mean      AS soil_pH,
  soc_top30_mean_gkg AS soil_soc,
  nitrogen_top30_mean_gkg AS soil_nitrogen
FROM soil_top30;
""")

# feature store (yield + soil)
con.sql("""
CREATE OR REPLACE VIEW feature_store AS
SELECT
  y.region_key,
  y.year_key,
  y.crop,
  y.target_yield,
  s.soil_pH,
  s.soil_soc,
  s.soil_nitrogen
FROM stg_crop_yield y
LEFT JOIN stg_soil s
  ON s.region_key = y.region_key;
""")

print("\nPreview feature_store:")
print(con.sql("SELECT * FROM feature_store LIMIT 10").df())

# training table
con.sql("""
CREATE OR REPLACE TABLE training_yield AS
SELECT
  region_key, year_key, crop,
  target_yield,
  soil_pH, soil_soc, soil_nitrogen
FROM feature_store
WHERE target_yield IS NOT NULL;
""")

print("\nRows in training_yield:")
print(con.sql("SELECT COUNT(*) AS rows FROM training_yield").df())

# export
con.sql("COPY (SELECT * FROM training_yield) TO 'training_yield.parquet' (FORMAT PARQUET)")
con.sql("COPY (SELECT * FROM training_yield) TO 'training_yield.csv' (HEADER, DELIMITER ',')")

print("\n Exports written: training_yield.parquet, training_yield.csv")
con.close()
