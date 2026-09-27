import geopandas as gpd
import pandas as pd
from pathlib import Path
import urllib.request, shutil, sys

DATA = Path("data")
DATA.mkdir(exist_ok=True)

# Try multiple mirrors for the Natural Earth Admin-0 countries zip
CANDIDATE_URLS = [
    # Official Natural Earth (sometimes slow)
    "https://www.naturalearthdata.com/http//www.naturalearthdata.com/download/110m/cultural/ne_110m_admin_0_countries.zip",
    # GitHub mirror (Kelso repo)
    "https://github.com/nvkelso/natural-earth-vector/releases/download/v5.1.2/ne_110m_admin_0_countries.zip",
    # Another mirror (common forks)
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"
]

zip_path = DATA / "ne_110m_admin_0_countries.zip"
geojson_direct = DATA / "ne_110m_admin_0_countries.geojson"
asia_out = DATA / "asia_countries.geojson"

def download(url, path):
    print(f"Downloading: {url}")
    with urllib.request.urlopen(url) as r, open(path, "wb") as f:
        shutil.copyfileobj(r, f)
    print(f"Saved -> {path}")

# 1) Try to fetch a ZIP first; if we only get a GeoJSON, well use that directly
source_type = None
for url in CANDIDATE_URLS:
    try:
        if url.lower().endswith(".zip"):
            download(url, zip_path)
            source_type = "zip"
            break
        elif url.lower().endswith(".geojson"):
            download(url, geojson_direct)
            source_type = "geojson"
            break
    except Exception as e:
        print(f"Failed: {e}")
        continue

if source_type is None:
    sys.exit(" Could not download Natural Earth from any mirror.")

# 2) Load world countries
if source_type == "zip":
    # Read straight from zip without extracting
    # The shapefile name inside the zip is usually 'ne_110m_admin_0_countries.shp'
    shp_inside = "ne_110m_admin_0_countries.shp"
    zip_uri = f"zip:///{zip_path.as_posix()}!{shp_inside}"
    world = gpd.read_file(zip_uri)
else:
    world = gpd.read_file(geojson_direct)

print("Columns available:", list(world.columns))

# 3) Robustly pick continent and name/admin columns
def pick(df, cands):
    for c in cands:
        if c in df.columns:
            return c
    return None

continent_col = pick(world, ["CONTINENT","continent"])
name_col = pick(world, ["ADMIN","admin","NAME_LONG","NAME","name"])

if continent_col is None:
    # Some mirrors may lack CONTINENT; try to infer via region_wb if present
    continent_col = pick(world, ["region_un","REGION_UN","region_wb","REGION_WB"])
    if continent_col is None:
        # fallback: assume everything, then well filter known list
        world["__continent__"] = "Asia"
        continent_col = "__continent__"

# Filter to Asia
asia = world[world[continent_col].str.contains("Asia", case=False, na=False)].copy()

# Create a stable ADMIN column for joins with your data (region_key=country)
if name_col is None:
    # last resort: try ISO name fields
    name_col = pick(asia, ["SOVEREIGNT","SOVEREIGN","BRK_NAME","NAME_EN","NAME"])
asia["ADMIN"] = asia[name_col].astype(str)

# 4) Save to GeoJSON
asia.to_file(asia_out, driver="GeoJSON")
print(f" Saved Asian country boundaries -> {asia_out}")
print(asia[["ADMIN"]].head())
