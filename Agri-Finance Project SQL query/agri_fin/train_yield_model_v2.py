import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline  #  important
import joblib

csv = Path("training_yield_v2.csv")
df = pd.read_csv(csv)

# ----- choose columns present -----
base_num = ["soil_pH","soil_soc","soil_nitrogen","rain_mm_year","temp_mean_year","fert_index","wdi_agri_value_added"]
base_num = [c for c in base_num if c in df.columns]
imf_cols = [c for c in df.columns if c.startswith("imf_")]
num_cols = base_num + imf_cols
cat_cols = [c for c in ["crop"] if c in df.columns]

# keep rows with target
df = df.dropna(subset=["target_yield"]).copy()
X = df[num_cols + cat_cols].copy()
y = df["target_yield"].astype(float)

# ----- preprocessors -----
numeric_tf = Pipeline(steps=[
    ("imputer", SimpleImputer(strategy="median"))
])

categorical_tf = Pipeline(steps=[
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("onehot", OneHotEncoder(handle_unknown="ignore"))
])

preprocess = ColumnTransformer(
    transformers=[
        ("num", numeric_tf, num_cols),
        ("cat", categorical_tf, cat_cols)
    ],
    remainder="drop"
)

# ----- model -----
rf = RandomForestRegressor(
    n_estimators=500,
    max_depth=12,
    random_state=42,
    n_jobs=-1
)

pipe = Pipeline(steps=[("preprocess", preprocess),
                      ("model", rf)])

# split
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)

# fit
pipe.fit(Xtr, ytr)

# eval
yp = pipe.predict(Xte)
mae  = mean_absolute_error(yte, yp)
rmse = np.sqrt(mean_squared_error(yte, yp))   # safe for any sklearn
r2   = r2_score(yte, yp)
print(f"MAE={mae:.4f}  RMSE={rmse:.4f}  R2={r2:.4f}")

# try feature importances
feature_names = []
feature_names += num_cols
try:
    oh = pipe.named_steps["preprocess"].named_transformers_["cat"].named_steps["onehot"]
    cat_names = oh.get_feature_names_out(cat_cols).tolist()
    feature_names += cat_names
except Exception:
    pass

try:
    importances = pipe.named_steps["model"].feature_importances_
    fi = pd.Series(importances, index=feature_names).sort_values(ascending=False)
    fi.to_csv("feature_importance_v2.csv", header=["importance"])
    print("\nTop features:")
    print(fi.head(15))
except Exception:
    print("Note: could not extract tree importances.")

# save artifacts
joblib.dump(pipe, "yield_model_rf_v2.pkl")
pd.DataFrame({"y_true": yte, "y_pred": yp}).to_csv("test_predictions_v2.csv", index=False)
print("\n Saved: yield_model_rf_v2.pkl, feature_importance_v2.csv, test_predictions_v2.csv")
