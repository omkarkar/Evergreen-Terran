import duckdb
con = duckdb.connect("agri_fin.duckdb")

def show(table):
    print(f"\n--- {table} ---")
    print(con.sql(f"PRAGMA table_info('{table}')").df())

for t in ["crop_yield","climate_nasa_power","soil_top30"]:
    show(t)

con.close()
