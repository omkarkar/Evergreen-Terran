from sqlalchemy import text

try:
    from src.db_engine import engine
except ImportError:
    from db_engine import engine


print("=" * 80)
print("CHECK 9: SEED COST JOIN QUALITY")
print("=" * 80)

with engine.connect() as conn:

    result = conn.execute(
        text("""
            SELECT
                COUNT(*) AS total_view_rows,
                COUNT(seed_cost_per_ha) AS rows_with_seed,
                COUNT(*) - COUNT(seed_cost_per_ha) AS rows_without_seed
            FROM crop_cop_per_ha;
        """)
    ).fetchone()

    total_rows = result[0]
    rows_with_seed = result[1]
    rows_without_seed = result[2]

    print("\nTOTAL VIEW ROWS:", total_rows)
    print("ROWS WITH SEED:", rows_with_seed)
    print("ROWS WITHOUT SEED:", rows_without_seed)

    if total_rows > 0:
        coverage = (rows_with_seed / total_rows) * 100
        print("SEED COVERAGE:", round(coverage, 2), "%")

    print("\n" + "=" * 80)
    print("CHECK DUPLICATE COUNTRY-CROP-YEAR ROWS")
    print("=" * 80)

    duplicates = conn.execute(
        text("""
            SELECT
                country,
                crop,
                year,
                COUNT(*) AS row_count
            FROM crop_cop_per_ha
            GROUP BY country, crop, year
            HAVING COUNT(*) > 1
            ORDER BY row_count DESC
            LIMIT 20;
        """)
    ).fetchall()

    if duplicates:
        print("DUPLICATES FOUND:")
        for row in duplicates:
            print(row)
    else:
        print("No duplicate country-crop-year rows found.")

    print("\n" + "=" * 80)
    print("CHECK DUPLICATE SEED CROP-YEAR KEYS")
    print("=" * 80)

    seed_duplicates = conn.execute(
        text("""
            SELECT
                clean_crop_name,
                year,
                COUNT(*) AS row_count
            FROM "Seed_Cost_Per_Hector_cleaned (1)"
            GROUP BY clean_crop_name, year
            HAVING COUNT(*) > 1
            ORDER BY row_count DESC
            LIMIT 20;
        """)
    ).fetchall()

    if seed_duplicates:
        print("DUPLICATE SEED RECORDS FOUND:")
        for row in seed_duplicates:
            print(row)
    else:
        print("No duplicate crop-year seed records found.")

print("\n" + "=" * 80)
print("CHECK 9 COMPLETE")
print("=" * 80)
