import duckdb
con = duckdb.connect("agri_fin.duckdb")
print(con.sql("PRAGMA table_info('climate_clean')").df())
print("\nSample rows:")
print(con.sql("SELECT * FROM climate_clean LIMIT 5").df())
con.close()
