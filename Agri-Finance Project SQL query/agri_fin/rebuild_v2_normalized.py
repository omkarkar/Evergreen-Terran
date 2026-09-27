import duckdb

con = duckdb.connect("agri_fin.duckdb")

# 1 Normalize crop_yield: if unit says kg/ha, divide by 1000, else keep.
con.sql("""
CREATE OR REPLACE VIEW stg_crop_yield_norm AS
SELECT
  CAST(country AS TEXT) AS region_key,
  CAST(year    AS INT)  AS year_key,
  LOWER(TRIM(crop))     AS crop,
  unit,
  CASE
    WHEN lower(coalesce(unit,'')) LIKE 'kg%' THEN yield_t_ha / 1000.0
    ELSE yield_t_ha
  END AS target_yield_t_ha
FROM crop_yield;
""")

# 2 Rebuild base joins using normalized target
con.sql("""
CREATE OR REPLACE VIEW feature_store_v2 AS
WITH base AS (
  SELECT
    y.region_key, y.year_key, y.crop,
    y.target_yield_t_ha AS target_yield,
    s.ph_top30_mean            AS soil_pH,
    s.soc_top30_mean_gkg       AS soil_soc,
    s.nitrogen_top30_mean_gkg  AS soil_nitrogen,
    c.rain_mm_year, c.temp_mean_year
  FROM stg_crop_yield_norm y
  LEFT JOIN soil_top30 s ON s.country = y.region_key
  LEFT JOIN climate_clean c ON c.country = y.region_key AND c.year = y.year_key
)
SELECT
  b.*,
  f.fert_index,
  i.* EXCLUDE (region_key, year_key),
  w.wdi_agri_value_added
FROM base b
LEFT JOIN stg_fertilizer f ON f.region_key = b.region_key AND f.year_key = b.year_key
LEFT JOIN stg_imf       i ON i.region_key = b.region_key AND i.year_key = b.year_key
LEFT JOIN stg_wdi       w ON w.region_key = b.region_key AND w.year_key = b.year_key;
""")

# 3 Re-export training set
con.sql("CREATE OR REPLACE TABLE training_yield_v2 AS SELECT * FROM feature_store_v2 WHERE target_yield IS NOT NULL;")
con.sql("COPY (SELECT * FROM training_yield_v2) TO 'training_yield_v2.csv' (HEADER, DELIMITER ',');")
con.sql("COPY (SELECT * FROM training_yield_v2) TO 'training_yield_v2.parquet' (FORMAT PARQUET);")

print(' Rebuilt training_yield_v2 with normalized target (t/ha).')
con.close()
