import duckdb
import pandas as pd
from pathlib import Path

DB = "agri_fin.duckdb"
con = duckdb.connect(DB)

def cols(t):
    return con.sql(f"PRAGMA table_info('{t}')").df()["name"].tolist()

def pick(cands, pool):
    for c in cands:
        if c in pool: return c
    return None

# ------ source tables you already loaded ------
t_y   = "crop_yield"
t_soil= "soil_top30"
t_cli = "climate_clean"           # from your cleaned NASA file
t_fert= "fertilizer_price_use"    # your fertilizer sheet
t_imf = "imf_fas_clean"           # IMF Financial Access
t_wdi = "wdi_agri_valueadded"     # WDI agri value added

# ------ detect keys in base tables ------
yc, sc, cc = cols(t_y), cols(t_soil), cols(t_cli)
fertc, imfc, wdic = cols(t_fert), cols(t_imf), cols(t_wdi)

y_region = pick(["country","Country","region","Region"], yc)
y_year   = pick(["year","Year","calendar_year"], yc)
y_crop   = pick(["crop","Crop","commodity","Commodity"], yc)

s_region = pick(["country","Country","region","Region"], sc)

c_region = pick(["country","Country","region","Region"], cc)
c_year   = pick(["year","Year","calendar_year"], cc)

assert y_region and y_year, "Could not find region/year in crop_yield"
assert s_region, "Could not find region in soil_top30"

# ------ create stage views for base ------
con.sql(f"""
CREATE OR REPLACE VIEW stg_crop_yield AS
SELECT
  CAST({y_region} AS TEXT) AS region_key,
  CAST({y_year}   AS INT)  AS year_key,
  LOWER(TRIM({y_crop}))    AS crop,
  *,
  yield_t_ha AS target_yield
FROM {t_y};
""")

con.sql(f"""
CREATE OR REPLACE VIEW stg_soil AS
SELECT
  CAST({s_region} AS TEXT) AS region_key,
  ph_top30_mean              AS soil_pH,
  soc_top30_mean_gkg         AS soil_soc,
  nitrogen_top30_mean_gkg    AS soil_nitrogen
FROM {t_soil};
""")

if c_region and c_year:
    con.sql(f"""
    CREATE OR REPLACE VIEW stg_climate AS
    SELECT
      CAST({c_region} AS TEXT) AS region_key,
      CAST({c_year}   AS INT)  AS year_key,
      rain_mm_year,
      temp_mean_year
    FROM {t_cli};
    """)
else:
    con.sql("""CREATE OR REPLACE VIEW stg_climate AS
               SELECT NULL::TEXT AS region_key, NULL::INT AS year_key,
                      NULL::DOUBLE AS rain_mm_year, NULL::DOUBLE AS temp_mean_year
            """)

# ------ fertilizer feature detection (robust) ------
fert_region = pick(["country","Country","region","Region"], fertc)
fert_year   = pick(["year","Year","calendar_year"], fertc)

fert_num = [c for c in fertc if c not in (fert_region, fert_year) ]  # candidates
# common names you might have
fert_pref = ["fertilizer_price_index","fert_price_index","fert_index",
             "fertilizer_use_kg_ha","fert_use_kg_ha","N_use_kg_ha","P2O5_use_kg_ha","K2O_use_kg_ha"]

# pick best available as a single composite feature
chosen = None
for c in fert_pref:
    if c in fertc:
        chosen = c; break

if not chosen:
    # fallback: average of any numeric-ish columns that look fertilizer-related
    # well build it dynamically in SQL
    fert_like = [c for c in fert_num if any(x in c.lower() for x in ["fert","n_","k2o","p2o5","price","use"])]
    fert_expr = "NULL" if not fert_like else "("+ " + ".join([f"TRY_CAST({c} AS DOUBLE)" for c in fert_like]) + f")/{len(fert_like)}"
else:
    fert_expr = f"TRY_CAST({chosen} AS DOUBLE)"

