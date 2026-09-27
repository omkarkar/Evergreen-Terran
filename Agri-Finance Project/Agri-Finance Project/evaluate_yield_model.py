import os
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)

from db_engine import engine


# ============================================================
# 1. SETTINGS
# ============================================================

TARGET = "yield_ton_per_ha"

OUTPUT_FOLDER = "model_evaluation_results"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# ============================================================
# 2. LOAD SAVED MODEL
# ============================================================

print("=" * 70)
print("EVERGREEN TERRAN - YIELD MODEL EVALUATION")
print("=" * 70)

print("\nLoading saved model...")

bundle = joblib.load("yield_model_bundle.joblib")

model = bundle["yield_model"]
best_model_name = bundle["best_model_name"]
all_metrics = bundle["all_metrics"]

numeric_features = bundle["numeric_features"]
categorical_features = bundle["categorical_features"]

print("Model loaded successfully.")
print("Best Model:", best_model_name)


# ============================================================
# 3. LOAD ORIGINAL DATA
# ============================================================

print("\nLoading yield_panel from PostgreSQL...")

df = pd.read_sql(
    "SELECT * FROM yield_panel",
    engine
)

print("Raw dataset rows:", len(df))


# ============================================================
# 4. PREPARE SAME DATA AS ORIGINAL TRAINING
# ============================================================

model_columns = (
    numeric_features
    + categorical_features
    + [TARGET]
)

model_df = df[model_columns].dropna().copy()

X = model_df[
    numeric_features + categorical_features
]

y = model_df[TARGET]

print("Usable modelling rows:", len(model_df))


# ============================================================
# 5. RECREATE ORIGINAL 80/20 SPLIT
# ============================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42
)

print("\nTotal samples   :", len(X))
print("Training samples:", len(X_train))
print("Testing samples :", len(X_test))


# ============================================================
# 6. ORIGINAL 5-FOLD CROSS-VALIDATION RESULTS
# ============================================================

print("\n" + "=" * 70)
print("5-FOLD CROSS-VALIDATION MODEL COMPARISON")
print("=" * 70)

comparison_rows = []

for name, metrics in all_metrics.items():

    comparison_rows.append({
        "Model": name,
        "CV_RMSE_Mean": metrics["cv_rmse_mean"],
        "CV_RMSE_Std": metrics["cv_rmse_std"]
    })

comparison_df = pd.DataFrame(comparison_rows)

comparison_df = comparison_df.sort_values(
    "CV_RMSE_Mean"
).reset_index(drop=True)

print(
    comparison_df.to_string(
        index=False,
        float_format=lambda x: f"{x:.3f}"
    )
)

comparison_df.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "model_comparison.csv"
    ),
    index=False
)


# ============================================================
# 7. TRAINING SET PERFORMANCE
# ============================================================

train_pred = model.predict(X_train)

train_mae = mean_absolute_error(
    y_train,
    train_pred
)

train_rmse = np.sqrt(
    mean_squared_error(
        y_train,
        train_pred
    )
)

train_r2 = r2_score(
    y_train,
    train_pred
)


# ============================================================
# 8. TEST SET PERFORMANCE
# ============================================================

test_pred = model.predict(X_test)

test_mae = mean_absolute_error(
    y_test,
    test_pred
)

test_rmse = np.sqrt(
    mean_squared_error(
        y_test,
        test_pred
    )
)

test_r2 = r2_score(
    y_test,
    test_pred
)


print("\n" + "=" * 70)
print("FINAL RANDOM FOREST PERFORMANCE")
print("=" * 70)

print("\nTRAINING SET")
print(f"MAE  : {train_mae:.3f} t/ha")
print(f"RMSE : {train_rmse:.3f} t/ha")
print(f"R2   : {train_r2:.3f}")

print("\nTEST SET")
print(f"MAE  : {test_mae:.3f} t/ha")
print(f"RMSE : {test_rmse:.3f} t/ha")
print(f"R2   : {test_r2:.3f}")


# ============================================================
# 9. SAVE PERFORMANCE TABLE
# ============================================================

performance_df = pd.DataFrame({
    "Dataset": [
        "Training",
        "Testing"
    ],

    "MAE_t_ha": [
        train_mae,
        test_mae
    ],

    "RMSE_t_ha": [
        train_rmse,
        test_rmse
    ],

    "R2": [
        train_r2,
        test_r2
    ]
})

performance_df.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "train_test_performance.csv"
    ),
    index=False
)


# ============================================================
# 10. SAVE TEST PREDICTIONS
# ============================================================

predictions_df = pd.DataFrame({
    "Actual_Yield_t_ha":
        y_test.to_numpy(),

    "Predicted_Yield_t_ha":
        test_pred
})

predictions_df["Residual"] = (
    predictions_df["Actual_Yield_t_ha"]
    -
    predictions_df["Predicted_Yield_t_ha"]
)

predictions_df["Absolute_Error"] = (
    predictions_df["Residual"].abs()
)

predictions_df.to_csv(
    os.path.join(
        OUTPUT_FOLDER,
        "test_predictions.csv"
    ),
    index=False
)


# ============================================================
# 11. MODEL COMPARISON GRAPH
# ============================================================

plt.figure(figsize=(10, 6))

plt.bar(
    comparison_df["Model"],
    comparison_df["CV_RMSE_Mean"],
    yerr=comparison_df["CV_RMSE_Std"],
    capsize=5
)

plt.xlabel("Machine Learning Model")
plt.ylabel("5-Fold CV RMSE (t/ha)")
plt.title("Cross-Validation Performance of Yield Models")

