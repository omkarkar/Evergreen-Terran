import pandas as pd
import numpy as np

from db_engine import engine

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, r2_score

from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.svm import SVR

from xgboost import XGBRegressor
from lightgbm import LGBMRegressor

import joblib


def build_preprocessor(numeric_features, categorical_features):
    """
    Build the ColumnTransformer used in all models.
    """
    return ColumnTransformer(
        transformers=[
            ("num", "passthrough", numeric_features),
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
        ]
    )


def get_yield_models():
    """
    Define all algorithms we want to test for yield prediction.
    """
    models = {
        "random_forest": RandomForestRegressor(
            n_estimators=200,
            random_state=42,
            n_jobs=-1,
        ),
        "gradient_boosting": GradientBoostingRegressor(
            random_state=42
        ),
        "xgboost": XGBRegressor(
            n_estimators=400,
            learning_rate=0.05,
            max_depth=6,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
        ),
        "lightgbm": LGBMRegressor(
            n_estimators=400,
            learning_rate=0.05,
            num_leaves=31,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
        ),
        "svr_rbf": SVR(
            kernel="rbf",
            C=10.0,
            epsilon=0.1,
        ),
    }
    return models


def train_yield_model():
    # ------------------------------------------------------------------
    # 1. Load data
    # ------------------------------------------------------------------
    df = pd.read_sql("SELECT * FROM yield_panel", engine)

    target_col = "yield_ton_per_ha"
    numeric_features = [
        "year",
        "tavg_c", "rh_pct", "prcp_mm",
        "tavg_c_anom", "prcp_mm_anom",
        "fert_k_kg_ha", "fert_n_kg_ha", "fert_p_kg_ha",
        "soil_ph_top30_mean", "soil_soc_top30_gkg", "soil_n_top30_gkg",
    ]
    categorical_features = ["country", "crop"]

    model_cols = numeric_features + categorical_features + [target_col]
    model_df = df[model_cols].dropna()

    X = model_df[numeric_features + categorical_features]
    y = model_df[target_col]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # ------------------------------------------------------------------
    # 2. Build preprocessor + all candidate models
    # ------------------------------------------------------------------
    preprocess = build_preprocessor(numeric_features, categorical_features)
    base_models = get_yield_models()

    best_model_name = None
    best_rmse = float("inf")
    best_pipeline = None
    all_metrics = {}

    # ------------------------------------------------------------------
    # 3. Loop over models, do cross-validation, pick best
    # ------------------------------------------------------------------
    for name, model in base_models.items():
        print(f"\n🔍 Evaluating model: {name}")

        pipe = Pipeline(
            steps=[
                ("preprocess", preprocess),
                ("model", model),
            ]
        )

        # 5-fold CV on training data
        scores = cross_val_score(
            pipe,
            X_train,
            y_train,
            cv=5,
            scoring="neg_mean_squared_error",
            n_jobs=-1,
        )
        rmse_scores = np.sqrt(-scores)
        avg_rmse = rmse_scores.mean()
        std_rmse = rmse_scores.std()

        print(f"  CV RMSE mean={avg_rmse:.3f}, std={std_rmse:.3f}")

        all_metrics[name] = {
            "cv_rmse_mean": float(avg_rmse),
            "cv_rmse_std": float(std_rmse),
        }

        if avg_rmse < best_rmse:
            best_rmse = avg_rmse
            best_model_name = name
            best_pipeline = pipe

    print(f"\n🏆 Best CV model: {best_model_name} (RMSE={best_rmse:.3f})")

    # ------------------------------------------------------------------
    # 4. Fit best model on full training data and evaluate on test set
    # ------------------------------------------------------------------
    best_pipeline.fit(X_train, y_train)

    y_pred = best_pipeline.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    print(f"Test MAE={mae:.3f}, R²={r2:.3f}")

    # ------------------------------------------------------------------
    # 5. Compute metadata
    # ------------------------------------------------------------------
    GLOBAL_YIELD_NUMERIC_MEANS = X_train[numeric_features].mean()
    ALL_YIELD_COUNTRIES = sorted(df["country"].dropna().unique())
    ALL_YIELD_CROPS = sorted(df["crop"].dropna().unique())

    # ------------------------------------------------------------------
    # 6. Save bundle
    # ------------------------------------------------------------------
    bundle = {
        "yield_model": best_pipeline,
        "best_model_name": best_model_name,
        "all_metrics": all_metrics,
        "GLOBAL_YIELD_NUMERIC_MEANS": GLOBAL_YIELD_NUMERIC_MEANS,
        "numeric_features": numeric_features,
        "categorical_features": categorical_features,
        "ALL_YIELD_COUNTRIES": ALL_YIELD_COUNTRIES,
        "ALL_YIELD_CROPS": ALL_YIELD_CROPS,
    }

    joblib.dump(bundle, "yield_model_bundle.joblib")
    print("✅ yield_model_bundle.joblib saved")


if __name__ == "__main__":
    train_yield_model()
