import pandas as pd
import numpy as np
from pathlib import Path
from sqlalchemy import text

# ------------------------------------------------------------
# DATABASE CONNECTION
# ------------------------------------------------------------

try:
    from src.db_engine import engine
except ImportError:
    from db_engine import engine


# ------------------------------------------------------------
# LOAD COST OF PRODUCTION EXCEL FILE
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

file_path = (
    BASE_DIR
    / "data"
    / "asia_allcountries_153crops_COP_usd_per_ha_2013_2023_no_seed.xlsx"
)

print("=" * 80)
print("LOADING COST OF PRODUCTION DATA")
print("=" * 80)

print("File:", file_path)

df = pd.read_excel(file_path)

print("Rows:", len(df))
print("Columns:", len(df.columns))

print("\nColumns:")
for col in df.columns:
    print("-", col)


# ============================================================
# CHECK 1: PESTICIDE TOTAL
# ============================================================

print("\n" + "=" * 80)
print("CHECK 1: PESTICIDE TOTAL")
print("=" * 80)

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


# ============================================================
# CHECK 2: NON-SEED TOTAL COST
# ============================================================

print("\n" + "=" * 80)
print("CHECK 2: TOTAL NON-SEED COST")
print("=" * 80)

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


# ============================================================
# CHECK 3: MISSING FERTILIZER
# ============================================================

print("\n" + "=" * 80)
print("CHECK 3: MISSING FERTILIZER")
print("=" * 80)

missing_fert = df[
    df["fertilizer_cost_per_ha_usd"].isna()
]

print(
    "Rows with missing fertilizer:",
    len(missing_fert)
)

print("\nFirst 10 missing-fertilizer rows:")

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
            "total_difference",
        ]
    ].head(10).to_string(index=False)
)


# ============================================================
# CHECK 4: BASIC DATASET COVERAGE
# ============================================================

print("\n" + "=" * 80)
print("CHECK 4: DATASET COVERAGE")
print("=" * 80)

print("Total rows:", len(df))
print("Countries:", df["country"].nunique())
print("Crops:", df["crop_item"].nunique())
print(
    "Year range:",
    df["year"].min(),
    "to",
    df["year"].max(),
)


# ============================================================
# CHECK 5: ASIA PRICE FACTOR
# ============================================================

print("\n" + "=" * 80)
print("CHECK 5: ASIA PRICE FACTOR")
print("=" * 80)

print("\nUnique asia_price_factor values:")

print(
    sorted(
        df["asia_price_factor"]
        .dropna()
        .unique()
    )
)

print(
    "\nNumber of unique factors:",
    df["asia_price_factor"].nunique()
)

print("\nFactor by country:")

factor_by_country = (
    df.groupby("country")["asia_price_factor"]
    .agg(["min", "max", "mean"])
    .sort_values("mean")
)

print(factor_by_country.to_string())


# ============================================================
# CHECK 6: TEST PRICE-FACTOR SCALING
# ============================================================

print("\n" + "=" * 80)
print("CHECK 6: ASIA PRICE FACTOR / PESTICIDE")
print("=" * 80)

df["fungicide_base"] = (
    df["fungicide_cost_per_ha_usd"]
    / df["asia_price_factor"]
)

df["herbicide_base"] = (
    df["herbicide_cost_per_ha_usd"]
    / df["asia_price_factor"]
)

df["insecticide_base"] = (
    df["insecticide_cost_per_ha_usd"]
    / df["asia_price_factor"]
)

df["pesticide_base"] = (
    df["total_pesticide_cost_per_ha_usd"]
    / df["asia_price_factor"]
)

sample_crop = df["crop_item"].iloc[0]
sample_year = df["year"].min()

sample = df[
    (df["crop_item"] == sample_crop)
    & (df["year"] == sample_year)
].copy()

print("Sample crop:", sample_crop)
print("Sample year:", sample_year)

print(
    sample[
        [
            "country",
            "asia_price_factor",
            "total_pesticide_cost_per_ha_usd",
            "pesticide_base",
        ]
    ].to_string(index=False)
)


