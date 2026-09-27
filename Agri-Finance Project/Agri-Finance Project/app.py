import textwrap

import numpy as np
import pandas as pd
import streamlit as st
import joblib

from sqlalchemy import text           # 👈 ADD THIS
from db_engine import engine          # uses your DATABASE_URL

# ------------------------------------------------------------
# Page config (must be before any other st.* call)
# ------------------------------------------------------------
st.set_page_config(
    page_title="Agri-Finance Prediction App",
    page_icon="🌾",
    layout="wide",
)

# ============================================================
# 1. CACHED LOADERS: MODEL + DATA FROM SQL
# ============================================================

@st.cache_resource
def load_yield_bundle():
    """
    Load the pre-trained yield model + metadata.
    This file is created by train_yield_model.py
    """
    bundle = joblib.load("yield_model_bundle.joblib")
    return bundle


@st.cache_data
def load_yield_panel():
    """Load merged yield + fertilizer + weather + soil panel from SQL."""
    return pd.read_sql("SELECT * FROM yield_panel", engine)


@st.cache_data
def load_price_df():
    """Load Asia-wide standardized prices."""
    query = 'SELECT crop_name, year, asia_price_usd_per_ton FROM "asia_wide_standardized_price_master final"'
    return pd.read_sql(query, engine)


@st.cache_data
def load_cop_df():
    """
    Load cost of production view (includes seed cost).
    Uses crop_cop_per_ha materialized view from your SQL.
    """
    return pd.read_sql("SELECT * FROM crop_cop_per_ha", engine)


# Load everything once
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
    """Loose matching of country/crop to known names."""
    if not user_str:
        return None
    user_clean = str(user_str).strip().lower()
    mapping = {o.lower(): o for o in options}

    # Exact match
    if user_clean in mapping:
        return mapping[user_clean]

    # Prefix
    cands = [o for o in options if o.lower().startswith(user_clean)]
    if len(cands) == 1:
        return cands[0]

    # Substring
    cands = [o for o in options if user_clean in o.lower()]
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
    """
    Safely convert a value to float.
    Treats None / NaN / empty strings as `default`.
    """
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
    """
    Predict yield ton/ha using:
    - trained RandomForest pipeline (yield_model)
    - yield_panel for local climate/fert/soil averages
    """
    c = match_yield_country(country)
    rcrop = match_yield_crop(crop)
    if c is None or rcrop is None:
        return None, c, rcrop

    hist = yield_panel[
        (yield_panel["country"] == c) &
        (yield_panel["crop"] == rcrop) &
        (yield_panel["year"] <= year)
    ].copy()

    if hist.shape[0] == 0:
        return None, c, rcrop

    # Take last up to 5 years
    k = min(5, hist.shape[0])
    tail = hist.sort_values("year").tail(k)

    climate_cols = [col for col in numeric_features if col != "year"]
    local_means = tail[climate_cols].mean()

    # Fill gaps with global means
    for col in climate_cols:
        if pd.isna(local_means[col]):
            local_means[col] = GLOBAL_YIELD_NUMERIC_MEANS[col]

    row = {"year": year, "country": c, "crop": rcrop}
    for col in climate_cols:
        row[col] = local_means[col]

    X_future = pd.DataFrame([row])[numeric_features + categorical_features]
    pred = float(yield_model.predict(X_future)[0])
    if pred < 0:
        pred = 0.0
    return pred, c, rcrop


def forecast_price_next_years(user_crop, current_year, horizon=5):
    """
    Forecast price using capped average annual growth rate
    (avoids unrealistic explosion).
    """
    crop_m = match_price_crop(user_crop)
    if crop_m is None:
        return None, crop_m

    sub = price_df[
        (price_df["crop_name"] == crop_m) &
        (price_df["year"] <= current_year)
    ].sort_values("year")

    if sub.shape[0] == 0:
        return None, crop_m

    k = min(7, sub.shape[0])
    tail = sub.tail(k)
    years = tail["year"].values
    prices = tail["asia_price_usd_per_ton"].values

    last_year = int(years[-1])
    last_price = float(prices[-1])

    if k >= 2 and prices[0] > 0:
        n_periods = years[-1] - years[0]
        if n_periods > 0:
            raw_g = (prices[-1] / prices[0]) ** (1.0 / n_periods) - 1.0
        else:
            raw_g = 0.0
    else:
        raw_g = 0.0

    g = max(min(raw_g, 0.05), -0.05)  # cap between -5% and +5%

    future_years = []
    preds = []
    price_now = last_price

    for i in range(1, horizon + 1):
        year_f = last_year + i
        price_now = price_now * (1.0 + g)
        future_years.append(year_f)
        preds.append(max(price_now, 0))

    df = pd.DataFrame({
        "year": future_years,
        "predicted_price_usd_per_ton": preds
    })
    return df, crop_m


