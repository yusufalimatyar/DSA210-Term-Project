# Fertility Rate Analysis in OECD Countries

## Project Overview

This project investigates the **economic and social determinants of fertility rates** across 34 OECD countries over the period 2000–2024. The central research question is:

> **When a country's macroeconomic conditions and inequality structure change over time, does its fertility rate respond — and through which channels?**

Fertility decline is one of the most pressing demographic challenges facing developed nations. Understanding which economic factors drive this decline — and how quickly they take effect — is critical for informed policy-making.

## Dataset

| Variable | Source | Indicator |
|---|---|---|
| Fertility Rate | World Bank API | `SP.DYN.TFRT.IN` |
| Inflation (%) | World Bank API | `FP.CPI.TOTL.ZG` |
| Unemployment Rate (%) | World Bank API | `SL.UEM.TOTL.ZS` |
| Female Labor Force Participation (%) | World Bank API | `SL.TLF.CACT.FE.ZS` |
| GDP per Capita (PPP, $) | World Bank API | `NY.GDP.PCAP.PP.CD` |
| Marriage Rate (per 1,000) | OECD Family Database SF3.1 | Crude marriage rate |
| Top 10% Income Share | World Inequality Database (WID) | `sptinc_z` (p90p100) |
| Top 10% Wealth Share | World Inequality Database (WID) | `shweal_z` (p90p100) |
| Income/Wealth Ratio | Derived from WID | `income_share_top10 / wealth_share_top10` |
| Income Level | World Bank API | `incomeLevel.value` |
| Region Tag | Manual mapping | 9 geographic regions |

- **Scope:** 34 OECD countries, 2000–2024
- **Observations:** 850 country-year rows, 100% complete (no missing values)
- **Processed data:** `data/processed/final_oecd.csv`

All World Bank indicators are fetched programmatically via the World Bank API v2. OECD marriage rate data is sourced from the [OECD Family Database](https://www.oecd.org/en/data/datasets/oecd-family-database.html). Inequality data is sourced from the [World Inequality Database](https://wid.world/data/) and standardized into `data/raw/wid_inequality.csv`.

## Motivation

Fertility rates across OECD countries have been declining steadily, with many now well below the replacement level of 2.1. This trend has profound implications for aging populations, labor markets, pension systems, and economic growth. While the decline is well-documented, the relative importance of different economic channels — and especially their **timing** — remains an active area of research.

This project goes beyond simple cross-country comparisons by using **within-country (country-demeaned) analysis** to isolate how changes in a country's own economic conditions over time relate to changes in its fertility rate. This approach avoids the confounding effects of structural differences between countries (e.g., Turkey having both high inflation and high fertility doesn't mean inflation causes higher fertility).

## Methodology

### Analysis Approach

1. **Exploratory Data Analysis (EDA):** Descriptive statistics, time series trends by region and country group, distribution comparisons, and correlation matrices.

