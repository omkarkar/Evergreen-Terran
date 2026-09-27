import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import numpy as np
import joblib

# 1 Load dataset
csv = Path("training_yield.csv")
df = pd.read_csv(csv)

# 2 Drop rows with missing numeric data
needed = ["target_yield","soil_pH","soil_soc","soil_nitrogen","rain_mm_year","temp_mean_year"]
df = df.dropna(subset=needed)

# 3 Define features & target
X = df[["soil_pH","soil_soc","soil_nitrogen","rain_mm_year","temp_mean_year"]]
y = df["target_yield"]

# 4 Train / test split
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)

# 5 Train model
rf = RandomForestRegressor(
    n_estimators=400,
    max_depth=10,
    random_state=42,
    n_jobs=-1
)
rf.fit(Xtr, ytr)

# 6 Evaluate
yp = rf.predict(Xte)
mae  = mean_absolute_error(yte, yp)
rmse = np.sqrt(mean_squared_error(yte, yp))   #  fixed line
r2   = r2_score(yte, yp)

print(f"MAE={mae:.4f}  RMSE={rmse:.4f}  R2={r2:.4f}")

# 7 Feature importance
fi = pd.Series(rf.feature_importances_, index=X.columns).sort_values(ascending=False)
print("\nFeature importance:")
print(fi)

# 8 Save outputs
fi.to_csv("feature_importance.csv", header=["importance"])
joblib.dump(rf, "yield_model_rf.pkl")
pd.DataFrame({"y_true": yte, "y_pred": yp}).to_csv("test_predictions.csv", index=False)

print("\n Saved: yield_model_rf.pkl, feature_importance.csv, test_predictions.csv")