def get_cost_of_production(country, crop, year, farm_size_ha=1.0):
    """
    Get per-ha and total cost of production from crop_cop_per_ha view.
    Uses nearest year available.
    """
    c = match_cop_country(country)
    rcrop = match_cop_crop(crop)
    if c is None or rcrop is None:
        return None, c, rcrop

    df_cc = cop_df[
        (cop_df["country"] == c) &
        (cop_df["crop"] == rcrop)
    ].copy()

    if df_cc.shape[0] == 0:
        return None, c, rcrop

    df_cc["year_diff"] = (df_cc["year"] - year).abs()
    row = df_cc.sort_values("year_diff").iloc[0]

    cop_year_used = int(row["year"])

    # Use safe float conversion to handle None / NaN
    fert_cost_ha = _safe_float(row.get("fertilizer_cost_per_ha"), 0.0)
    irr_cost_ha = _safe_float(row.get("irrigation_cost_per_ha"), 0.0)
    pest_cost_ha = _safe_float(row.get("pesticide_cost_per_ha"), 0.0)
    seed_cost_ha = _safe_float(row.get("seed_cost_per_ha"), 0.0)
    non_seed_cost_ha = _safe_float(row.get("non_seed_cost_per_ha"), 0.0)
    total_with_seed_ha = _safe_float(
        row.get("total_cost_per_ha"),
        non_seed_cost_ha + seed_cost_ha
    )

    other_cost_ha = max(
        non_seed_cost_ha - (fert_cost_ha + irr_cost_ha + pest_cost_ha),
        0.0
    )

    fert_tot = fert_cost_ha * farm_size_ha
    pest_tot = pest_cost_ha * farm_size_ha
    irr_tot = irr_cost_ha * farm_size_ha
    seed_tot = seed_cost_ha * farm_size_ha
    other_tot = other_cost_ha * farm_size_ha
    total_tot = total_with_seed_ha * farm_size_ha

    res = {
        "country": c,
        "crop": rcrop,
        "requested_year": year,
        "cop_year_used": cop_year_used,
        "farm_size_ha": farm_size_ha,
        "fertilizer_cost_per_ha_usd": fert_cost_ha,
        "pesticide_cost_per_ha_usd": pest_cost_ha,
        "irrigation_cost_per_ha_usd": irr_cost_ha,
        "other_cost_per_ha_usd": other_cost_ha,
        "seed_cost_per_ha_usd": seed_cost_ha,
        "total_cost_per_ha_usd_with_seed": total_with_seed_ha,
        "fertilizer_cost_total_usd": fert_tot,
        "pesticide_cost_total_usd": pest_tot,
        "irrigation_cost_total_usd": irr_tot,
        "other_cost_total_usd": other_tot,
        "seed_cost_total_usd": seed_tot,
        "total_cost_total_usd": total_tot,
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
    tenure_months
):
    # Normalize interest from % to decimal if needed
    if annual_interest_rate > 1:
        r = annual_interest_rate / 100.0
    else:
        r = annual_interest_rate

    # 1) Yield
    pred_yield, y_country, y_crop = predict_yield_ton_per_ha(country, crop, current_year)
    if pred_yield is None:
        return "Could not predict yield; country or crop not found in yield data.", None

    total_prod = pred_yield * farm_size_ha

    # 2) Price (next 5 years)
    price_forecast, price_crop = forecast_price_next_years(crop, current_year, horizon=5)
    if price_forecast is None:
        return "Could not forecast price; crop not found in price data.", None

    first_year_price_row = price_forecast.iloc[0]
    season_year = int(first_year_price_row["year"])
    season_price = float(first_year_price_row["predicted_price_usd_per_ton"])
    revenue = total_prod * season_price

    # 3) Cost of production
    cop_res, cop_country, cop_crop = get_cost_of_production(country, crop, season_year, farm_size_ha)
    if cop_res is None:
        return "Could not compute cost of production; no CoP data for this country/crop.", None

    cost_per_ha = cop_res["total_cost_per_ha_usd_with_seed"]
    total_cost = cop_res["total_cost_total_usd"]

    # 4) Repayment capacity
    total_interest = loan_amount_usd * r * (tenure_months / 12.0)
    total_repayment = loan_amount_usd + total_interest
    profit = revenue - total_cost

    capacity_ratio = None
    if total_repayment > 0:
        capacity_ratio = profit / total_repayment

    if capacity_ratio is None:
        decision_text = "Cannot evaluate repayment capacity."
        icon = "⚠"
    else:
        if capacity_ratio >= 1.3:
            decision_text = "He can repay comfortably."
            icon = "✔"
        elif capacity_ratio >= 1.0:
            decision_text = "He can likely repay, but with some risk."
            icon = "✔"
        else:
            decision_text = "High risk: profit may not fully cover repayment."
            icon = "⚠"

    # Build text report
    lines = []
    lines.append("🌾 Agri-Finance App Demo (Simulation)")
    lines.append("")
    lines.append(f"Farmer: {farmer_name}")
    lines.append(f"Country: {country} (matched: YIELD='{y_country}', COP='{cop_country}')")
    lines.append(f"Crop: {crop} (matched: YIELD='{y_crop}', PRICE='{price_crop}', COP='{cop_crop}')")
    lines.append(f"Loan Amount Requested: ${loan_amount_usd:,.0f}")
    lines.append(f"Farm Size: {farm_size_ha} hectares")
    lines.append("")

    # 1) Yield
    lines.append("1️⃣ Yield Prediction (Using yield+weather+soil+fertilizer model)")
    lines.append("")
    lines.append(f"Predicted yield: {pred_yield:.2f} tons/ha")
    lines.append("")
    lines.append(f"Total expected production: {pred_yield:.2f} × {farm_size_ha} = {total_prod:.2f} tons")
    lines.append("")

    # 2) Price
    lines.append("2️⃣ Price Prediction for Next 5 Years (Asia-wide USD/ton)")
    lines.append("")
    lines.append(f"Projected Asia {price_crop} price (USD/ton):")
    lines.append("")
    lines.append("Year\tPredicted Price")
    for _, row in price_forecast.iterrows():
        lines.append(f"{int(row['year'])}\t${row['predicted_price_usd_per_ton']:.0f}/ton")
    lines.append("")
    lines.append(f"Estimated revenue this season (year {season_year}):")
    lines.append(f"{total_prod:.2f} tons × {season_price:.0f} = ${revenue:,.0f}")
    lines.append("")

    # 3) Cost of production
    lines.append("3️⃣ Cost of Production (Based on CoP + seed datasets)")
    lines.append("")
    lines.append("Estimated per-hectare cost:")
    lines.append("")
    lines.append("Component\tCost (USD/ha)")
    lines.append(f"Fertilizer\t{cop_res['fertilizer_cost_per_ha_usd']:.0f}")
    lines.append(f"Pesticides\t{cop_res['pesticide_cost_per_ha_usd']:.0f}")
    lines.append(f"Irrigation\t{cop_res['irrigation_cost_per_ha_usd']:.0f}")
    lines.append(f"Seed\t{cop_res['seed_cost_per_ha_usd']:.0f}")
    lines.append(f"Other\t{cop_res['other_cost_per_ha_usd']:.0f}")
    lines.append("")
    lines.append(f"Total cost/ha = ${cost_per_ha:.0f}")
    lines.append(f"Farm cost ({farm_size_ha} ha) = ${total_cost:,.0f}")
    lines.append("")

    # 4) Repayment
    lines.append("4️⃣ Repayment Capacity")
    lines.append("")
    lines.append("Farmer’s margin = Revenue – Cost")
    lines.append(f"= {revenue:,.0f} – {total_cost:,.0f} = ${profit:,.0f}")
    lines.append("")
    lines.append(f"Loan requested = ${loan_amount_usd:,.0f}")
    lines.append(f"Interest = {r*100:.1f}% per year")
    lines.append(f"Tenure = {tenure_months} months")
    lines.append(f"Total repayment (principal + interest) ≈ ${total_repayment:,.0f}")
    if capacity_ratio is not None:
        lines.append(f"Profit / Total repayment ratio = {capacity_ratio:.2f}x")
    lines.append("")
    lines.append(f"{icon} {decision_text}")

    report_text = "\n".join(lines)

    summary = {
        "predicted_yield_ton_per_ha": float(pred_yield),
        "total_production_tons": float(total_prod),
        "season_year": int(season_year),
        "predicted_price_usd_per_ton": float(season_price),
        "revenue_usd": float(revenue),
        "total_cost_usd": float(total_cost),
        "profit_usd": float(profit),
        "capacity_ratio": float(capacity_ratio) if capacity_ratio is not None else None,
        "decision_text": decision_text,
        "price_crop": price_crop,
    }

    return report_text, summary