plt.xticks(
    rotation=25,
    ha="right"
)

plt.tight_layout()

plt.savefig(
    os.path.join(
        OUTPUT_FOLDER,
        "model_rmse_comparison.png"
    ),
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# ============================================================
# 12. ACTUAL VS PREDICTED GRAPH
# ============================================================

plt.figure(figsize=(8, 7))

plt.scatter(
    y_test,
    test_pred,
    alpha=0.5
)

minimum = min(
    y_test.min(),
    test_pred.min()
)

maximum = max(
    y_test.max(),
    test_pred.max()
)

plt.plot(
    [minimum, maximum],
    [minimum, maximum],
    linestyle="--"
)

plt.xlabel("Actual Yield (t/ha)")
plt.ylabel("Predicted Yield (t/ha)")
plt.title("Actual vs Predicted Crop Yield")

plt.tight_layout()

plt.savefig(
    os.path.join(
        OUTPUT_FOLDER,
        "actual_vs_predicted.png"
    ),
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# ============================================================
# 13. RESIDUAL DISTRIBUTION
# ============================================================

residuals = (
    y_test.to_numpy()
    -
    test_pred
)

plt.figure(figsize=(8, 6))

plt.hist(
    residuals,
    bins=30
)

plt.xlabel("Residual Error (Actual - Predicted)")
plt.ylabel("Frequency")
plt.title("Distribution of Yield Prediction Errors")

plt.tight_layout()

plt.savefig(
    os.path.join(
        OUTPUT_FOLDER,
        "residual_distribution.png"
    ),
    dpi=300,
    bbox_inches="tight"
)

plt.close()


# ============================================================
# 14. FEATURE IMPORTANCE
# ============================================================

print("\n" + "=" * 70)
print("FEATURE IMPORTANCE")
print("=" * 70)

try:

    preprocessor = model.named_steps["preprocess"]
    final_model = model.named_steps["model"]

    feature_names = (
        preprocessor.get_feature_names_out()
    )

    if hasattr(
        final_model,
        "feature_importances_"
    ):

        importance_df = pd.DataFrame({
            "Feature": feature_names,
            "Importance":
                final_model.feature_importances_
        })

        importance_df = (
            importance_df
            .sort_values(
                "Importance",
                ascending=False
            )
            .reset_index(drop=True)
        )

        importance_df.to_csv(
            os.path.join(
                OUTPUT_FOLDER,
                "feature_importance.csv"
            ),
            index=False
        )

        print("\nTop 20 Features:")

        print(
            importance_df
            .head(20)
            .to_string(index=False)
        )

        top20 = (
            importance_df
            .head(20)
            .sort_values("Importance")
        )

        plt.figure(figsize=(10, 8))

        plt.barh(
            top20["Feature"],
            top20["Importance"]
        )

        plt.xlabel("Feature Importance")
        plt.ylabel("Feature")

        plt.title(
            "Top 20 Random Forest Feature Importances"
        )

        plt.tight_layout()

        plt.savefig(
            os.path.join(
                OUTPUT_FOLDER,
                "feature_importance.png"
            ),
            dpi=300,
            bbox_inches="tight"
        )

        plt.close()

    else:

        print(
            "Feature importance is not available "
            "for this model."
        )

except Exception as e:

    print(
        "Feature importance could not be generated:"
    )

    print(e)


# ============================================================
# 15. CREATE THESIS SUMMARY FILE
# ============================================================

summary_path = os.path.join(
    OUTPUT_FOLDER,
    "evaluation_summary.txt"
)

with open(
    summary_path,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "EVERGREEN TERRAN\n"
    )

    f.write(
        "YIELD MODEL TRAINING AND EVALUATION RESULTS\n"
    )

    f.write(
        "=" * 70 + "\n\n"
    )

    f.write(
        f"Selected Model: {best_model_name}\n\n"
    )

    f.write(
        "DATASET INFORMATION\n"
    )

    f.write(
        "-" * 40 + "\n"
    )

    f.write(
        f"Raw yield_panel rows: {len(df)}\n"
    )

    f.write(
        f"Usable modelling samples: {len(X)}\n"
    )

    f.write(
        f"Training samples: {len(X_train)}\n"
    )

    f.write(
        f"Testing samples: {len(X_test)}\n"
    )

    f.write(
        "Train/Test split: 80/20\n"
    )

    f.write(
        "Random state: 42\n"
    )

    f.write(
        "Cross-validation: 5-fold\n\n"
    )


    f.write(
        "MODEL COMPARISON\n"
    )

    f.write(
        "-" * 40 + "\n"
    )

    f.write(
        comparison_df.to_string(
            index=False
        )
    )


    f.write(
        "\n\nTRAINING PERFORMANCE\n"
    )

    f.write(
        "-" * 40 + "\n"
    )

    f.write(
        f"MAE: {train_mae:.3f} t/ha\n"
    )

    f.write(
        f"RMSE: {train_rmse:.3f} t/ha\n"
    )

    f.write(
        f"R2: {train_r2:.3f}\n"
    )


    f.write(
        "\nTEST PERFORMANCE\n"
    )

    f.write(
        "-" * 40 + "\n"
    )

    f.write(
        f"MAE: {test_mae:.3f} t/ha\n"
    )

    f.write(
        f"RMSE: {test_rmse:.3f} t/ha\n"
    )

    f.write(
        f"R2: {test_r2:.3f}\n"
    )


print("\n" + "=" * 70)
print("EVALUATION COMPLETED SUCCESSFULLY")
print("=" * 70)

print("\nResults saved in folder:")
print(OUTPUT_FOLDER)