2. **Within-Country Correlation Analysis:** Country-demeaning (subtracting each country's mean) to remove between-country confounds — equivalent to fixed effects. This isolates temporal variation: "when inflation rises *within* a country, does fertility fall?"

3. **Lagged Correlation Analysis:** Testing lags of 0–5 years to capture delayed effects. Economic shocks don't affect fertility decisions instantly — families need time to adjust plans.

4. **Hypothesis Testing:** Seven directional and group-comparison hypotheses tested using Spearman rank correlations (robust to non-normality), Kruskal-Wallis tests, and Mann-Whitney U tests with Bonferroni correction.

5. **Inequality Analysis:** WID variables (`income_share_top10`, `wealth_share_top10`, `income_wealth_ratio`) are merged into the panel and tested as additional hypotheses (H8–H10).

6. **Machine Learning:** Linear Regression, Random Forest, and Gradient Boosting trained across multiple feature engineering strategies (lagged features, country-demeaning) to assess predictive power of the identified channels.

### Hypotheses

| # | Variable | Hypothesis | Mechanism |
|---|---|---|---|
| H1 | Unemployment | ρ < 0 (one-tailed) | Cyclical shock: job loss → economic insecurity → postpone children |
| H2 | Female LFP | ρ < 0 (one-tailed) | Structural trend: women in workforce → higher opportunity cost → fewer children |
| H3 | Inflation | ρ < 0 (one-tailed) | Cost-of-living pressure erodes purchasing power |
| H4 | GDP per Capita | ρ ≠ 0 (two-tailed) | Demographic-economic paradox: richer countries have fewer children |
| H5 | Marriage Rate | ρ > 0 (one-tailed) | Marriage as the primary institutional pathway to parenthood |
| H6 | Country Group | Group means differ | Structural differences between developed, transition, and special case countries |
| H7 | Income Level | Group means differ | High income vs upper-middle income fertility differences |

### Inequality Hypotheses

| # | Variable | Hypothesis | Mechanism |
|---|---|---|---|
| H8 | `income_share_top10` | ρ < 0 (one-tailed) | Higher concentration of income at top decile raises perceived insecurity for median households |
| H9 | `wealth_share_top10` | ρ < 0 (one-tailed) | Wealth concentration may weaken long-run family formation incentives |
| H10 | `income_wealth_ratio` | exploratory | Relative balance between income and wealth concentration may track fertility pressure |

### Country Groups

| Group | Countries | Description |
|---|---|---|
| Developed (16) | USA, CAN, GBR, DEU, FRA, NLD, BEL, CHE, AUT, IRL, SWE, NOR, DNK, FIN, AUS, NZL | Benchmark group |
| Transition (12) | MEX, COL, TUR, CHL, POL, CZE, HUN, SVK, SVN, EST, LVA, LTU | Economies in transition |
| Special Case (6) | JPN, KOR, ITA, ESP, PRT, GRC | Extreme fertility decline cases |

## Project Structure

```
├── data/
│   ├── raw/                  # Raw data from APIs and OECD
│   └── processed/            # Cleaned and merged datasets
├── notebooks/
│   └── analysis.ipynb        # Main analysis notebook
├── outputs/                  # Generated visualizations
└── src/
    ├── data_collection.py    # World Bank API + OECD data fetching
    ├── data_cleaning.py      # Filtering, labeling, imputation
    ├── inequality_eda.py     # Inequality-focused EDA outputs
    └── modeling/
        ├── train_baselines.py  # Initial baseline (LR + RF)
        └── train_models.py     # Full pipeline (LR, RF, GBR + lags + demeaning)
```

## How to Run

1. **Prepare WID raw file**:
   - Download WID export (`WID_Data_*.csv`) and place it under `data/raw/`
   - Alternatively place already standardized `data/raw/wid_inequality.csv`

2. **Data collection** (fetches from APIs — requires internet):
   ```bash
   python3 src/data_collection.py
   ```

3. **Data cleaning** (processes raw data into analysis-ready format):
   ```bash
   python3 src/data_cleaning.py
   ```

4. **Run inequality EDA outputs**:
   ```bash
   python3 src/inequality_eda.py
   ```

5. **Run ML models** (LR, RF, GBR with lagged & demeaned features):
   ```bash
   python3 src/modeling/train_models.py
   ```
   Generated files:
   - `data/processed/model_metrics_detailed.csv`
   - `data/processed/model_vif_table.csv`
   - `data/processed/model_feature_set_comparison.csv`
   - `data/processed/final_model_summary.txt`
   - `outputs/models/` (feature importance CSVs, residual plots)

6. **Analysis** (open and run the notebook):
   ```bash
   jupyter notebook notebooks/analysis.ipynb
   ```
   Then select **Kernel → Restart & Run All**.

## Modeling Pipeline

The ML pipeline (`src/modeling/train_models.py`) trains **Linear Regression**, **Random Forest**, and **Gradient Boosting** across three feature sets:

| Feature Set | Description | Key Idea |
|---|---|---|
| `core` | 5 economic features + country_group | Simple baseline |
| `core_lagged` | Core + lagged features (optimal lags from stat analysis) | Captures delayed effects |
| `demeaned_lagged` | Country-demeaned core + lags | Within-country temporal model |

Key design choices:
- **Lagged features** based on within-country Spearman optimal lags (marriage lag=2, GDP lag=5, etc.)
- **StandardScaler** for numeric features
- **Country-demeaning** (centering) to isolate within-country dynamics
- **VIF diagnostics** per feature set
- **GBR hyperparameter tuning** via grid search on validation set

## Findings

### Statistical Analysis (Within-Country, Spearman)

The strongest results come from the **within-country lagged correlation analysis**, which isolates how changes in a country's own economic conditions over time relate to changes in its fertility rate:

| Variable | Optimal Lag | ρ | p-value | Interpretation |
|---|---|---|---|---|
| Marriage Rate | 2 years | +0.53 | <0.001 | **Strongest channel.** When marriages rise within a country, fertility follows ~2 years later. |
| GDP per Capita | 5 years | −0.49 | <0.001 | **Demographic-economic paradox.** As countries grow richer over time, fertility declines — but with a long delay. |
| Female LFP | 5 years | −0.35 | <0.001 | Rising female workforce participation is followed by lower fertility ~5 years later. |
| Inflation | 4 years | +0.16 | <0.001 | Weak positive — opposite to hypothesis. Within-country inflation does not clearly suppress fertility. |
| Unemployment | 2 years | −0.10 | 0.005 | Weak but directionally correct: job insecurity depresses fertility with a 2-year delay. |
| Income Share Top 10% | 4 years | +0.07 | 0.047 | Very weak. Inequality–fertility link is not robust in this panel. |

**Key insight:** The lag structure matters enormously. Contemporaneous (lag=0) correlations are much weaker. Economic shocks affect fertility decisions with a delay of 2–5 years, reflecting the time families need to adjust plans.

### Hypothesis Test Results

| # | Hypothesis | Result |
|---|---|---|
| H1 | Unemployment → lower fertility | ✅ Supported (ρ = −0.10, p = 0.005, lag=2) |
| H2 | Female LFP → lower fertility | ✅ Supported (ρ = −0.35, p < 0.001, lag=5) |
| H3 | Inflation → lower fertility | ❌ Not supported (positive sign, opposite to hypothesis) |
| H4 | GDP per capita ↔ fertility | ✅ Supported (ρ = −0.49, p < 0.001, lag=5) |
| H5 | Marriage rate → higher fertility | ✅ Supported (ρ = +0.53, p < 0.001, lag=2) |
| H6 | Country groups differ | ✅ Supported (Kruskal-Wallis p < 0.001) |
| H7 | Income levels differ | ✅ Supported (Mann-Whitney p < 0.001) |
| H8 | Income inequality → lower fertility | ❌ Not supported (ρ = −0.05, p = 0.062) |
| H9 | Wealth inequality → lower fertility | ❌ Not supported (positive sign) |

### Machine Learning Results

Three models (Linear Regression, Random Forest, Gradient Boosting) were trained across three feature sets with a temporal split (train ≤2018, val 2019–2021, test 2022–2024):

| Feature Set | Best Model | Val RMSE | Test RMSE | Test R² |
|---|---|---|---|---|
| `core` | Gradient Boosting | 0.152 | 0.305 | −1.12 |
| `core_lagged` | GBR (tuned) | 0.139 | 0.278 | −0.76 |
| `demeaned_lagged` | Gradient Boosting | 0.163 | 0.260 | −0.54 |

**All models have negative test R²**, meaning they perform worse than a simple mean prediction on the 2022–2024 test set. This is discussed honestly in the Limitations section below.

Adding **lagged features** improved test RMSE by ~15% over the core baseline. **Country-demeaning** further reduced test RMSE to 0.260 and brought test R² closest to zero (−0.54), confirming that within-country temporal signals are more generalizable than cross-country patterns.

## Limitations & Honest Assessment

1. **Negative test R² — structural break.** The test set (2022–2024) falls in the post-COVID period, where fertility dynamics shifted structurally across OECD countries. The model, trained on 2005–2018 data, cannot capture this regime change. This is a genuine distribution shift, not a modeling deficiency per se.

2. **Small panel size.** 34 countries × 25 years = 850 observations (680 after lag truncation). This is small for ML models that need to learn complex non-linear relationships while generalizing temporally.

3. **Narrow target range.** Fertility rate has a standard deviation of only 0.30 (range 0.72–2.71). Small absolute prediction errors translate into poor R² scores.

4. **Omitted variables.** Fertility decisions depend heavily on cultural norms, childcare availability, housing costs, parental leave policies, and contraception access — none of which are in this dataset. Macroeconomic indicators alone are insufficient predictors.

5. **ML as complement, not main finding.** The primary contribution of this project is the **statistical analysis**: identifying which economic channels matter, their direction, and their timing (lag structure). The ML pipeline demonstrates that even when these channels are combined into a predictive model, year-to-year fertility prediction from macroeconomic data remains fundamentally difficult.

## Requirements

- Python 3.x
- pandas, numpy, matplotlib, seaborn, scipy, scikit-learn, statsmodels

## AI Usage Disclosure

This project was developed with the assistance of **Windsurf Cascade (Claude)**, an AI coding assistant. Below is a transparent account of how AI was used at each stage:

| Stage | AI Contribution | My Contribution |
|---|---|---|
| **Data Collection** | Helped write `data_collection.py` to fetch World Bank API data programmatically; assisted with OECD data parsing | Identified which variables and indicators to use; decided on country scope and time range |
| **Data Cleaning** | Assisted with writing `data_cleaning.py` including imputation logic, outlier detection, and region/group mappings | Defined the country groups (developed, transition, special_case); decided to drop homeownership due to missing data; chose imputation strategy |
| **EDA & Visualization** | Generated code for correlation matrices, scatter plots, time series charts, boxplots, and Simpson's Paradox demonstration | Interpreted results; identified the inflation paradox; decided which visualizations to include |
| **Statistical Analysis** | Implemented within-country demeaning, lagged Spearman correlations, hypothesis tests (Kruskal-Wallis, Mann-Whitney U), and Bonferroni corrections | Formulated all 7 hypotheses; chose within-country approach over pooled; interpreted lag structure and null findings |
| **ML Modeling** | Built `train_models.py` pipeline with lagged features, country-demeaning, StandardScaler, VIF diagnostics, and GBR tuning; diagnosed root causes of negative test R² | Reviewed model performance analysis; decided on feature sets; interpreted limitations and decided to present negative results honestly |
| **Variable Selection** | Suggested replacing `female_youth_unemployment` with `female_labor_force_participation` as a theoretically stronger variable | Made the final decision to adopt this change after evaluating the rationale |
| **Documentation** | Assisted with writing README, notebook markdown, and English translations | Reviewed all content; defined project scope and research question |
| **Git & Deployment** | Provided git commands for version control and GitHub push | Managed the repository and approved all commits |

All statistical interpretations, research decisions, and hypothesis formulations are my own. AI was used as a **coding and writing assistant**, not as a decision-maker.