# ============================================================
# 5. STREAMLIT UI + SQL LOGGING (DASHBOARD STYLE)
# ============================================================

# Custom top banner
st.markdown(
    """
    <style>
    .big-title {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        font-size: 0.95rem;
        color: #555;
        margin-bottom: 1.5rem;
    }
    .badge-good {
        padding: 0.35rem 0.7rem;
        border-radius: 999px;
        background-color: #e6ffed;
        color: #037c3b;
        font-size: 0.8rem;
        display: inline-block;
        font-weight: 600;
    }
    .badge-risk {
        padding: 0.35rem 0.7rem;
        border-radius: 999px;
        background-color: #fff5f5;
        color: #c53030;
        font-size: 0.8rem;
        display: inline-block;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="big-title">🌾 Agri-Finance Prediction App</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">'
    'End-to-end view of yield, price, cost of production and loan repayment capacity.'
    '</div>',
    unsafe_allow_html=True,
)

# -------------- Sidebar inputs ----------------
with st.sidebar:
    st.header("🧑‍🌾 Farmer & Loan Inputs")

    farmer_name = st.text_input("Farmer Name", "Mr. Kumar")
    country = st.text_input("Country", "India")
    crop = st.text_input("Crop", "Wheat")

    current_year = st.number_input(
        "Current Year",
        min_value=2000,
        max_value=2050,
        value=2023,
    )

    st.markdown("---")
    farm_size_ha = st.number_input("Farm Size (ha)", min_value=0.1, value=2.0)
    loan_amount_usd = st.number_input("Loan Amount (USD)", min_value=0.0, value=2000.0)
    annual_interest_rate = st.number_input("Annual Interest Rate (%)", min_value=0.0, value=12.0)
    tenure_months = st.number_input("Loan Tenure (months)", min_value=1, value=12)

    st.markdown("---")
    generate = st.button("🚀 Generate Agri-Finance Report", use_container_width=True)

# -------------- Main layout ----------------
if generate:
    report_text, summary = generate_agri_finance_report(
        farmer_name=farmer_name,
        country=country,
        crop=crop,
        current_year=current_year,
        farm_size_ha=farm_size_ha,
        loan_amount_usd=loan_amount_usd,
        annual_interest_rate=annual_interest_rate,
        tenure_months=tenure_months,
    )

    if summary is None:
        st.error(report_text)
    else:
        # KPIs row
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Yield (t/ha)", f"{summary['predicted_yield_ton_per_ha']:.2f}")
        kpi2.metric("Total Production (t)", f"{summary['total_production_tons']:.2f}")
        kpi3.metric("Revenue (USD)", f"{summary['revenue_usd']:,.0f}")
        kpi4.metric("Total Cost (USD)", f"{summary['total_cost_usd']:,.0f}")

        # Second KPI row: profit & capacity
        c1, c2, c3 = st.columns(3)
        c1.metric("Profit (USD)", f"{summary['profit_usd']:,.0f}")
        if summary["capacity_ratio"] is not None:
            c2.metric("Profit / Repayment", f"{summary['capacity_ratio']:.2f}x")
        else:
            c2.metric("Profit / Repayment", "N/A")

        risk_html_class = "badge-good" if "repay comfortably" in summary["decision_text"] else "badge-risk"
        c3.markdown(
            f'<span class="{risk_html_class}">{summary["decision_text"]}</span>',
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # Tabs: chart view, cost breakdown, full report
        tab1, tab2, tab3 = st.tabs(["📈 Price Forecast", "💰 Cost Breakdown", "📄 Full Report"])

        # -------- Tab 1: Price Forecast -----------
        with tab1:
            price_forecast, price_crop = forecast_price_next_years(crop, current_year, horizon=5)
            if price_forecast is not None:
                st.subheader(f"Price Forecast for {price_crop} (Asia-wide USD/ton)")
                chart_df = price_forecast.set_index("year")
                st.line_chart(chart_df["predicted_price_usd_per_ton"])
                st.caption("Forecast uses capped average growth (−5% to +5% per year).")
            else:
                st.info("No price history available for this crop.")

        # -------- Tab 2: Cost Breakdown -----------
        with tab2:
            price_forecast_tmp, _ = forecast_price_next_years(crop, current_year, horizon=5)
            if price_forecast_tmp is not None and price_forecast_tmp.shape[0] > 0:
                season_year = int(price_forecast_tmp.iloc[0]["year"])
                cop_res, _, _ = get_cost_of_production(country, crop, season_year, farm_size_ha)
            else:
                cop_res = None

            if cop_res is not None:
                st.subheader("Per-Hectare Cost Structure")

                cost_components = pd.DataFrame({
                    "Component": ["Fertilizer", "Pesticides", "Irrigation", "Seed", "Other"],
                    "Cost_USD_per_ha": [
                        cop_res["fertilizer_cost_per_ha_usd"],
                        cop_res["pesticide_cost_per_ha_usd"],
                        cop_res["irrigation_cost_per_ha_usd"],
                        cop_res["seed_cost_per_ha_usd"],
                        cop_res["other_cost_per_ha_usd"],
                    ]
                }).set_index("Component")

                st.bar_chart(cost_components)
                st.caption(f"Total cost/ha: ${cop_res['total_cost_per_ha_usd_with_seed']:.0f}")
            else:
                st.info("No cost-of-production data available for this country/crop combination.")

        # -------- Tab 3: Full text report ---------
        with tab3:
            st.subheader("Detailed Text Report")
            st.text_area("Report", report_text, height=500)

               # ---------- Save to SQL table agri_finance_reports ----------
        insert_sql = """
            INSERT INTO agri_finance_reports (
                farmer_name,
                country,
                crop,
                current_year,
                farm_size_ha,
                loan_amount_usd,
                annual_interest_rate,
                tenure_months,
                report_text,
                expected_yield_ton_per_ha,
                expected_revenue_usd_per_ha,
                expected_profit_usd_per_ha,
                risk_level
            )
            VALUES (
                %(farmer_name)s,
                %(country)s,
                %(crop)s,
                %(current_year)s,
                %(farm_size_ha)s,
                %(loan_amount_usd)s,
                %(annual_interest_rate)s,
                %(tenure_months)s,
                %(report_text)s,
                %(expected_yield_ton_per_ha)s,
                %(expected_revenue_usd_per_ha)s,
                %(expected_profit_usd_per_ha)s,
                %(risk_level)s
            )
        """

        params = {
            "farmer_name": farmer_name,
            "country": country,
            "crop": crop,
            "current_year": current_year,
            "farm_size_ha": farm_size_ha,
            "loan_amount_usd": loan_amount_usd,
            "annual_interest_rate": annual_interest_rate,
            "tenure_months": tenure_months,
            "report_text": report_text,
            "expected_yield_ton_per_ha": summary["predicted_yield_ton_per_ha"],
            "expected_revenue_usd_per_ha": summary["revenue_usd"],
            "expected_profit_usd_per_ha": summary["profit_usd"],
            "risk_level": summary["decision_text"],
        }

        try:
            with engine.begin() as conn:
                # 👇 use exec_driver_sql instead of execute
                conn.exec_driver_sql(insert_sql, params)
            st.success("✅ Report saved to agri_finance_reports")
        except Exception as e:
            st.error(f"❌ Error saving to SQL: {e}")
