import pandas as pd
import numpy as np

file_path = r"data/asia_allcountries_153crops_COP_usd_per_ha_2013_2023_no_seed.xlsx"

df = pd.read_excel(file_path)

print("=" * 70)
print("CHECK 1: PESTICIDE TOTAL")
print("=" * 70)

df["calculated_pesticide"] = (
    df["fungicide_cost_per_ha_usd"].fillna(0)
    + df["herbicide_cost_per_ha_usd"].fillna(0)
    + df["insecticide_cost_per_ha_usd"].fillna(0)
)

df["pesticide_difference"] = (
    df["total_pesticide_cost_per_ha_usd"]
    - df["calculated_pesticide"]
)

pesticide_match = np.isclose(
    df["total_pesticide_cost_per_ha_usd"],
    df["calculated_pesticide"],
    atol=0.000001
)

print("Matching rows:", pesticide_match.sum())
print("Total rows:", len(df))
print("Match percentage:", pesticide_match.mean() * 100)
print(
    "Maximum difference:",
    df["pesticide_difference"].abs().max()
)


print("\n" + "=" * 70)
print("CHECK 2: TOTAL COST")
print("=" * 70)

df["fertilizer_for_check"] = (
    df["fertilizer_cost_per_ha_usd"].fillna(0)
)

df["calculated_total_cost"] = (
    df["total_pesticide_cost_per_ha_usd"]
    + df["fertilizer_for_check"]
    + df["irrigation_cost_per_ha_usd"]
)

df["total_difference"] = (
    df["total_cost_usd_per_ha"]
    - df["calculated_total_cost"]
)

total_match = np.isclose(
    df["total_cost_usd_per_ha"],
    df["calculated_total_cost"],
    atol=0.000001
)

print("Matching rows:", total_match.sum())
print("Total rows:", len(df))
print("Match percentage:", total_match.mean() * 100)
print(
    "Maximum difference:",
    df["total_difference"].abs().max()
)


print("\n" + "=" * 70)
print("CHECK 3: MISSING FERTILIZER ROWS")
print("=" * 70)

missing_fert = df[df["fertilizer_cost_per_ha_usd"].isna()]

print("Rows with missing fertilizer:", len(missing_fert))

print(
    missing_fert[
        [
            "country",
            "year",
            "crop_item",
            "total_pesticide_cost_per_ha_usd",
            "fertilizer_cost_per_ha_usd",
            "irrigation_cost_per_ha_usd",
            "total_cost_usd_per_ha",
            "calculated_total_cost",
            "total_difference"
        ]
    ].head(10)
)


print("\n" + "=" * 70)
print("CHECK 4: SAMPLE COMPLETE ROWS")
print("=" * 70)

print(
    df[
        [
            "country",
            "year",
            "crop_item",
            "total_pesticide_cost_per_ha_usd",
            "fertilizer_cost_per_ha_usd",
            "irrigation_cost_per_ha_usd",
            "total_cost_usd_per_ha",
            "calculated_total_cost",
            "total_difference"
        ]
    ].head(20)
)

print("\n" + "=" * 70)
print("CHECK 5: ASIA PRICE FACTOR")
print("=" * 70)

print("Unique asia_price_factor values:")
print(sorted(df["asia_price_factor"].unique()))

print("\nNumber of unique factors:")
print(df["asia_price_factor"].nunique())

print("\nFactor by country:")
print(
    df.groupby("country")["asia_price_factor"]
    .agg(["min", "max", "mean"])
    .sort_values("mean")
)

print("\nCorrelation with cost components:")
print(
    df[
        [
            "asia_price_factor",
            "fungicide_cost_per_ha_usd",
            "herbicide_cost_per_ha_usd",
            "insecticide_cost_per_ha_usd",
            "total_pesticide_cost_per_ha_usd",
            "fertilizer_cost_per_ha_usd",
            "irrigation_cost_per_ha_usd",
            "total_cost_usd_per_ha",
        ]
    ].corr()["asia_price_factor"]
)

print("\nSample grouped by price factor:")
print(
    df.groupby("asia_price_factor")
    [
        [
            "total_pesticide_cost_per_ha_usd",
            "fertilizer_cost_per_ha_usd",
            "irrigation_cost_per_ha_usd",
            "total_cost_usd_per_ha",
        ]
    ]
    .mean()
)

print("\n" + "=" * 80)
print("CHECK 8: POSTGRESQL crop_cop_per_ha VIEW")
print("=" * 80)

from sqlalchemy import text
from db_engine import engine

with engine.connect() as conn:

    print("\nVIEW DEFINITION:")
    print("-" * 80)

    definition = conn.execute(
        text("""
        SELECT pg_get_viewdef(
            'crop_cop_per_ha'::regclass,
            true
        );
        """)
    ).scalar()

    print(definition)

    print("\n" + "=" * 80)
    print("VIEW COLUMNS")
    print("=" * 80)

    columns = conn.execute(
        text("""
        SELECT
            attname,
            format_type(atttypid, atttypmod)
        FROM pg_attribute
        WHERE attrelid = 'crop_cop_per_ha'::regclass
          AND attnum > 0
          AND NOT attisdropped
        ORDER BY attnum;
        """)
    ).fetchall()

    for col in columns:
        print(col)

    print("\n" + "=" * 80)
    print("FIRST 5 VIEW ROWS")
    print("=" * 80)

    result = conn.execute(
        text("""
        SELECT *
        FROM crop_cop_per_ha
        LIMIT 5;
        """)
    )

    print("Columns:", list(result.keys()))

    for row in result:
        print(row)