# ============================================================
# CHECK 8: POSTGRESQL VIEW DEFINITION
# ============================================================

print("\n" + "=" * 80)
print("CHECK 8: POSTGRESQL crop_cop_per_ha VIEW")
print("=" * 80)

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
                format_type(
                    atttypid,
                    atttypmod
                )
            FROM pg_attribute
            WHERE
                attrelid =
                    'crop_cop_per_ha'::regclass
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


# ============================================================
# CHECK 9: SEED COST JOIN QUALITY
# ============================================================

print("\n" + "=" * 80)
print("CHECK 9: SEED COST JOIN QUALITY")
print("=" * 80)

with engine.connect() as conn:

    result = conn.execute(
        text("""
            SELECT
                COUNT(*) AS total_view_rows,
                COUNT(seed_cost_per_ha)
                    AS rows_with_seed,
                COUNT(*)
                    - COUNT(seed_cost_per_ha)
                    AS rows_without_seed
            FROM crop_cop_per_ha;
        """)
    ).fetchone()

    total_view_rows = result[0]
    rows_with_seed = result[1]
    rows_without_seed = result[2]

    print(
        "\nTOTAL VIEW ROWS:",
        total_view_rows
    )

    print(
        "ROWS WITH SEED:",
        rows_with_seed
    )

    print(
        "ROWS WITHOUT SEED:",
        rows_without_seed
    )

    print("\nSeed coverage percentage:")

    if total_view_rows > 0:
        seed_percentage = (
            rows_with_seed
            / total_view_rows
            * 100
        )

        print(
            round(seed_percentage, 2),
            "%"
        )


    # --------------------------------------------------------
    # CHECK DUPLICATES IN FINAL VIEW
    # --------------------------------------------------------

    print("\n" + "=" * 80)
    print(
        "CHECK FOR DUPLICATE "
        "COUNTRY-CROP-YEAR ROWS"
    )
    print("=" * 80)

    duplicates = conn.execute(
        text("""
            SELECT
                country,
                crop,
                year,
                COUNT(*) AS row_count
            FROM crop_cop_per_ha
            GROUP BY
                country,
                crop,
                year
            HAVING COUNT(*) > 1
            ORDER BY row_count DESC
            LIMIT 20;
        """)
    ).fetchall()

    if duplicates:

        print(
            "WARNING: Duplicate rows found:"
        )

        for row in duplicates:
            print(row)

    else:

        print(
            "No duplicate country-crop-year "
            "rows found."
        )


    # --------------------------------------------------------
    # CHECK DUPLICATES IN SEED DATASET
    # --------------------------------------------------------

    print("\n" + "=" * 80)
    print(
        "CHECK SEED DATA DUPLICATE "
        "CROP-YEAR KEYS"
    )
    print("=" * 80)

    seed_duplicates = conn.execute(
        text("""
            SELECT
                clean_crop_name,
                year,
                COUNT(*) AS row_count
            FROM
                "Seed_Cost_Per_Hector_cleaned (1)"
            GROUP BY
                clean_crop_name,
                year
            HAVING COUNT(*) > 1
            ORDER BY row_count DESC
            LIMIT 20;
        """)
    ).fetchall()

    if seed_duplicates:

        print(
            "WARNING: Duplicate crop-year "
            "seed records found:"
        )

        for row in seed_duplicates:
            print(row)

    else:

        print(
            "No duplicate crop-year "
            "seed records found."
        )


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n" + "=" * 80)
print("FINAL CHECK COMPLETE")
print("=" * 80)

print("""
Important formulas being tested:

Pesticide Cost =
    Fungicide
    + Herbicide
    + Insecticide

Non-seed Cost =
    Pesticide
    + Fertilizer
    + Irrigation

Final Cost per hectare =
    Non-seed Cost
    + Seed/Planting-Material Cost

Total Farm Cost =
    Final Cost per hectare
    x Farm Size
""")