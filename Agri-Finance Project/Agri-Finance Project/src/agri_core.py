# agri_core.py

import pandas as pd
import joblib

from db_engine import engine


# ============================================================
# 1. LOADERS: MODEL + DATA FROM SQL
# ============================================================

def load_yield_bundle():
    """Load the pre-trained yield model and metadata."""
    return joblib.load("yield_model_bundle.joblib")


def load_yield_panel():
    """Load merged yield + fertilizer + weather + soil panel from SQL."""
    return pd.read_sql("SELECT * FROM yield_panel", engine)


def load_price_df():
    """Load Asia-wide standardized commodity prices."""
    query = (
        'SELECT crop_name, year, asia_price_usd_per_ton '
        'FROM "asia_wide_standardized_price_master final"'
    )
    return pd.read_sql(query, engine)


def load_cop_df():
    """Load cost-of-production view, including seed cost."""
    return pd.read_sql("SELECT * FROM crop_cop_per_ha", engine)


# Load everything once at import time
yield_bundle = load_yield_bundle()
yield_panel = load_yield_panel()
price_df = load_price_df()
cop_df = load_cop_df()

yield_model = yield_bundle["yield_model"]
GLOBAL_YIELD_NUMERIC_MEANS = yield_bundle["GLOBAL_YIELD_NUMERIC_MEANS"]
numeric_features = yield_bundle["numeric_features"]
categorical_features = yield_bundle["categorical_features"]
ALL_YIELD_COUNTRIES = yield_bundle["ALL_YIELD_COUNTRIES"]
ALL_YIELD_CROPS = yield_bundle["ALL_YIELD_CROPS"]

ALL_PRICE_CROPS = sorted(price_df["crop_name"].astype(str).str.strip().unique())
ALL_COP_COUNTRIES = sorted(cop_df["country"].astype(str).str.strip().unique())
ALL_COP_CROPS = sorted(cop_df["crop"].astype(str).str.strip().unique())


# ============================================================
# 2. HELPER FUNCTIONS
# ============================================================

def _match_name(user_str, options):
    """Match a user-entered country/crop name to a known value."""
    if not user_str:
        return None

    user_clean = str(user_str).strip().lower()
    mapping = {str(o).strip().lower(): o for o in options}

    # Exact match
    if user_clean in mapping:
        return mapping[user_clean]

    # Unique prefix match
    cands = [o for o in options if str(o).strip().lower().startswith(user_clean)]
    if len(cands) == 1:
        return cands[0]

    # Unique substring match
    cands = [o for o in options if user_clean in str(o).strip().lower()]
    if len(cands) == 1:
        return cands[0]

    return None


def match_yield_country(user_country):
    return _match_name(user_country, ALL_YIELD_COUNTRIES)


def match_yield_crop(user_crop):
    return _match_name(user_crop, ALL_YIELD_CROPS)


def match_price_crop(user_crop):
    return _match_name(user_crop, ALL_PRICE_CROPS)


def match_cop_country(user_country):
    return _match_name(user_country, ALL_COP_COUNTRIES)


def match_cop_crop(user_crop):
    return _match_name(user_crop, ALL_COP_CROPS)


def _safe_float(value, default=0.0):
    """Safely convert a value to float. Treat None/NaN as default."""
    if value is None:
        return float(default)

    try:
        if pd.isna(value):
            return float(default)
    except TypeError:
        pass

    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


# ============================================================
# 3. CORE PREDICTION FUNCTIONS
# ============================================================

def predict_yield_ton_per_ha(country, crop, year):
    """Predict crop yield in tonnes/ha using the trained model."""
    c = match_yield_country(country)
    rcrop = match_yield_crop(crop)

    if c is None or rcrop is None:
        return None, c, rcrop

    hist = yield_panel[
        (yield_panel["country"] == c)
        & (yield_panel["crop"] == rcrop)
        & (yield_panel["year"] <= year)
    ].copy()

    if hist.empty:
        return None, c, rcrop

    # Use up to the five most recent records available through the requested year.
    k = min(5, len(hist))
    tail = hist.sort_values("year").tail(k)

    climate_cols = [col for col in numeric_features if col != "year"]
    local_means = tail[climate_cols].mean()

    # Fill missing numerical predictors using global training means.
    for col in climate_cols:
        if pd.isna(local_means[col]):
            local_means[col] = GLOBAL_YIELD_NUMERIC_MEANS[col]

    row = {
        "year": int(year),
        "country": c,
        "crop": rcrop,
    }

    for col in climate_cols:
        row[col] = local_means[col]

    X_future = pd.DataFrame([row])[numeric_features + categorical_features]
    pred = float(yield_model.predict(X_future)[0])

    # Crop yield cannot be negative.
    pred = max(pred, 0.0)

    return pred, c, rcrop


