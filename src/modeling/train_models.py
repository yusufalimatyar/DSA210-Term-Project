"""Course-aligned modeling pipeline (Week7-Week11): LR, RF, GBR, CV, VIF.

Key improvements over initial baseline:
1. Lagged features based on within-country Spearman optimal lags
2. Country-demeaning (centering, Week7) as feature engineering option
3. StandardScaler for numeric features in pipeline (Week8)
4. Reduced categorical features: country_group only (3 categories)
5. VIF diagnostics integrated per feature set (Week7)
6. Feature importance reports for tree models (Week8, Week10)
7. Residual analysis plots for Linear Regression (Week7)
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from joblib import dump
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold, ParameterGrid, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from statsmodels.stats.outliers_influence import variance_inflation_factor


DATA_PATH = Path("data/processed/final_oecd.csv")
PROCESSED_DIR = Path("data/processed")
MODELS_DIR = Path("models")
OUTPUTS_MODELS_DIR = Path("outputs/models")

TARGET = "fertility_rate"

# Core economic features (strong signals in statistical analysis)
CORE_FEATURES = [
    "inflation",
    "unemployment_total",
    "female_labor_force_participation",
    "gdp_per_capita",
    "marriage_rate",
]

# Optimal lags from within-country Spearman correlation analysis (AGENTS.md §3)
OPTIMAL_LAGS: dict[str, int] = {
    "marriage_rate": 2,          # rho=+0.53, strongest relationship
    "gdp_per_capita": 5,         # rho=-0.49, strong negative
    "female_labor_force_participation": 5,  # rho=-0.35, delayed negative
    "inflation": 4,              # rho=+0.16, moderate delayed
    "unemployment_total": 2,     # rho=-0.10, delayed insecurity effect
}

LAG_FEATURE_NAMES = [f"{f}_lag{OPTIMAL_LAGS[f]}" for f in OPTIMAL_LAGS]

# Only country_group as categorical (3 categories: developed, transition, special_case)
# Reduced from region_tag(9)+income_level(2)+country_group(3) to avoid overfitting
CATEGORICAL_FEATURES = ["country_group"]


def _build_feature_sets() -> dict[str, dict]:
    """Define feature sets for systematic model comparison."""
    core_dm = [f"{f}_dm" for f in CORE_FEATURES]
    lag_dm = [f"{lf}_dm" for lf in LAG_FEATURE_NAMES]
    return {
        "core": {
            "numeric": list(CORE_FEATURES),
            "categorical": list(CATEGORICAL_FEATURES),
        },
        "core_lagged": {
            "numeric": list(CORE_FEATURES) + list(LAG_FEATURE_NAMES),
            "categorical": list(CATEGORICAL_FEATURES),
        },
        "demeaned_lagged": {
            "numeric": core_dm + lag_dm,
            "categorical": list(CATEGORICAL_FEATURES),
        },
    }


FEATURE_SETS = _build_feature_sets()


def ensure_dirs() -> None:
    for d in [PROCESSED_DIR, MODELS_DIR, OUTPUTS_MODELS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------
def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create per-country lagged features using optimal lag structure."""
    out = df.sort_values(["country_code", "year"]).copy()
    for feat, lag in OPTIMAL_LAGS.items():
        out[f"{feat}_lag{lag}"] = out.groupby("country_code")[feat].shift(lag)
    return out


