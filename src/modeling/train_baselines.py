"""Train baseline ML models for fertility_rate and save artifacts/metrics."""

from pathlib import Path
import json

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


DATA_PATH = Path("data/processed/final_oecd.csv")
MODELS_DIR = Path("models")
OUTPUTS_DIR = Path("outputs/models")
PROCESSED_DIR = Path("data/processed")

TARGET = "fertility_rate"
FEATURES = [
    "inflation",
    "unemployment_total",
    "female_labor_force_participation",
    "gdp_per_capita",
    "marriage_rate",
    "income_share_top10",
    "wealth_share_top10",
    "income_wealth_ratio",
]


def ensure_dirs() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    cols = ["country", "country_code", "year", TARGET] + FEATURES
    return df[cols].dropna().sort_values(["year", "country_code"]).reset_index(drop=True)


def split_by_year(df: pd.DataFrame):
    train = df[df["year"] <= 2018].copy()
    val = df[(df["year"] >= 2019) & (df["year"] <= 2021)].copy()
    test = df[df["year"] >= 2022].copy()
    return train, val, test


def evaluate(y_true, y_pred) -> dict:
    rmse = mean_squared_error(y_true, y_pred) ** 0.5
    return {
        "r2": float(r2_score(y_true, y_pred)),
        "rmse": float(rmse),
        "mae": float(mean_absolute_error(y_true, y_pred)),
    }


def run_model(name: str, model, train: pd.DataFrame, val: pd.DataFrame, test: pd.DataFrame) -> dict:
    x_train, y_train = train[FEATURES], train[TARGET]
    x_val, y_val = val[FEATURES], val[TARGET]
    x_test, y_test = test[FEATURES], test[TARGET]

    model.fit(x_train, y_train)

    val_pred = model.predict(x_val)
    test_pred = model.predict(x_test)

    result = {
        "model": name,
        "val_r2": evaluate(y_val, val_pred)["r2"],
        "val_rmse": evaluate(y_val, val_pred)["rmse"],
        "val_mae": evaluate(y_val, val_pred)["mae"],
        "test_r2": evaluate(y_test, test_pred)["r2"],
        "test_rmse": evaluate(y_test, test_pred)["rmse"],
        "test_mae": evaluate(y_test, test_pred)["mae"],
    }
    return result


def save_artifacts(train: pd.DataFrame, val: pd.DataFrame, test: pd.DataFrame, results: list[dict]) -> None:
    split_df = pd.DataFrame(
        [
            {"split": "train", "year_min": int(train["year"].min()), "year_max": int(train["year"].max()), "rows": int(len(train))},
            {"split": "val", "year_min": int(val["year"].min()), "year_max": int(val["year"].max()), "rows": int(len(val))},
            {"split": "test", "year_min": int(test["year"].min()), "year_max": int(test["year"].max()), "rows": int(len(test))},
        ]
    )
    split_df.to_csv(PROCESSED_DIR / "model_split_summary.csv", index=False)

    metrics_df = pd.DataFrame(results).sort_values("val_rmse").reset_index(drop=True)
    metrics_df.to_csv(PROCESSED_DIR / "model_baseline_metrics.csv", index=False)

    config = {
        "target": TARGET,
        "features": FEATURES,
        "split": {
            "train_year_max": 2018,
            "val_years": [2019, 2020, 2021],
            "test_year_min": 2022,
        },
        "models": ["linear_regression", "random_forest"],
    }
    with open(MODELS_DIR / "baseline_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)



def main() -> None:
    ensure_dirs()
    df = load_data()
    train, val, test = split_by_year(df)

    results = []
    results.append(run_model("linear_regression", LinearRegression(), train, val, test))
    results.append(
        run_model(
            "random_forest",
            RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=-1),
            train,
            val,
            test,
        )
    )

    save_artifacts(train, val, test, results)

    print("Baseline modeling complete.")
    print(pd.DataFrame(results).sort_values("val_rmse").to_string(index=False))


if __name__ == "__main__":
    main()
