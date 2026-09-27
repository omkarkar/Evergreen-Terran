import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from pathlib import Path
import joblib

st.set_page_config(page_title="Asia Yield/Rainfall Map", layout="wide")

GEO = Path("data/asia_countries.geojson")
CSV = Path("training_yield.csv")
MODEL = Path("yield_model_rf.pkl")

st.title(" Asia Choropleth — Yield, Predicted Yield, Rainfall")

# ---- Load Geo ----
if not GEO.exists():
    st.error("GeoJSON not found. Expected: data/asia_countries.geojson")
    st.stop()
gdf = gpd.read_file(GEO)

# ---- Load data ----
if not CSV.exists():
    st.error("training_yield.csv not found. Run your feature-store build first.")
    st.stop()

df = pd.read_csv(CSV)

# Keep required columns if present
needed_cols = ["region_key","year_key","target_yield","soil_pH","soil_soc","soil_nitrogen","rain_mm_year","temp_mean_year"]
df = df[[c for c in needed_cols if c in df.columns]].copy()

# Basic cleaning
df = df.dropna(subset=["region_key","year_key"])
df["year_key"] = pd.to_numeric(df["year_key"], errors="coerce")
df = df.dropna(subset=["year_key"])

# Latest year per region
idx = df.groupby("region_key")["year_key"].idxmax()
latest = df.loc[idx].copy()

# Load model (optional for predicted map)
model = joblib.load(MODEL) if MODEL.exists() else None
if model is None:
    st.info("Model file not found (yield_model_rf.pkl). 'Predicted Yield' option will be disabled.")

# Sidebar
metric = st.sidebar.selectbox(
    "Metric",
    options=(["Actual Yield","Rainfall (mm)"] + (["Predicted Yield"] if model is not None else [])),
    index=0
)
country = st.sidebar.selectbox("Filter country (optional)", ["(All)"] + sorted(gdf["ADMIN"].astype(str).unique().tolist()))

# Name fixes to match your region names (adjust as needed)
name_fix = {
    "Viet Nam": "Vietnam",
    "Korea, Republic of": "South Korea",
    "Korea, Democratic People's Republic of": "North Korea",
    "Lao PDR": "Laos",
    "Timor-Leste": "East Timor",
    "Russian Federation": "Russia",
    "Iran (Islamic Republic of)": "Iran",
    "Syrian Arab Republic": "Syria",
    "Türkiye": "Turkey",
}
gdf["ADMIN"] = gdf["ADMIN"].astype(str).replace(name_fix)

# Build a value column based on selection
val_col = None
if metric == "Actual Yield":
    val_col = "target_yield"
elif metric == "Rainfall (mm)":
    val_col = "rain_mm_year"
elif metric == "Predicted Yield":
    # compute prediction row-wise from the features
    feats = ["soil_pH","soil_soc","soil_nitrogen","rain_mm_year","temp_mean_year"]
    miss = [c for c in feats if c not in latest.columns]
    if miss:
        st.error(f"Missing feature columns for prediction: {miss}")
        st.stop()
    X = latest[feats].copy()
    latest["predicted_yield"] = model.predict(X)
    val_col = "predicted_yield"

# Prepare table for merge
map_df = latest[["region_key", val_col]].rename(columns={"region_key":"ADMIN"}).copy()

# Optional single-country filter
if country != "(All)":
    gdf = gdf[gdf["ADMIN"] == country]

merged = gdf.merge(map_df, on="ADMIN", how="left")

# Map title/legend
legend = "Yield (t/ha)" if "Yield" in metric else "Rainfall (mm)"
center = [23, 90]  # South Asia-ish center

m = folium.Map(location=center, zoom_start=3, tiles="cartodbpositron")
ch = folium.Choropleth(
    geo_data=merged.to_json(),
    data=merged,
    columns=["ADMIN", val_col],
    key_on="feature.properties.ADMIN",
    fill_color="YlGn",
    fill_opacity=0.85,
    line_opacity=0.25,
    nan_fill_color="lightgrey",
    legend_name=legend
)
ch.add_to(m)

folium.GeoJsonTooltip(
    fields=["ADMIN", val_col],
    aliases=["Country", legend],
    localize=True,
    sticky=False
).add_to(ch.geojson)

st_folium(m, width=1100, height=650)

# Show a small table of values beneath
st.markdown("### Data used for map")
st.dataframe(merged[["ADMIN", val_col]].rename(columns={val_col:legend}).sort_values(by=legend, ascending=False).head(50))