def add_demeaned_features(
    df: pd.DataFrame,
    cols: list[str],
    country_means: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Country-demean (center) numeric columns (Week7 centering).

    Uses training-set country means to prevent data leakage.
    """
    out = df.copy()
    if country_means is None:
        country_means = df.groupby("country_code")[cols].mean()
    for col in cols:
        out[f"{col}_dm"] = out[col] - out["country_code"].map(country_means[col])
    return out, country_means


# ---------------------------------------------------------------------------
# Data loading & splitting
# ---------------------------------------------------------------------------
def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    needed = (
        ["country", "country_code", "year", TARGET]
        + CORE_FEATURES
        + CATEGORICAL_FEATURES
    )
    return df[needed].dropna().sort_values(["year", "country_code"]).reset_index(drop=True)


def split_by_year(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train = df[df["year"] <= 2018].copy()
    val = df[(df["year"] >= 2019) & (df["year"] <= 2021)].copy()
    test = df[df["year"] >= 2022].copy()
    return train, val, test


# ---------------------------------------------------------------------------
# VIF diagnostics (Week7)
# ---------------------------------------------------------------------------
def compute_vif(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    """Compute Variance Inflation Factor for multicollinearity check."""
    X = df[features].dropna()
    rows = []
    for i, col in enumerate(features):
        rows.append({"feature": col, "vif": float(variance_inflation_factor(X.values, i))})
    return pd.DataFrame(rows).sort_values("vif", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------
def rmse(y_true, y_pred) -> float:
    return float(mean_squared_error(y_true, y_pred) ** 0.5)


def evaluate_split(y_true, y_pred) -> dict[str, float]:
    return {
        "r2": float(r2_score(y_true, y_pred)),
        "rmse": rmse(y_true, y_pred),
        "mae": float(mean_absolute_error(y_true, y_pred)),
    }


# ---------------------------------------------------------------------------
# Pipeline building & training
# ---------------------------------------------------------------------------
def build_preprocessor(
    numeric_features: list[str],
    categorical_features: list[str],
) -> ColumnTransformer:
    """Build preprocessor with StandardScaler (numeric) + OneHotEncoder (categorical)."""
    transformers = [("num", StandardScaler(), numeric_features)]
    if categorical_features:
        transformers.append(
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features)
        )
    return ColumnTransformer(transformers=transformers)


def run_model(
    model_name: str,
    estimator,
    numeric_features: list[str],
    categorical_features: list[str],
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> tuple[dict, Pipeline]:
    preprocessor = build_preprocessor(numeric_features, categorical_features)
    pipeline = Pipeline([("preprocess", preprocessor), ("model", estimator)])

    all_feats = numeric_features + categorical_features
    x_train, y_train = train_df[all_feats], train_df[TARGET]
    x_val, y_val = val_df[all_feats], val_df[TARGET]
    x_test, y_test = test_df[all_feats], test_df[TARGET]

    # GroupKFold by year: tests temporal generalization within training period
    gkf = GroupKFold(n_splits=5)
    cv_neg_rmse = cross_val_score(
        pipeline, x_train, y_train,
        cv=gkf, groups=train_df["year"],
        scoring="neg_root_mean_squared_error", n_jobs=-1,
    )
    cv_r2 = cross_val_score(
        pipeline, x_train, y_train,
        cv=gkf, groups=train_df["year"],
        scoring="r2", n_jobs=-1,
    )

    pipeline.fit(x_train, y_train)
    val_m = evaluate_split(y_val, pipeline.predict(x_val))
    test_m = evaluate_split(y_test, pipeline.predict(x_test))

    return {
        "model": model_name,
        "cv_rmse_mean": float((-cv_neg_rmse).mean()),
        "cv_rmse_std": float((-cv_neg_rmse).std()),
        "cv_r2_mean": float(cv_r2.mean()),
        "cv_r2_std": float(cv_r2.std()),
        "val_r2": val_m["r2"],
        "val_rmse": val_m["rmse"],
        "val_mae": val_m["mae"],
        "test_r2": test_m["r2"],
        "test_rmse": test_m["rmse"],
        "test_mae": test_m["mae"],
    }, pipeline


def tune_gradient_boosting(
    fs_name: str,
    numeric_features: list[str],
    categorical_features: list[str],
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> tuple[dict, Pipeline]:
    """Grid search over GBR hyperparameters (Week10 ensemble tuning)."""
    grid = {
        "n_estimators": [200, 300, 500],
        "learning_rate": [0.03, 0.05, 0.1],
        "max_depth": [2, 3],
        "subsample": [0.8, 1.0],
    }

    rows = []
    best_rmse = float("inf")
    best_result = None
    best_pipeline = None

    for params in ParameterGrid(grid):
        est = GradientBoostingRegressor(random_state=42, **params)
        result, pipe = run_model(
            "gradient_boosting_tuned", est,
            numeric_features, categorical_features,
            train_df, val_df, test_df,
        )
        result.update({
            "feature_set": fs_name,
            "n_numeric_features": len(numeric_features),
            **params,
        })
        rows.append(result)
        if result["val_rmse"] < best_rmse:
            best_rmse = result["val_rmse"]
            best_result = result
            best_pipeline = pipe

    pd.DataFrame(rows).sort_values("val_rmse").to_csv(
        PROCESSED_DIR / "gbr_tuning_results.csv", index=False,
    )

    if best_result is None or best_pipeline is None:
        raise RuntimeError("GBR tuning produced no valid model.")

    return best_result, best_pipeline


def save_feature_importance(model_name: str, fs_name: str, pipeline: Pipeline) -> None:
    """Save feature importance for tree-based models (Week8/Week10)."""
    model = pipeline.named_steps["model"]
    if not hasattr(model, "feature_importances_"):
        return
    names = pipeline.named_steps["preprocess"].get_feature_names_out()
    imp = pd.DataFrame({"feature": names, "importance": model.feature_importances_})
    imp.sort_values("importance", ascending=False).to_csv(
        OUTPUTS_MODELS_DIR / f"feature_importance_{fs_name}_{model_name}.csv", index=False,
    )


def save_residual_plot(
    fs_name: str,
    numeric_features: list[str],
    categorical_features: list[str],
    pipeline: Pipeline,
    test_df: pd.DataFrame,
) -> None:
    """Residual analysis plot for Linear Regression (Week7)."""
    x = test_df[numeric_features + categorical_features]
    y = test_df[TARGET]
    y_pred = pipeline.predict(x)
    residuals = y - y_pred

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    axes[0].scatter(y_pred, residuals, alpha=0.6, s=20)
    axes[0].axhline(0, color="red", ls="--", lw=1)
    axes[0].set_title(f"Residuals vs Predicted ({fs_name})")
    axes[0].set_xlabel("Predicted fertility_rate")
    axes[0].set_ylabel("Residual")

    axes[1].hist(residuals, bins=20, edgecolor="black", alpha=0.8)
    axes[1].set_title(f"Residual Distribution ({fs_name})")
    axes[1].set_xlabel("Residual")
    axes[1].set_ylabel("Count")

    plt.tight_layout()
    plt.savefig(
        OUTPUTS_MODELS_DIR / f"linear_regression_residuals_{fs_name}.png",
        dpi=150, bbox_inches="tight",
    )
    plt.close(fig)


def save_split_summary(train: pd.DataFrame, val: pd.DataFrame, test: pd.DataFrame) -> None:
    rows = []
    for name, split in [("train", train), ("val", val), ("test", test)]:
        rows.append({
            "split": name,
            "year_min": int(split["year"].min()),
            "year_max": int(split["year"].max()),
            "rows": len(split),
        })
    pd.DataFrame(rows).to_csv(PROCESSED_DIR / "model_split_summary.csv", index=False)


def save_config() -> None:
    config = {
        "target": TARGET,
        "core_features": CORE_FEATURES,
        "optimal_lags": OPTIMAL_LAGS,
        "feature_sets": {k: v for k, v in FEATURE_SETS.items()},
        "categorical_features": CATEGORICAL_FEATURES,
        "split": {"train_max": 2018, "val": [2019, 2020, 2021], "test_min": 2022},
        "models": ["linear_regression", "random_forest", "gradient_boosting"],
        "cv": "GroupKFold(n_splits=5, groups=year)",
        "scaling": "StandardScaler (numeric features)",
    }
    with open(MODELS_DIR / "modeling_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, default=str)


def main() -> None:
    ensure_dirs()
    df = load_data()

    # --- Feature engineering: lagged features ---
    df = add_lag_features(df)
    df = df.dropna(subset=LAG_FEATURE_NAMES).reset_index(drop=True)

    # --- Split ---
    train_df, val_df, test_df = split_by_year(df)

    # --- Feature engineering: country-demeaning (centering, Week7) ---
    demean_cols = CORE_FEATURES + LAG_FEATURE_NAMES
    train_df, country_means = add_demeaned_features(train_df, demean_cols)
    val_df, _ = add_demeaned_features(val_df, demean_cols, country_means)
    test_df, _ = add_demeaned_features(test_df, demean_cols, country_means)

    save_split_summary(train_df, val_df, test_df)

    # --- VIF diagnostics (Week7) ---
    vif_records = []
    for fs_name, fs_spec in FEATURE_SETS.items():
        vif_df = compute_vif(train_df, fs_spec["numeric"])
        vif_df["feature_set"] = fs_name
        vif_records.append(vif_df)
    vif_all = pd.concat(vif_records, ignore_index=True)
    vif_all.to_csv(PROCESSED_DIR / "model_vif_table.csv", index=False)
    print("\n=== VIF Diagnostics ===")
    print(vif_all.to_string(index=False))

    # --- Model definitions (Week7 LR, Week8 RF, Week10 GBR) ---
    model_specs = {
        "linear_regression": LinearRegression(),
        "random_forest": RandomForestRegressor(
            n_estimators=400, random_state=42, n_jobs=-1, min_samples_leaf=2,
        ),
        "gradient_boosting": GradientBoostingRegressor(
            random_state=42, n_estimators=300, learning_rate=0.05, max_depth=3,
        ),
    }

    # --- Train all models on all feature sets ---
    all_results = []
    for fs_name, fs_spec in FEATURE_SETS.items():
        num_feats = fs_spec["numeric"]
        cat_feats = fs_spec["categorical"]
        pipelines: dict[str, Pipeline] = {}

        for model_name, estimator in model_specs.items():
            result, pipe = run_model(
                model_name, estimator,
                num_feats, cat_feats,
                train_df, val_df, test_df,
            )
            result["feature_set"] = fs_name
            result["n_numeric_features"] = len(num_feats)
            all_results.append(result)

            pipelines[model_name] = pipe
            dump(pipe, MODELS_DIR / f"{fs_name}_{model_name}.joblib")
            save_feature_importance(model_name, fs_name, pipe)

        if "linear_regression" in pipelines:
            save_residual_plot(
                fs_name, num_feats, cat_feats,
                pipelines["linear_regression"], test_df,
            )

    # --- GBR hyperparameter tuning on core_lagged (Week10) ---
    tuning_fs = "core_lagged"
    tuned_result, tuned_pipe = tune_gradient_boosting(
        tuning_fs,
        FEATURE_SETS[tuning_fs]["numeric"],
        FEATURE_SETS[tuning_fs]["categorical"],
        train_df, val_df, test_df,
    )
    all_results.append(tuned_result)
    dump(tuned_pipe, MODELS_DIR / f"{tuning_fs}_gradient_boosting_tuned.joblib")
    save_feature_importance("gradient_boosting_tuned", tuning_fs, tuned_pipe)

    # --- Save metrics ---
    metrics_df = (
        pd.DataFrame(all_results)
        .sort_values(["feature_set", "val_rmse"])
        .reset_index(drop=True)
    )
    metrics_df.to_csv(PROCESSED_DIR / "model_metrics_detailed.csv", index=False)

    comparison = (
        metrics_df.sort_values("val_rmse")
        .groupby("feature_set", as_index=False)
        .first()[["feature_set", "model", "cv_r2_mean", "val_rmse", "val_mae", "test_rmse", "test_mae", "test_r2"]]
    )
    comparison.to_csv(PROCESSED_DIR / "model_feature_set_comparison.csv", index=False)

    best = metrics_df.loc[metrics_df["val_rmse"].idxmin()]
    pd.DataFrame([best]).to_csv(PROCESSED_DIR / "final_model_metrics.csv", index=False)

    summary = [
        "Final model selection summary",
        f"Selected model: {best['model']}",
        f"Feature set: {best['feature_set']}",
        f"CV R2: {best['cv_r2_mean']:.6f} (+/- {best['cv_r2_std']:.6f})",
        f"Validation RMSE: {best['val_rmse']:.6f}",
        f"Validation MAE: {best['val_mae']:.6f}",
        f"Test RMSE: {best['test_rmse']:.6f}",
        f"Test MAE: {best['test_mae']:.6f}",
        f"Test R2: {best['test_r2']:.6f}",
    ]
    (PROCESSED_DIR / "final_model_summary.txt").write_text("\n".join(summary), encoding="utf-8")

    save_config()

    print(f"\n{'='*70}")
    print("Model Metrics (sorted by val_rmse)")
    print(f"{'='*70}")
    print(metrics_df.to_string(index=False))
    print(f"\n{'='*70}")
    print("Best model per feature set")
    print(f"{'='*70}")
    print(comparison.to_string(index=False))
    print("\nModel training pipeline completed.")


if __name__ == "__main__":
    main()