if fert_region and fert_year:
    con.sql(f"""
    CREATE OR REPLACE VIEW stg_fertilizer AS
    SELECT
      CAST({fert_region} AS TEXT) AS region_key,
      CAST({fert_year}   AS INT)  AS year_key,
      {fert_expr} AS fert_index
    FROM {t_fert};
    """)
else:
    con.sql("""CREATE OR REPLACE VIEW stg_fertilizer AS
               SELECT NULL::TEXT AS region_key, NULL::INT AS year_key, NULL::DOUBLE AS fert_index
            """)

# ------ IMF FAS & WDI detection (optional, robust) ------
# IMF: try a couple of meaningful numeric columns
imf_region = pick(["country","Country","economy","Economy"], imfc)
imf_year   = pick(["year","Year","calendar_year"], imfc)
imf_candidates = [c for c in imfc if c not in (imf_region, imf_year)]
imf_like = [c for c in imf_candidates if any(k in c.lower() for k in ["branch","atm","accounts","credit","loans","deposit","per_"])]
imf_take = imf_like[:2]  # take up to 2 columns
if imf_region and imf_year and imf_take:
    imf_select = ", ".join([f"TRY_CAST({c} AS DOUBLE) AS imf_{c}" for c in imf_take])
    con.sql(f"""
    CREATE OR REPLACE VIEW stg_imf AS
    SELECT
      CAST({imf_region} AS TEXT) AS region_key,
      CAST({imf_year}   AS INT)  AS year_key,
      {imf_select}
    FROM {t_imf};
    """)
else:
    con.sql("""CREATE OR REPLACE VIEW stg_imf AS
               SELECT NULL::TEXT AS region_key, NULL::INT AS year_key
            """)

# WDI: try a main value column (e.g., agri value added %)
wdi_region = pick(["country","Country","economy","Economy"], wdic)
wdi_year   = pick(["year","Year","calendar_year"], wdic)
wdi_value  = pick(["value","Value","val","AGRI_VALUE_ADDED","agri_value_added","agri_value_added_percent"], wdic)
if wdi_region and wdi_year and wdi_value:
    con.sql(f"""
    CREATE OR REPLACE VIEW stg_wdi AS
    SELECT
      CAST({wdi_region} AS TEXT) AS region_key,
      CAST({wdi_year}   AS INT)  AS year_key,
      TRY_CAST({wdi_value} AS DOUBLE) AS wdi_agri_value_added
    FROM {t_wdi};
    """)
else:
    con.sql("""CREATE OR REPLACE VIEW stg_wdi AS
               SELECT NULL::TEXT AS region_key, NULL::INT AS year_key, NULL::DOUBLE AS wdi_agri_value_added
            """)

# ------ feature_store_v2 (join everything) ------
con.sql("""
CREATE OR REPLACE VIEW feature_store_v2 AS
WITH base AS (
  SELECT
    y.region_key,
    y.year_key,
    y.crop,
    y.target_yield,
    s.soil_pH, s.soil_soc, s.soil_nitrogen,
    c.rain_mm_year, c.temp_mean_year
  FROM stg_crop_yield y
  LEFT JOIN stg_soil s     ON s.region_key = y.region_key
  LEFT JOIN stg_climate c  ON c.region_key = y.region_key AND c.year_key = y.year_key
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

# preview & export training set v2
print(con.sql("SELECT * FROM feature_store_v2 LIMIT 10").df())

con.sql("""
CREATE OR REPLACE TABLE training_yield_v2 AS
SELECT *
FROM feature_store_v2
WHERE target_yield IS NOT NULL;
""")

con.sql("COPY (SELECT * FROM training_yield_v2) TO 'training_yield_v2.csv' (HEADER, DELIMITER ',')")
con.sql("COPY (SELECT * FROM training_yield_v2) TO 'training_yield_v2.parquet' (FORMAT PARQUET)")
print(" Wrote training_yield_v2.csv & training_yield_v2.parquet")
con.close()
