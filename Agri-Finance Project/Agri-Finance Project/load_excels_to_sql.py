import os
import pandas as pd
from sqlalchemy import text
from db_engine import engine

# Map Excel filenames to existing Postgres tables
FILE_TABLE_MAP = {
    "asia_allcountries_153crops_COP_usd_per_ha_2013_2023_no_seed.xlsx":
        "asia_allcountries_153crops_cop_usd_per_ha_2013_2023_no_seed",
    "asia_wide_standardized_price_master final.xlsx":
        "asia_wide_standardized_price_master final",
    "fertilizer_clean.xlsx":
        "fertilizer_clean",
    "nasa_power_asia_annual_clean.xlsx":
        "nasa_power_asia_annual_clean",
    "Seed_Cost_Per_Hector_cleaned (1).xlsx":
        "Seed_Cost_Per_Hector_cleaned (1)",
    "soilgrids_asia_top30_clean.xlsx":
        "soilgrids_asia_top30_clean",
    "Yield data.xlsx":
        "Yield data",
}

DATA_DIR = "data"


def load_single_excel(file_name: str, table_name: str):
    file_path = os.path.join(DATA_DIR, file_name)

    if not os.path.exists(file_path):
        print(f"⚠️ File not found, skipping: {file_path}")
        return

    print(f"Loading {file_name} into {table_name} ...")

    # Read Excel
    df = pd.read_excel(file_path)

    # Empty existing data but keep table + views
    with engine.begin() as conn:
        # Quote table name if it has spaces / capitals
        conn.execute(text(f'TRUNCATE TABLE "{table_name}"'))

    # Append new data
    df.to_sql(table_name, engine, if_exists="append", index=False)

    print(f"✅ Loaded {len(df)} rows into {table_name}")


def refresh_materialized_views():
    """Refresh the derived model layers after base tables are updated."""
    print("🔄 Refreshing materialized views ...")
    with engine.begin() as conn:
        conn.execute(text("REFRESH MATERIALIZED VIEW yield_panel;"))
        conn.execute(text("REFRESH MATERIALIZED VIEW crop_cop_per_ha;"))
        conn.execute(text("REFRESH MATERIALIZED VIEW agri_master_panel;"))
    print("✅ Materialized views refreshed.")


def load_all_excels():
    for file_name, table_name in FILE_TABLE_MAP.items():
        load_single_excel(file_name, table_name)

    # After all raw tables updated, refresh model layers
    refresh_materialized_views()


if __name__ == "__main__":
    load_all_excels()
