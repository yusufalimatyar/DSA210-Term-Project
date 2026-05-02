"""Generate inequality-focused EDA outputs from final_oecd dataset."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


DATA_PATH = Path("data/processed/final_oecd.csv")
OUTPUT_DIR = Path("outputs")
PROCESSED_DIR = Path("data/processed")


def ensure_dirs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    return df.sort_values(["country_code", "year"]).reset_index(drop=True)


def save_summary_tables(df: pd.DataFrame) -> None:
    summary_cols = [
        "fertility_rate",
        "income_share_top10",
        "wealth_share_top10",
        "income_wealth_ratio",
    ]
    summary = df[summary_cols].describe().T.round(4)
    summary.to_csv(PROCESSED_DIR / "inequality_eda_summary.csv")

    by_group = (
        df.groupby("country_group")[["fertility_rate", "income_share_top10", "wealth_share_top10", "income_wealth_ratio"]]
        .mean()
        .round(4)
    )
    by_group.to_csv(PROCESSED_DIR / "inequality_by_group.csv")


def plot_distributions(df: pd.DataFrame) -> None:
    vars_ineq = ["income_share_top10", "wealth_share_top10", "income_wealth_ratio"]
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    for i, col in enumerate(vars_ineq):
        sns.histplot(df[col], kde=True, bins=20, ax=axes[i], color="#1f77b4")
        axes[i].set_title(col)
        axes[i].set_xlabel(col)
        axes[i].set_ylabel("Count")

    plt.suptitle("Inequality Variables - Distribution", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "inequality_distributions.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_scatter_with_trend(df: pd.DataFrame) -> None:
    vars_ineq = ["income_share_top10", "wealth_share_top10", "income_wealth_ratio"]
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    for i, col in enumerate(vars_ineq):
        ax = axes[i]
        sns.scatterplot(
            data=df,
            x=col,
            y="fertility_rate",
            hue="country_group",
            alpha=0.6,
            s=20,
            ax=ax,
            legend=(i == 0),
        )

        x = df[col].to_numpy()
        y = df["fertility_rate"].to_numpy()
        z = np.polyfit(x, y, 1)
        xline = np.linspace(x.min(), x.max(), 100)
        ax.plot(xline, np.poly1d(z)(xline), color="black", linewidth=2, alpha=0.8)

        corr = df[[col, "fertility_rate"]].corr(method="spearman").iloc[0, 1]
        ax.set_title(f"fertility_rate vs {col}\nSpearman rho={corr:+.3f}")
        ax.set_xlabel(col)
        ax.set_ylabel("fertility_rate")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fertility_vs_inequality_scatter.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_group_trends(df: pd.DataFrame) -> None:
    trend = (
        df.groupby(["country_group", "year"])[["income_share_top10", "wealth_share_top10"]]
        .mean()
        .reset_index()
    )

    fig, axes = plt.subplots(1, 2, figsize=(16, 5), sharex=True)
    sns.lineplot(data=trend, x="year", y="income_share_top10", hue="country_group", marker="o", ax=axes[0])
    sns.lineplot(data=trend, x="year", y="wealth_share_top10", hue="country_group", marker="o", ax=axes[1])

    axes[0].set_title("Top 10% Income Share by Group")
    axes[1].set_title("Top 10% Wealth Share by Group")
    axes[0].set_ylabel("Share")
    axes[1].set_ylabel("Share")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "inequality_group_trends.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_correlation_heatmap(df: pd.DataFrame) -> None:
    cols = [
        "fertility_rate",
        "inflation",
        "unemployment_total",
        "female_labor_force_participation",
        "gdp_per_capita",
        "marriage_rate",
        "income_share_top10",
        "wealth_share_top10",
        "income_wealth_ratio",
    ]
    corr = df[cols].corr(method="spearman")

    fig, ax = plt.subplots(figsize=(10, 8))
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(corr, mask=mask, annot=True, fmt=".2f", cmap="RdBu_r", center=0, vmin=-1, vmax=1, ax=ax)
    ax.set_title("Spearman Correlation Matrix (Extended with Inequality)")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "correlation_matrix_with_inequality.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ensure_dirs()
    df = load_data()

    save_summary_tables(df)
    plot_distributions(df)
    plot_scatter_with_trend(df)
    plot_group_trends(df)
    plot_correlation_heatmap(df)

    print("Inequality EDA outputs created in outputs/ and data/processed/.")


if __name__ == "__main__":
    main()
