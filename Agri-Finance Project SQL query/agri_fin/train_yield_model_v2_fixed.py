import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
import joblib

csv = Path("training_yield_v2.csv")
df = pd.read_csv(csv)

# Select available numeric features
base_num = ["soil_pH","soil_soc","soil_nitrogen","rain_mm_year","temp_mean_year","fert_index","wdi_agri_value_added"]
imf_cols = [c for c in df.columns if c.startswith("imf_")]
num_cols = [c for c in (base_num + imf_cols) if c in df.columns]

# Drop columns that are entirely NaN
all_nan = [c for c in num_cols if df[c].isna().all()]
num_cols = [c for c in num_cols if c not in all_nan]

cat_cols = [c for c in ["crop"] if c in df.columns]

print("Using numeric features:", num_cols)
print("Dropping all-NaN features:", all_nan)

# Target
df = df.dropna(subset=["target_yield"]).copy()
y_raw = df["target_yield"].astype(float)
X = df[num_cols + cat_cols].copy()

# Optional: log-transform target
use_log = True
y = np.log1p(y_raw) if use_log else y_raw

# Pipelines
numeric_tf = Pipeline([("imputer", SimpleImputer(strategy="median"))])
categorical_tf = Pipeline([("imputer", SimpleImputer(strategy="most_frequent")),
                           ("onehot", OneHotEncoder(handle_unknown="ignore"))])

preprocess = ColumnTransformer([
    ("num", numeric_tf, num_cols),
    ("cat", categorical_tf, cat_cols)
], remainder="drop")

rf = RandomForestRegressor(n_estimators=600, max_depth=14, random_state=42, n_jobs=-1)
pipe = Pipeline([("preprocess", preprocess), ("model", rf)])

Xtr, Xte, ytr_raw, yte_raw = train_test_split(X, y_raw, test_size=0.2, random_state=42)
ytr = np.log1p(ytr_raw) if use_log else ytr_raw

pipe.fit(Xtr, ytr)

# Predict on original scale
yp_t = pipe.predict(Xte)
yp = np.expm1(yp_t) if use_log else yp_t

mae  = mean_absolute_error(yte_raw, yp)
rmse = np.sqrt(mean_squared_error(yte_raw, yp))
r2   = r2_score(yte_raw, yp)
print(f"MAE={mae:.4f}  RMSE={rmse:.4f}  R2={r2:.4f}")

# Try feature importances
feat_names = []
feat_names += num_cols
try:
    oh = pipe.named_steps["preprocess"].named_transformers_["cat"].named_steps["onehot"]
    cat_names = oh.get_feature_names_out(cat_cols).tolist()
    feat_names += cat_names
except Exception:
    pass

try:
    importances = pipe.named_steps["model"].feature_importances_
    fi = pd.Series(importances, index=feat_names).sort_values(ascending=False)
    fi.to_csv("feature_importance_v2.csv", header=["importance"])
    print("\nTop features:\n", fi.head(15))
except Exception:
    print("Note: could not extract tree importances.")

# Save artifacts
joblib.dump(pipe, "yield_model_rf_v2.pkl")
pd.DataFrame({"y_true": yte_raw, "y_pred": yp}).to_csv("test_predictions_v2.csv", index=False)
print("\n Saved: yield_model_rf_v2.pkl, feature_importance_v2.csv, test_predictions_v2.csv")
