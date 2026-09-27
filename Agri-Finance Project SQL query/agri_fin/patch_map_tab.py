import re, pathlib
p = pathlib.Path("app.py")
src = p.read_text(encoding="utf-8", errors="ignore")

# Replace the existing Map tab block by a version with "Predicted Yield"
new_block = r"""
with tab4:
    st.subheader("Asia Choropleth")
    if not GEO_PATH.exists():
        st.info("GeoJSON not found. Expected: data/asia_countries.geojson")
    else:
        import geopandas as gpd
        import folium
        from streamlit_folium import st_folium

        gdf = gpd.read_file(GEO_PATH)

        # latest per country from training CSV
        if df_train.empty:
            st.warning("training_yield_v2.csv not loaded. Map will be empty.")
            latest = pd.DataFrame(columns=["ADMIN","target_yield","rain_mm_year","temp_mean_year","soil_pH","soil_soc","soil_nitrogen"])
        else:
            tmp = df_train.dropna(subset=["region_key","year_key"]).copy()
            tmp["year_key"] = pd.to_numeric(tmp["year_key"], errors="coerce")
            tmp = tmp.dropna(subset=["year_key"])
            idx = tmp.groupby("region_key")["year_key"].idxmax()
            cols = [c for c in ["region_key","target_yield","rain_mm_year","temp_mean_year","soil_pH","soil_soc","soil_nitrogen"] if c in tmp.columns]
            latest = tmp.loc[idx, cols].rename(columns={"region_key":"ADMIN"})

        # name fixes for common mismatches
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
        if "ADMIN" in gdf.columns:
            gdf["ADMIN"] = gdf["ADMIN"].astype(str).replace(name_fix)

        # If model present, compute predictions per country for latest year
        pred_available = False
        try:
            mpath = Path("yield_model_rf_v2.pkl")
            if mpath.exists():
                import joblib
                model = joblib.load(mpath)
                feats = [c for c in ["soil_pH","soil_soc","soil_nitrogen","rain_mm_year","temp_mean_year"] if c in latest.columns]
                if feats:
                    latest["predicted_yield"] = model.predict(latest[feats].fillna(latest[feats].median()))
                    pred_available = True
        except Exception as e:
            st.warning(f"Prediction disabled: {e}")

        options = ["Actual Yield", "Rainfall (mm)", "Mean Temp (C)"]
        if pred_available:
            options.insert(1, "Predicted Yield")
        metric = st.radio("Map metric", options, horizontal=True)

        mapper = {
            "Actual Yield": ("target_yield", "Yield (t/ha)"),
            "Predicted Yield": ("predicted_yield", "Predicted (t/ha)"),
            "Rainfall (mm)": ("rain_mm_year", "Rainfall (mm)"),
            "Mean Temp (C)": ("temp_mean_year", "Mean Temp (C)")
        }
        val_col, legend = mapper[metric]

        merged = gdf.merge(latest, on="ADMIN", how="left")
        m = folium.Map(location=[23, 90], zoom_start=3, tiles="cartodbpositron")
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

        st_folium(m, width=1100, height=620)
"""

# naive replace: find the start of 'with tab4:' and replace through the next st_folium call
out = re.sub(r"with tab4:[\s\S]*?st_folium\(.*?\)\s*", new_block, src, flags=re.M)
p.write_text(out, encoding="utf-8")
print("Patched app.py map tab with Predicted Yield option.")