def forecast_price_next_years(user_crop, current_year, horizon=5):
    """
    Project commodity prices using a capped annualized historical growth rate.

    The growth rate is estimated from up to the seven most recent price records
    available on or before current_year and capped to [-5%, +5%]. Forecast years
    begin after the latest available historical price year.
    """
    crop_m = match_price_crop(user_crop)
    if crop_m is None:
        return None, crop_m

    sub = price_df[
        (price_df["crop_name"] == crop_m)
        & (price_df["year"] <= current_year)
    ].sort_values("year")

    if sub.empty:
        return None, crop_m

    k = min(7, len(sub))
    tail = sub.tail(k)

    years = tail["year"].to_numpy()
    prices = tail["asia_price_usd_per_ton"].to_numpy()

    last_year = int(years[-1])
    last_price = float(prices[-1])

    if k >= 2 and prices[0] > 0:
        n_periods = int(years[-1] - years[0])
        if n_periods > 0:
            raw_g = (prices[-1] / prices[0]) ** (1.0 / n_periods) - 1.0
        else:
            raw_g = 0.0
    else:
        raw_g = 0.0

    # Cap annual growth between -5% and +5%.
    g = max(min(float(raw_g), 0.05), -0.05)

    future_years = []
    preds = []
    price_now = last_price

    for i in range(1, int(horizon) + 1):
        year_f = last_year + i
        price_now *= 1.0 + g
        future_years.append(year_f)
        preds.append(max(float(price_now), 0.0))

    forecast_df = pd.DataFrame(
        {
            "year": future_years,
            "predicted_price_usd_per_ton": preds,
        }
    )

    return forecast_df, crop_m


def get_cost_of_production(country, crop, year, farm_size_ha=1.0):
    """Get per-hectare and total cost of production from crop_cop_per_ha."""
    c = match_cop_country(country)
    rcrop = match_cop_crop(crop)

    if c is None or rcrop is None:
        return None, c, rcrop

    df_cc = cop_df[
        (cop_df["country"] == c)
        & (cop_df["crop"] == rcrop)
    ].copy()

    if df_cc.empty:
        return None, c, rcrop

    # Use the available CoP record closest to the requested assessment year.
    df_cc["year_diff"] = (df_cc["year"] - year).abs()
    row = df_cc.sort_values(["year_diff", "year"]).iloc[0]

    cop_year_used = int(row["year"])

    fert_cost_ha = _safe_float(row.get("fertilizer_cost_per_ha"), 0.0)
    irr_cost_ha = _safe_float(row.get("irrigation_cost_per_ha"), 0.0)
    pest_cost_ha = _safe_float(row.get("pesticide_cost_per_ha"), 0.0)
    seed_cost_ha = _safe_float(row.get("seed_cost_per_ha"), 0.0)
    non_seed_cost_ha = _safe_float(row.get("non_seed_cost_per_ha"), 0.0)

    total_with_seed_ha = _safe_float(
        row.get("total_cost_per_ha"),
        non_seed_cost_ha + seed_cost_ha,
    )

    other_cost_ha = max(
        non_seed_cost_ha - (fert_cost_ha + irr_cost_ha + pest_cost_ha),
        0.0,
    )

    res = {
        "country": c,
        "crop": rcrop,
        "requested_year": int(year),
        "cop_year_used": cop_year_used,
        "farm_size_ha": float(farm_size_ha),
        "fertilizer_cost_per_ha_usd": fert_cost_ha,
        "pesticide_cost_per_ha_usd": pest_cost_ha,
        "irrigation_cost_per_ha_usd": irr_cost_ha,
        "other_cost_per_ha_usd": other_cost_ha,
        "seed_cost_per_ha_usd": seed_cost_ha,
        "total_cost_per_ha_usd_with_seed": total_with_seed_ha,
        "fertilizer_cost_total_usd": fert_cost_ha * farm_size_ha,
        "pesticide_cost_total_usd": pest_cost_ha * farm_size_ha,
        "irrigation_cost_total_usd": irr_cost_ha * farm_size_ha,
        "other_cost_total_usd": other_cost_ha * farm_size_ha,
        "seed_cost_total_usd": seed_cost_ha * farm_size_ha,
        "total_cost_total_usd": total_with_seed_ha * farm_size_ha,
    }

    return res, c, rcrop


# ============================================================
# 4. FINAL REPORT FUNCTION
# ============================================================

