import duckdb, pandas as pd

con = duckdb.connect("agri_fin.duckdb")

def cols(table):
    return [r[0] for r in con.sql(f"PRAGMA table_info('{table}')").fetchall()]

def pick(cands, cols_list):
    for c in cands:
        if c in cols_list:
            return c
    return None

REG  = ["region_id","region","Region","REGION","district","District","state","State","admin_name","ADM2_EN","ADM1_EN","country","Country"]
YEAR = ["year","Year","YEAR","harvest_year","HarvestYear","calendar_year"]
CROP = ["crop","Crop","commodity","Commodity"]

yc, cc, sc = cols("crop_yield"), cols("climate_nasa_power"), cols("soil_top30")

y_region = pick(REG, yc);  y_year = pick(YEAR, yc);  y_crop = pick(CROP, yc)
c_region = pick(REG, cc);  c_year = pick(YEAR, cc)
s_region = pick(REG, sc)

assert y_region and y_year, f"Need region/year in crop_yield; found: region={y_region}, year={y_year}. Run PRAGMA to see actual names."

print(f"Detected keys -> crop_yield: region={y_region}, year={y_year}, crop={y_crop}")
print(f"Detected keys -> climate:    region={c_region}, year={c_year}")
print(f"Detected keys -> soil:       region={s_region}")

# staging views
con.sql(f"""
CREATE OR REPLACE VIEW stg_crop_yield AS
SELECT
  CAST({y_region} AS TEXT) AS region_key,
  CAST({y_year}   AS INT)  AS year_key,
  { (f"LOWER(TRIM({y_crop})) AS crop,") if y_crop else "NULL AS crop," }
  *,
  COALESCE(yield_t_per_ha, production_tonnes * 1.0 / NULLIF(area_harvested,0)) AS target_yield
FROM crop_yield;
""")

if c_region and c_year:
    con.sql(f"""
    CREATE OR REPLACE VIEW stg_climate AS
    SELECT
      CAST({c_region} AS TEXT) AS region_key,
      CAST({c_year}   AS INT)  AS year_key,
      *
    FROM climate_nasa_power;
    """)
else:
    con.sql("CREATE OR REPLACE VIEW stg_climate AS SELECT NULL::TEXT AS region_key, NULL::INT AS year_key;")

if s_region:
    con.sql(f"""
    CREATE OR REPLACE VIEW stg_soil AS
    SELECT
      CAST({s_region} AS TEXT) AS region_key,
      *
    FROM soil_top30;
    """)
else:
    con.sql("CREATE OR REPLACE VIEW stg_soil AS SELECT NULL::TEXT AS region_key;")

# feature store
con.sql("""
CREATE OR REPLACE VIEW feature_store AS
SELECT
  y.region_key,
  y.year_key,
  y.crop,
  y.target_yield,
  AVG(c.rainfall_mm)                                     AS rain_total_year,
  AVG(COALESCE(c.tavg, (c.tmax + c.tmin)/2.0))           AS temp_mean_year,
  AVG(s.pH)                                              AS soil_pH,
  AVG(COALESCE(s.SOC, s.soc, s.org_carbon))              AS soil_soc
FROM stg_crop_yield y
LEFT JOIN stg_climate c
  ON c.region_key = y.region_key AND c.year_key = y.year_key
LEFT JOIN stg_soil s
  ON s.region_key = y.region_key
GROUP BY 1,2,3,4;
""")

print("\nPreview feature_store:")
print(con.sql("SELECT * FROM feature_store LIMIT 10").df())

# training set
con.sql("""
CREATE OR REPLACE TABLE training_yield AS
SELECT
  region_key, year_key, crop,
  target_yield,
  rain_total_year, temp_mean_year, soil_pH, soil_soc
FROM feature_store
WHERE target_yield IS NOT NULL;
""")

print("\nRows in training_yield:")
print(con.sql("SELECT COUNT(*) AS rows FROM training_yield").df())

con.sql("COPY (SELECT * FROM training_yield) TO 'training_yield.parquet' (FORMAT PARQUET)")
con.sql("COPY (SELECT * FROM training_yield) TO 'training_yield.csv' (HEADER, DELIMITER ',')")
print("\n Exports written: training_yield.parquet, training_yield.csv")

con.close()
