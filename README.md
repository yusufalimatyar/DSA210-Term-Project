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

5. **Inequality Extension (completed for data + EDA):** WID variables are merged into the panel (`income_share_top10`, `wealth_share_top10`, `income_wealth_ratio`) and inequality-focused EDA outputs are generated.

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

### Inequality Hypotheses (Current Extension)

| # | Variable | Hypothesis | Mechanism |
|---|---|---|---|
| H8 | `income_share_top10` | ρ < 0 (one-tailed) | Higher concentration of income at top decile raises perceived insecurity for median households |
| H9 | `wealth_share_top10` | ρ < 0 (one-tailed) | Wealth concentration may weaken long-run family formation incentives |
| H10 | `income_wealth_ratio` | exploratory | Relative balance between income and wealth concentration may track fertility pressure |

### Current Inequality Findings (Notebook Results)

- `H8` (`income_share_top10`, within-country, lag=0, one-tailed): `ρ = -0.0529`, `p = 0.0617` → **fail to reject H₀**
- `H9` (`wealth_share_top10`, within-country, lag=0, one-tailed): `ρ = +0.0709`, `p = 0.9807` (for negative-tail test) → **fail to reject H₀**
- Lag scan (0–5) shows inequality effects are statistically weak and mixed in sign:
  - `income_share_top10`: best lag `4`, `ρ = +0.0743`, `p = 0.0472`
  - `wealth_share_top10`: best lag `0`, `ρ = +0.0709`, `p = 0.0386`
  - `income_wealth_ratio`: best lag `0`, `ρ = -0.0833`, `p = 0.0152`
- Interpretation: inequality-fertility link in this OECD panel is currently **weak** and does not provide strong support for a robust negative channel.

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
    └── inequality_eda.py     # Inequality-focused EDA outputs
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

5. **Analysis** (open and run the notebook):
   ```bash
   jupyter notebook notebooks/analysis.ipynb
   ```
   Then select **Kernel → Restart & Run All**.

## Next Implementation Roadmap (Before ML)

1. Update notebook constants and plots to include all inequality variables.
2. Re-run within-country lag tests with inequality channels included.
3. Decide final inequality feature set for modeling (single metric vs multi-metric).
4. Start modeling stage (OLS / FE / ML) with multicollinearity diagnostics.

## Requirements

- Python 3.x
- pandas, numpy, matplotlib, seaborn, scipy

## AI Usage Disclosure

This project was developed with the assistance of **Windsurf Cascade (Claude)**, an AI coding assistant. Below is a transparent account of how AI was used at each stage:

| Stage | AI Contribution | My Contribution |
|---|---|---|
| **Data Collection** | Helped write `data_collection.py` to fetch World Bank API data programmatically; assisted with OECD data parsing | Identified which variables and indicators to use; decided on country scope and time range |
| **Data Cleaning** | Assisted with writing `data_cleaning.py` including imputation logic, outlier detection, and region/group mappings | Defined the country groups (developed, transition, special_case); decided to drop homeownership due to missing data; chose imputation strategy |
| **EDA & Visualization** | Generated code for correlation matrices, scatter plots, time series charts, boxplots, and Simpson's Paradox demonstration | Interpreted results; identified the inflation paradox; decided which visualizations to include |
| **Statistical Analysis** | Implemented within-country demeaning, lagged Spearman correlations, hypothesis tests (Kruskal-Wallis, Mann-Whitney U), and Bonferroni corrections | Formulated all 7 hypotheses; chose within-country approach over pooled; interpreted lag structure and null findings |
| **Variable Selection** | Suggested replacing `female_youth_unemployment` with `female_labor_force_participation` as a theoretically stronger variable | Made the final decision to adopt this change after evaluating the rationale |
| **Documentation** | Assisted with writing README, notebook markdown, and English translations | Reviewed all content; defined project scope and research question |
| **Git & Deployment** | Provided git commands for version control and GitHub push | Managed the repository and approved all commits |

All statistical interpretations, research decisions, and hypothesis formulations are my own. AI was used as a **coding and writing assistant**, not as a decision-maker.