def generate_agri_finance_report(
    farmer_name,
    country,
    crop,
    current_year,
    farm_size_ha,
    loan_amount_usd,
    annual_interest_rate,
    tenure_months,
):
    """Generate the integrated agricultural-finance assessment."""

    current_year = int(current_year)
    farm_size_ha = float(farm_size_ha)
    loan_amount_usd = float(loan_amount_usd)
    annual_interest_rate = float(annual_interest_rate)
    tenure_months = int(tenure_months)

    # Defensive input validation.
    if farm_size_ha <= 0:
        return "Farm size must be greater than zero.", None

    if loan_amount_usd <= 0:
        return "Loan amount must be greater than zero.", None

    if tenure_months <= 0:
        return "Loan tenure must be greater than zero.", None

    if annual_interest_rate < 0 or annual_interest_rate > 100:
        return "Annual interest rate must be between 0 and 100 percent.", None

    # The application accepts the annual interest rate as a percentage, e.g. 12 = 12%.
    r = annual_interest_rate / 100.0

    # --------------------------------------------------------
    # 1) YIELD PREDICTION
    # --------------------------------------------------------
    pred_yield, y_country, y_crop = predict_yield_ton_per_ha(
        country,
        crop,
        current_year,
    )

    if pred_yield is None:
        return (
            "Could not predict yield; country or crop not found in yield data.",
            None,
        )

    total_prod = pred_yield * farm_size_ha

    # --------------------------------------------------------
    # 2) COMMODITY PRICE ASSESSMENT + FIVE-YEAR PROJECTION
    # --------------------------------------------------------
    price_crop = match_price_crop(crop)

    if price_crop is None:
        return "Could not project price; crop not found in price data.", None

    price_history = price_df[
        (price_df["crop_name"] == price_crop)
        & (price_df["year"] <= current_year)
    ].sort_values("year")

    if price_history.empty:
        return "Could not project price; no historical price data available.", None

    last_historical_year = int(price_history["year"].max())

    # Forecast far enough to reach the assessment year AND provide five years
    # after the assessment year for the report.
    forecast_horizon = max(
        5,
        (current_year + 5) - last_historical_year,
    )

    price_forecast_all, price_crop = forecast_price_next_years(
        crop,
        current_year,
        horizon=forecast_horizon,
    )

    if price_forecast_all is None:
        return "Could not generate commodity-price projection.", None

    # Use an observed current-year price if one exists; otherwise use the
    # projected price corresponding exactly to the requested assessment year.
    observed_current = price_history[price_history["year"] == current_year]

    if not observed_current.empty:
        season_year = current_year
        season_price = float(
            observed_current.iloc[-1]["asia_price_usd_per_ton"]
        )
        season_price_source = "observed"
    else:
        assessment_rows = price_forecast_all[
            price_forecast_all["year"] == current_year
        ]

        if assessment_rows.empty:
            return (
                f"Could not generate commodity price for assessment year {current_year}.",
                None,
            )

        assessment_row = assessment_rows.iloc[0]
        season_year = int(assessment_row["year"])
        season_price = float(
            assessment_row["predicted_price_usd_per_ton"]
        )
        season_price_source = "projected"

    # Five future years after the requested assessment year for reporting.
    future_price_forecast = price_forecast_all[
        (price_forecast_all["year"] > current_year)
        & (price_forecast_all["year"] <= current_year + 5)
    ].copy()

    revenue = total_prod * season_price

    # --------------------------------------------------------
    # 3) COST OF PRODUCTION
    # --------------------------------------------------------
    cop_res, cop_country, cop_crop = get_cost_of_production(
        country,
        crop,
        current_year,
        farm_size_ha,
    )

    if cop_res is None:
        return (
            "Could not compute cost of production; no CoP data for this country/crop.",
            None,
        )

    cost_per_ha = cop_res["total_cost_per_ha_usd_with_seed"]
    total_cost = cop_res["total_cost_total_usd"]

    # --------------------------------------------------------
    # 4) LOAN REPAYMENT + REPAYMENT CAPACITY
    # --------------------------------------------------------
    monthly_rate = r / 12.0
    n_months = tenure_months

    if monthly_rate == 0:
        emi = loan_amount_usd / n_months
    else:
        growth_factor = (1.0 + monthly_rate) ** n_months
        emi = (
            loan_amount_usd
            * monthly_rate
            * growth_factor
            / (growth_factor - 1.0)
        )

    total_repayment = emi * n_months
    total_interest = total_repayment - loan_amount_usd

    profit = revenue - total_cost
    capacity_ratio = profit / total_repayment

    if capacity_ratio >= 1.3:
        decision_text = "He can repay comfortably."
        icon = "✔"
    elif capacity_ratio >= 1.0:
        decision_text = "He can likely repay, but with some risk."
        icon = "✔"
    else:
        decision_text = "High risk: profit may not fully cover repayment."
        icon = "⚠"

    # --------------------------------------------------------
    # 5) HUMAN-READABLE REPORT
    # --------------------------------------------------------
    lines = []
    lines.append("🌾 Agri-Finance App Demo (Simulation)")
    lines.append("")
    lines.append(f"Farmer: {farmer_name}")
    lines.append(
        f"Country: {country} (matched: YIELD='{y_country}', COP='{cop_country}')"
    )
    lines.append(
        f"Crop: {crop} (matched: YIELD='{y_crop}', PRICE='{price_crop}', COP='{cop_crop}')"
    )
    lines.append(f"Assessment Year: {current_year}")
    lines.append(f"Loan Amount Requested: ${loan_amount_usd:,.2f}")
    lines.append(f"Farm Size: {farm_size_ha:g} hectares")
    lines.append("")

    lines.append("1️⃣ Yield Prediction")
    lines.append("")
    lines.append(f"Predicted yield: {pred_yield:.2f} tons/ha")
    lines.append(
        f"Total expected production: {pred_yield:.2f} × {farm_size_ha:g} "
        f"= {total_prod:.2f} tons"
    )
    lines.append("")

    lines.append("2️⃣ Commodity Price Projection (Asia-wide USD/ton)")
    lines.append("")
    lines.append(
        f"Assessment-year price ({season_year}, {season_price_source}): "
        f"${season_price:,.2f}/ton"
    )
    lines.append("")
    lines.append("Five-year price projection after the assessment year:")
    lines.append("Year\tProjected Price")

    for _, row in future_price_forecast.iterrows():
        lines.append(
            f"{int(row['year'])}\t${row['predicted_price_usd_per_ton']:,.2f}/ton"
        )

    lines.append("")
    lines.append(f"Estimated revenue for assessment year {season_year}:")
    lines.append(
        f"{total_prod:.2f} tons × ${season_price:,.2f} "
        f"= ${revenue:,.2f}"
    )
    lines.append("")

    lines.append("3️⃣ Cost of Production (CoP + seed datasets)")
    lines.append("")
    lines.append(
        f"Requested assessment year: {current_year}; "
        f"CoP year used: {cop_res['cop_year_used']}"
    )
    lines.append("Estimated per-hectare cost:")
    lines.append("")
    lines.append("Component\tCost (USD/ha)")
    lines.append(f"Fertilizer\t{cop_res['fertilizer_cost_per_ha_usd']:,.2f}")
    lines.append(f"Pesticides\t{cop_res['pesticide_cost_per_ha_usd']:,.2f}")
    lines.append(f"Irrigation\t{cop_res['irrigation_cost_per_ha_usd']:,.2f}")
    lines.append(f"Seed\t{cop_res['seed_cost_per_ha_usd']:,.2f}")
    lines.append(f"Other\t{cop_res['other_cost_per_ha_usd']:,.2f}")
    lines.append("")
    lines.append(f"Total cost/ha = ${cost_per_ha:,.2f}")
    lines.append(f"Farm cost ({farm_size_ha:g} ha) = ${total_cost:,.2f}")
    lines.append("")

    lines.append("4️⃣ Repayment Capacity")
    lines.append("")
    lines.append("Farmer's margin = Revenue - Cost")
    lines.append(f"= ${revenue:,.2f} - ${total_cost:,.2f} = ${profit:,.2f}")
    lines.append("")
    lines.append(f"Loan requested = ${loan_amount_usd:,.2f}")
    lines.append(f"Interest = {annual_interest_rate:.2f}% per year")
    lines.append(f"Tenure = {tenure_months} months")
    lines.append(f"Estimated monthly EMI = ${emi:,.2f}")
    lines.append(f"Total interest = ${total_interest:,.2f}")
    lines.append(f"Total repayment = ${total_repayment:,.2f}")
    lines.append(f"Profit / Total repayment ratio = {capacity_ratio:.2f}x")
    lines.append("")
    lines.append(f"{icon} {decision_text}")

    report_text = "\n".join(lines)

    # --------------------------------------------------------
    # 6) STRUCTURED SUMMARY FOR THE API / FRONTEND
    # --------------------------------------------------------
    summary = {
        "assessment_year": int(current_year),
        "predicted_yield_ton_per_ha": float(pred_yield),
        "total_production_tons": float(total_prod),
        "season_year": int(season_year),
        "season_price_source": season_price_source,
        "predicted_price_usd_per_ton": float(season_price),
        "revenue_usd": float(revenue),
        "cop_year_used": int(cop_res["cop_year_used"]),
        "total_cost_usd": float(total_cost),
        "profit_usd": float(profit),
        "emi_usd": float(emi),
        "total_interest_usd": float(total_interest),
        "total_repayment_usd": float(total_repayment),
        "capacity_ratio": float(capacity_ratio),
        "decision_text": decision_text,
        "price_crop": price_crop,
    }

    return report_text, summary
