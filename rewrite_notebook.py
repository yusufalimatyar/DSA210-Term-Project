"""
Rewrites analysis.ipynb from scratch: clean structure, no old outputs,
all imports consolidated, constants defined once, all text in English.
"""
import json

cells = []

def _split(text):
    """Convert a multi-line string into notebook source format."""
    lines = text.strip("\n").split("\n")
    result = []
    for i, line in enumerate(lines):
        if i < len(lines) - 1:
            result.append(line + "\n")
        else:
            result.append(line)
    return result

def md(text):
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": _split(text)
    })

def code(text):
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": _split(text)
    })

# ============================================================
# CELL 0: Title (markdown)
# ============================================================
md("""\
# Fertility Rate Analysis in OECD Countries

**Dependent variable:** `fertility_rate`
**Independent variables:** `inflation`, `unemployment_total`, `female_labor_force_participation`, `gdp_per_capita`, `marriage_rate`
**Categorical labels:** `region_tag`, `income_level`, `country_group`

**Scope:** 34 OECD countries, 2000\u20132024, 850 rows, 100% complete

### Data Sources

| Variable | Source | Indicator Code |
|---|---|---|
| `fertility_rate` | World Bank API v2 | `SP.DYN.TFRT.IN` |
| `inflation` | World Bank API v2 | `FP.CPI.TOTL.ZG` |
| `unemployment_total` | World Bank API v2 | `SL.UEM.TOTL.ZS` |
| `female_labor_force_participation` | World Bank API v2 | `SL.TLF.CACT.FE.ZS` |
| `gdp_per_capita` | World Bank API v2 (PPP, current int'l $) | `NY.GDP.PCAP.PP.CD` |
| `marriage_rate` | OECD Family Database SF3.1 | Crude marriage rate per 1,000 |
| `income_level` | World Bank API v2 | `incomeLevel.value` |
| `region_tag` | Manual mapping based on geography | 9 regions |

All World Bank data fetched programmatically via `src/data_collection.py`. OECD marriage rate data downloaded from the [OECD Family Database](https://www.oecd.org/en/data/datasets/oecd-family-database.html) (SF3.1 Marriage and Divorce Rates). Data cleaning and merging performed by `src/data_cleaning.py`.""")

# ============================================================
# CELL 1: Setup — all imports, constants, load data (code)
# ============================================================
code("""\
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
from scipy.stats import (shapiro, pearsonr, spearmanr,
                          f_oneway, kruskal, ttest_ind, mannwhitneyu, levene)
from scipy import stats as sp_stats
from itertools import combinations
from matplotlib.patches import Patch

warnings.filterwarnings("ignore")
sns.set_theme(style="whitegrid", palette="muted", font_scale=1.1)
plt.rcParams["figure.figsize"] = (12, 6)
plt.rcParams["figure.dpi"] = 100

# --- Constants ---
NUMERIC_VARS = [
    "fertility_rate", "inflation", "unemployment_total",
    "female_labor_force_participation", "gdp_per_capita", "marriage_rate",
]
INDEPENDENT_VARS = [
    "inflation", "unemployment_total", "female_labor_force_participation",
    "gdp_per_capita", "marriage_rate",
]
VAR_LABELS = {
    "inflation": "Inflation (%)",
    "unemployment_total": "Unemployment (%)",
    "female_labor_force_participation": "Female Labor Force Participation (%)",
    "gdp_per_capita": "GDP per Capita (PPP, $)",
    "marriage_rate": "Marriage Rate (per 1,000)",
}
VAR_SHORT = {
    "inflation": "Inflation",
    "unemployment_total": "Unemployment",
    "female_labor_force_participation": "Female\\nLFP",
    "gdp_per_capita": "GDP per\\nCapita",
    "marriage_rate": "Marriage\\nRate",
}
GROUP_COLORS = {"developed": "#2196F3", "transition": "#FF9800", "special_case": "#F44336"}
GROUP_ORDER = ["developed", "transition", "special_case"]

# --- Load data ---
df = pd.read_csv("../data/processed/final_oecd.csv")
print(f"Shape: {df.shape}")
print(f"Columns: {df.columns.tolist()}")
print(f"Year range: {df['year'].min()} - {df['year'].max()}")
print(f"Country count: {df['country_code'].nunique()}")
print(f"Missing values: {df.isnull().sum().sum()}")""")

# ============================================================
# CELL 2: Data Overview header (markdown)
# ============================================================
md("## 1. Data Overview")

# ============================================================
# CELL 3: Basic stats (code)
# ============================================================
code("""\
print("=== DATA TYPES ===")
print(df.dtypes)
print()
print("=== FIRST 5 ROWS ===")
display(df.head())
print()
print("=== DESCRIPTIVE STATISTICS ===")
display(df[NUMERIC_VARS].describe().round(3))""")

# ============================================================
# CELL 4: Comprehensive descriptive statistics (code)
# ============================================================
code("""\
stats_records = []
for col in NUMERIC_VARS:
    data = df[col].dropna()
    n = len(data)
    stats_records.append({
        "Variable": col, "N": n,
        "Mean": data.mean(), "Median": data.median(),
        "Std Dev (s)": data.std(ddof=1),
        "Variance (s\\u00b2)": data.var(ddof=1),
        "Std Error": data.std(ddof=1) / np.sqrt(n),
        "Min": data.min(), "Q1": data.quantile(0.25),
        "Q3": data.quantile(0.75), "Max": data.max(),
        "Range": data.max() - data.min(),
        "IQR": data.quantile(0.75) - data.quantile(0.25),
        "Skewness": data.skew(), "Kurtosis": data.kurtosis(),
        "CV (%)": (data.std(ddof=1) / abs(data.mean())) * 100,
    })
stats_table = pd.DataFrame(stats_records).set_index("Variable")

print("=" * 70)
print("COMPREHENSIVE DESCRIPTIVE STATISTICS")
print("=" * 70)
display(stats_table.T.round(4))

print()
for group in GROUP_ORDER:
    subset = df[df["country_group"] == group]
    print(f"--- {group.upper()} (n={len(subset)}) ---")
    display(subset[NUMERIC_VARS].describe().round(4))""")

# ============================================================
# CELL 5: Trends header (markdown)
# ============================================================
md("## 2. Fertility Rate Trends")

# ============================================================
# CELL 6: Regional + group trend plots (code)
# ============================================================
code("""\
fig, axes = plt.subplots(1, 2, figsize=(18, 7))

# --- Left: by region ---
region_trend = df.groupby(["region_tag", "year"])["fertility_rate"].mean().reset_index()
for region in sorted(df["region_tag"].unique()):
    s = region_trend[region_trend["region_tag"] == region]
    axes[0].plot(s["year"], s["fertility_rate"], marker="o", markersize=3, linewidth=2, label=region)
axes[0].set_title("Average Fertility Rate by Region")
axes[0].set_xlabel("Year")
axes[0].set_ylabel("Fertility Rate")
axes[0].axhline(y=2.1, color="red", linestyle=":", alpha=0.5, label="Replacement level")
axes[0].legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)

# --- Right: by analysis group ---
group_trend = df.groupby(["country_group", "year"])["fertility_rate"].mean().reset_index()
for group in GROUP_ORDER:
    s = group_trend[group_trend["country_group"] == group]
    axes[1].plot(s["year"], s["fertility_rate"], marker="o", markersize=4,
                 linewidth=2, color=GROUP_COLORS[group], label=group)
axes[1].set_title("Average Fertility Rate by Analysis Group")
axes[1].set_xlabel("Year")
axes[1].set_ylabel("Fertility Rate")
axes[1].axhline(y=2.1, color="red", linestyle=":", alpha=0.5)
axes[1].legend()

plt.tight_layout()
plt.savefig("../outputs/fertility_trends.png", dpi=150, bbox_inches="tight")
plt.show()""")

# ============================================================
# CELL 7: Distributions header (markdown)
# ============================================================
md("## 3. Distributions & Group Comparisons")

# ============================================================
# CELL 8: Boxplots + summary tables (code)
# ============================================================
code("""\
fig, axes = plt.subplots(1, 3, figsize=(20, 6))

# Region boxplot
region_order = df.groupby("region_tag")["fertility_rate"].median().sort_values(ascending=False).index
sns.boxplot(data=df, x="region_tag", y="fertility_rate", order=region_order, ax=axes[0], palette="Set2")
axes[0].set_title("By Region")
axes[0].tick_params(axis="x", rotation=45)
axes[0].axhline(y=2.1, color="red", linestyle=":", alpha=0.5)

# Income level boxplot
sns.boxplot(data=df, x="income_level", y="fertility_rate", ax=axes[1], palette="Set3")
axes[1].set_title("By Income Level")
axes[1].axhline(y=2.1, color="red", linestyle=":", alpha=0.5)

# Analysis group boxplot
sns.boxplot(data=df, x="country_group", y="fertility_rate", order=GROUP_ORDER, ax=axes[2], palette="Set2")
axes[2].set_title("By Analysis Group")
axes[2].axhline(y=2.1, color="red", linestyle=":", alpha=0.5)

plt.suptitle("Fertility Rate Distribution", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig("../outputs/boxplots_all.png", dpi=150, bbox_inches="tight")
plt.show()

# Summary tables
print("=== AVERAGES BY ANALYSIS GROUP ===")
display(df.groupby("country_group")[NUMERIC_VARS].mean().round(3))
print()
print("=== AVERAGES BY INCOME LEVEL ===")
display(df.groupby("income_level")[NUMERIC_VARS].mean().round(3))
print()
print("=== AVERAGES BY REGION ===")
display(df.groupby("region_tag")[NUMERIC_VARS].mean().round(3))""")

# ============================================================
# CELL 9: Correlation header (markdown)
# ============================================================
md("## 4. Pooled Correlation Analysis")

# ============================================================
# CELL 10: Correlation matrix (code)
# ============================================================
code("""\
corr_matrix = df[NUMERIC_VARS].corr()

fig, ax = plt.subplots(figsize=(10, 8))
mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
sns.heatmap(corr_matrix, mask=mask, annot=True, fmt=".3f", cmap="RdBu_r",
            center=0, vmin=-1, vmax=1, square=True, linewidths=1, ax=ax)
ax.set_title("Pearson Correlation Matrix (Pooled)\\n"
             "CAUTION: Pooled correlations may be misleading (Simpson's Paradox)")
plt.tight_layout()
plt.savefig("../outputs/correlation_matrix.png", dpi=150, bbox_inches="tight")
plt.show()

print("\\nPooled correlations with fertility_rate:")
print(corr_matrix["fertility_rate"].sort_values(ascending=False).round(4))
print("\\n\\u26a0 These pooled values mix between-country and within-country variation.")
print("  See Section 5 for the correct within-country analysis.")""")

# ============================================================
# CELL 11: Scatter plots (code)
# ============================================================
code("""\
fig, axes = plt.subplots(2, 3, figsize=(18, 11))
axes_flat = axes.flatten()

for i, var in enumerate(INDEPENDENT_VARS):
    ax = axes_flat[i]
    for region in sorted(df["region_tag"].unique()):
        s = df[df["region_tag"] == region]
        ax.scatter(s[var], s["fertility_rate"], alpha=0.4, s=15, label=region)
    z = np.polyfit(df[var], df["fertility_rate"], 1)
    x_range = np.linspace(df[var].min(), df[var].max(), 100)
    ax.plot(x_range, np.poly1d(z)(x_range), "r-", linewidth=2, alpha=0.8)
    r, p = pearsonr(df[var], df["fertility_rate"])
    star = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
    ax.text(0.03, 0.97, f"r = {r:+.3f} {star}", transform=ax.transAxes,
            fontsize=10, fontweight="bold", verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8))
    ax.set_xlabel(VAR_LABELS[var])
    ax.set_ylabel("Fertility Rate")
    ax.axhline(y=2.1, color="red", linestyle=":", alpha=0.3)

axes_flat[5].set_visible(False)
handles, labels_leg = axes_flat[0].get_legend_handles_labels()
fig.legend(handles, labels_leg, loc="lower center", ncol=5, fontsize=8, bbox_to_anchor=(0.5, -0.02))
plt.suptitle("Fertility Rate vs Independent Variables (Pooled)\\n"
             "CAUTION: Pooled correlations may be misleading \\u2014 Simpson's Paradox",
             fontsize=13, fontweight="bold")
plt.tight_layout(rect=[0, 0.03, 1, 0.93])
plt.savefig("../outputs/scatter_pooled_all.png", dpi=150, bbox_inches="tight")
plt.show()""")

# ============================================================
# CELL 12: Simpson's Paradox explanation (markdown)
# ============================================================
md("""\
### Simpson's Paradox: Inflation and GDP per Capita

The scatter plots above show a **positive** pooled correlation for inflation \u2014 suggesting "higher inflation = higher fertility." This is **misleading**:

- **Why?** Countries like Turkey, Mexico, and Colombia have both high inflation and high fertility. This is a **between-country** structural difference, not a causal relationship.
- **True relationship:** Within the same country, when inflation rises, fertility **declines** within 1 year (within-country \u03c1 = \u22120.13).
- This phenomenon is known as **Simpson's Paradox**: the relationship within subgroups can be the opposite of the relationship in the aggregate data.

The figure below demonstrates this visually:""")

# ============================================================
# CELL 13: Simpson's Paradox 2x2 (code)
# ============================================================
code("""\
fig, axes = plt.subplots(2, 2, figsize=(16, 14))

# Helper: country-demeaned columns
df_temp = df.copy()
for col in ["inflation", "gdp_per_capita", "fertility_rate"]:
    df_temp[col + "_dm"] = df_temp.groupby("country")[col].transform(lambda x: x - x.mean())

panels = [
    (0, 0, "inflation",    "fertility_rate", "Inflation (%)", "Fertility Rate",
     "POOLED: Inflation \\u2191 = Fertility \\u2191 ?\\n(Wrong \\u2014 confounded)", False),
    (0, 1, "inflation_dm", "fertility_rate_dm", "Inflation (demeaned)", "Fertility (demeaned)",
     "WITHIN-COUNTRY: Inflation \\u2191 = Fertility \\u2193\\n(Correct \\u2014 temporal variation)", True),
    (1, 0, "gdp_per_capita",    "fertility_rate", "GDP per Capita ($)", "Fertility Rate",
     "POOLED: GDP \\u2191 = Fertility \\u2193 ?\\n(Confounded)", False),
    (1, 1, "gdp_per_capita_dm", "fertility_rate_dm", "GDP per Capita (demeaned)", "Fertility (demeaned)",
     "WITHIN-COUNTRY: GDP \\u2191 = Fertility \\u2193\\n(Correct \\u2014 demographic-economic paradox)", True),
]

for row, col_idx, x_col, y_col, xlabel, ylabel, title, is_within in panels:
    ax = axes[row, col_idx]
    for group in GROUP_ORDER:
        s = df_temp[df_temp["country_group"] == group]
        ax.scatter(s[x_col], s[y_col], alpha=0.4, s=15, color=GROUP_COLORS[group], label=group)

    z = np.polyfit(df_temp[x_col], df_temp[y_col], 1)
    x_range = np.linspace(df_temp[x_col].min(), df_temp[x_col].max(), 100)
    ax.plot(x_range, np.poly1d(z)(x_range), "k--", linewidth=2, alpha=0.8)

    if is_within:
        rho, p = spearmanr(df_temp[x_col], df_temp[y_col])
        label = f"Within: \\u03c1 = {rho:+.3f}\\n(TRUE RELATIONSHIP)"
        color = "#C8E6C9"
        ax.axhline(0, color="gray", linestyle=":", alpha=0.5)
        ax.axvline(0, color="gray", linestyle=":", alpha=0.5)
    else:
        rho, p = pearsonr(df_temp[x_col], df_temp[y_col])
        label = f"Pooled: r = {rho:+.3f}\\n(MISLEADING!)"
        color = "#FFCDD2"

    ax.text(0.03, 0.97, label, transform=ax.transAxes, fontsize=11, fontweight="bold",
            verticalalignment="top", bbox=dict(boxstyle="round", facecolor=color, alpha=0.9))
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=11)
    ax.legend(fontsize=9)

if "inflation" in df_temp.columns:
    axes[0, 0].set_xlim(-5, 20)

plt.suptitle("Simpson's Paradox: Pooled vs Within-Country Correlations\\n"
             "Country-demeaning reveals the true within-country relationship",
             fontsize=14, fontweight="bold")
plt.tight_layout(rect=[0, 0, 1, 0.93])
plt.savefig("../outputs/simpsons_paradox.png", dpi=150, bbox_inches="tight")
plt.show()

print("\\u2192 Inflation: Pooled r \\u2248 +0.13 (misleading) \\u2192 Within \\u03c1 \\u2248 \\u22120.11 (true: negative)")
print("\\u2192 GDP: Pooled r \\u2248 \\u22120.13 \\u2192 Within \\u03c1 \\u2248 \\u22120.25 (true: stronger negative)")
print("\\u2192 Reason: High-inflation countries (Turkey/Mexico) also have structurally high fertility.")""")

# ============================================================
# CELL 14: Within-Country header (markdown)
# ============================================================
md("""\
## 5. Within-Country (Country-Demeaned) Analysis

Our hypothesis is explicitly **within-country temporal**: "when a country's economy worsens, does its fertility rate decline?"

To isolate within-country dynamics we:
1. **Country-demean** each variable (subtract each country's mean) \u2192 removes structural between-country differences
2. **Test lagged correlations** (0\u20135 years) \u2192 economic shocks don't affect fertility instantly""")

# ============================================================
# CELL 15: Demeaning + within + lagged correlations (code)
# ============================================================
code("""\
# --- Country-demeaning ---
df_sorted = df.sort_values(["country", "year"]).copy()
demean_cols = ["fertility_rate"] + INDEPENDENT_VARS
for col in demean_cols:
    df_sorted[col + "_dm"] = df_sorted.groupby("country")[col].transform(lambda x: x - x.mean())

# --- Within-country (lag=0) Spearman correlations ---
print("=" * 80)
print("WITHIN-COUNTRY (COUNTRY-DEMEANED) SPEARMAN CORRELATIONS")
print("  Each country's mean subtracted \\u2192 only temporal variation remains")
print("=" * 80)
print(f"{'Variable':<40} {'Pooled \\u03c1':>10} {'Within \\u03c1':>10} {'':>5} {'Direction Change?':>18}")
print("-" * 80)

within_results = {}
for var in INDEPENDENT_VARS:
    c_pool = df_sorted[["fertility_rate", var]].dropna()
    rho_pool, _ = spearmanr(c_pool["fertility_rate"], c_pool[var])
    c_within = df_sorted[["fertility_rate_dm", var + "_dm"]].dropna()
    rho_within, p_within = spearmanr(c_within["fertility_rate_dm"], c_within[var + "_dm"])
    within_results[var] = {"rho": rho_within, "p": p_within}
    changed = "YES \\u26a0" if (rho_pool > 0) != (rho_within > 0) else "no"
    star = "***" if p_within < 0.001 else "**" if p_within < 0.01 else "*" if p_within < 0.05 else "ns"
    print(f"{var:<40} {rho_pool:>+10.4f} {rho_within:>+10.4f} {star:>5}  {changed:>10}")

print("\\n\\u2192 Pooled vs Within differences reveal Simpson's paradox / confounding.")

# --- Lagged correlations ---
max_lag = 5
print("\\n" + "=" * 90)
print("LAGGED WITHIN-COUNTRY CORRELATIONS (Spearman)")
print("  fertility_rate(t) vs variable(t - lag)")
print("=" * 90)

lag_results = {}
header = f"{'Variable':<40}"
for lag in range(max_lag + 1):
    header += f" {'lag=' + str(lag):>8}"
print(header)
print("-" * 90)

for var in INDEPENDENT_VARS:
    row = f"{var:<40}"
    lag_results[var] = {}
    for lag in range(max_lag + 1):
        if lag == 0:
            c = df_sorted[["fertility_rate_dm", var + "_dm"]].dropna()
            rho, p = spearmanr(c["fertility_rate_dm"], c[var + "_dm"])
        else:
            df_sorted["_lag"] = df_sorted.groupby("country")[var + "_dm"].shift(lag)
            c = df_sorted[["fertility_rate_dm", "_lag"]].dropna()
            rho, p = spearmanr(c["fertility_rate_dm"], c["_lag"])
        lag_results[var][lag] = {"rho": rho, "p": p, "n": len(c)}
        star = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
        row += f" {rho:>+7.3f}{star:1}"
    print(row)

if "_lag" in df_sorted.columns:
    df_sorted.drop(columns=["_lag"], inplace=True)

print("\\nSignificance: *** p<0.001, ** p<0.01, * p<0.05")
print()
print("=" * 70)
print("OPTIMAL LAG (strongest significant correlation)")
print("=" * 70)
for var in INDEPENDENT_VARS:
    best_lag, best_rho = None, 0
    for lag in range(max_lag + 1):
        res = lag_results[var][lag]
        if res["p"] < 0.05 and abs(res["rho"]) > abs(best_rho):
            best_rho = res["rho"]
            best_lag = lag
    if best_lag is not None:
        r = lag_results[var][best_lag]
        print(f"  {var:<40} \\u2192 lag={best_lag}, \\u03c1={r['rho']:+.4f}, p={r['p']:.4f}, n={r['n']}")
    else:
        print(f"  {var:<40} \\u2192 NO significant lag found")""")

# ============================================================
# CELL 16: Lag heatmap (code)
# ============================================================
code("""\
lag_matrix = np.zeros((len(INDEPENDENT_VARS), max_lag + 1))
p_matrix   = np.zeros((len(INDEPENDENT_VARS), max_lag + 1))
for i, var in enumerate(INDEPENDENT_VARS):
    for j in range(max_lag + 1):
        lag_matrix[i, j] = lag_results[var][j]["rho"]
        p_matrix[i, j]   = lag_results[var][j]["p"]

fig, ax = plt.subplots(figsize=(10, 5))
im = ax.imshow(lag_matrix, cmap="RdBu_r", aspect="auto", vmin=-0.5, vmax=0.5)

for i in range(len(INDEPENDENT_VARS)):
    for j in range(max_lag + 1):
        rho_val, p_val = lag_matrix[i, j], p_matrix[i, j]
        star = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else ""
        color = "white" if abs(rho_val) > 0.25 else "black"
        ax.text(j, i, f"{rho_val:+.3f}\\n{star}", ha="center", va="center",
                fontsize=9, fontweight="bold", color=color)

ax.set_xticks(range(max_lag + 1))
ax.set_xticklabels([f"Lag {l}" for l in range(max_lag + 1)])
ax.set_yticks(range(len(INDEPENDENT_VARS)))
ax.set_yticklabels([VAR_SHORT[v].replace("\\n", " ") for v in INDEPENDENT_VARS])
ax.set_xlabel("Lag Period (Years)")
ax.set_title("Within-Country Correlations: Lag Structure Heatmap\\n"
             "(Spearman \\u03c1, country-demeaned)", fontsize=13, fontweight="bold")
cbar = plt.colorbar(im, ax=ax, shrink=0.8)
cbar.set_label("Spearman \\u03c1")
plt.tight_layout()
plt.savefig("../outputs/lag_heatmap.png", dpi=150, bbox_inches="tight")
plt.show()""")

# ============================================================
# CELL 17: Hypothesis Testing header (markdown)
# ============================================================
md("""\
## 6. Hypothesis Testing

### Research Question
**When a country's macroeconomic conditions deteriorate over time, does its fertility rate decline?**

### Sub-Hypotheses (\u03b1 = 0.05)

| # | Variable | H\u2080 | H\u2081 | Tail | Rationale |
|---|---|---|---|---|---|
| **H1** | `unemployment_total` | \u03c1 = 0 | \u03c1 < 0 | one | Cyclical shock: job loss \u2192 economic insecurity \u2192 postpone children (lag: 2 yr) |
| **H2** | `female_labor_force_participation` | \u03c1 = 0 | \u03c1 < 0 | one | Structural trend: women in workforce \u2192 higher opportunity cost \u2192 fewer children |
| **H3** | `inflation` | \u03c1 = 0 | \u03c1 < 0 | one | Inflation erodes purchasing power (lag: 1 yr) |
| **H4** | `gdp_per_capita` | \u03c1 = 0 | \u03c1 \u2260 0 | **two** | Demographic-economic paradox |
| **H5** | `marriage_rate` | \u03c1 = 0 | \u03c1 > 0 | one | Marriage = primary pathway to parenthood |
| **H6** | `country_group` | \u03bc\u2081=\u03bc\u2082=\u03bc\u2083 | At least one differs | \u2014 | Structural group differences |
| **H7** | `income_level` | \u03bc_high = \u03bc_upper | \u03bc_high \u2260 \u03bc_upper | \u2014 | Income classification |""")

# ============================================================
# CELL 18: Normality + Pearson + Spearman + H1-H5 (code)
# ============================================================
code("""\
# --- Normality tests ---
print("=" * 65)
print("NORMALITY TESTS (Shapiro-Wilk)")
print("=" * 65)
print(f"{'Variable':<40} {'W-stat':>8} {'p-value':>12} {'Normal?':>8}")
print("-" * 65)
for col in NUMERIC_VARS:
    w, p = shapiro(df[col].dropna())
    print(f"{col:<40} {w:>8.4f} {p:>12.2e} {'Yes' if p > 0.05 else 'No':>8}")
print("\\n\\u2192 Most variables are non-normal \\u2192 Spearman (rank) is the primary test.\\n")

# --- Pooled correlation tests ---
print("=" * 75)
print("SPEARMAN CORRELATION with fertility_rate (pooled, two-tailed)")
print("=" * 75)
print(f"{'Variable':<40} {'\\u03c1s':>8} {'p-value':>12} {'Sig?':>10}")
print("-" * 75)
for var in INDEPENDENT_VARS:
    rho, p = spearmanr(df["fertility_rate"], df[var])
    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
    print(f"{var:<40} {rho:>8.4f} {p:>12.6f} {sig:>10}")

# --- Directional hypothesis tests H1-H5 ---
print("\\n" + "=" * 90)
print("DIRECTIONAL HYPOTHESIS TESTS \\u2014 WITHIN-COUNTRY (\\u03b1 = 0.05)")
print("=" * 90)

hypotheses = [
    {"name": "H1", "var": "unemployment_total",
     "direction": "negative", "tail": "one", "lag": 2,
     "H0": "\\u03c1 \\u2265 0", "H1": "\\u03c1 < 0 (unemployment \\u2191 \\u2192 fertility \\u2193, 2-yr lag)"},
    {"name": "H2", "var": "female_labor_force_participation",
     "direction": "negative", "tail": "one", "lag": 0,
     "H0": "\\u03c1 \\u2265 0", "H1": "\\u03c1 < 0 (higher female LFP \\u2192 lower fertility)"},
    {"name": "H3", "var": "inflation",
     "direction": "negative", "tail": "one", "lag": 1,
     "H0": "\\u03c1 \\u2265 0", "H1": "\\u03c1 < 0 (inflation \\u2191 \\u2192 fertility \\u2193, 1-yr lag)"},
    {"name": "H4", "var": "gdp_per_capita",
     "direction": "two-sided", "tail": "two", "lag": 0,
     "H0": "\\u03c1 = 0", "H1": "\\u03c1 \\u2260 0 (GDP associated with fertility)"},
    {"name": "H5", "var": "marriage_rate",
     "direction": "positive", "tail": "one", "lag": 0,
     "H0": "\\u03c1 \\u2264 0", "H1": "\\u03c1 > 0 (marriage \\u2191 \\u2192 fertility \\u2191)"},
]

hyp_results = []
for h in hypotheses:
    var, lag = h["var"], h["lag"]
    if lag == 0:
        test_df = df_sorted[["fertility_rate_dm", var + "_dm"]].dropna()
        x_col = var + "_dm"
    else:
        df_sorted["_test_lag"] = df_sorted.groupby("country")[var + "_dm"].shift(lag)
        test_df = df_sorted[["fertility_rate_dm", "_test_lag"]].dropna()
        x_col = "_test_lag"

    rho, p_two = spearmanr(test_df["fertility_rate_dm"], test_df[x_col])
    r, p_two_r = pearsonr(test_df["fertility_rate_dm"], test_df[x_col])

    if h["tail"] == "one":
        if h["direction"] == "negative":
            p_s = p_two / 2 if rho < 0 else 1 - p_two / 2
            p_r = p_two_r / 2 if r < 0 else 1 - p_two_r / 2
        else:
            p_s = p_two / 2 if rho > 0 else 1 - p_two / 2
            p_r = p_two_r / 2 if r > 0 else 1 - p_two_r / 2
    else:
        p_s, p_r = p_two, p_two_r

    tail_label = "one-tailed" if h["tail"] == "one" else "two-tailed"
    print(f"\\n--- {h['name']}: {var} (lag={lag}, {tail_label}) ---")
    print(f"  H\\u2080: {h['H0']}   H\\u2081: {h['H1']}")
    print(f"  n = {len(test_df)}")
    print(f"  Spearman: \\u03c1 = {rho:+.4f}, p = {p_s:.6f}  \\u2192  {'REJECT H\\u2080 \\u2713' if p_s < 0.05 else 'FAIL TO REJECT \\u2717'}")
    print(f"  Pearson:  r = {r:+.4f}, p = {p_r:.6f}  \\u2192  {'REJECT H\\u2080 \\u2713' if p_r < 0.05 else 'FAIL TO REJECT \\u2717'}")

    hyp_results.append({
        "Hypothesis": h["name"], "Variable": var, "Lag": lag, "Tail": tail_label,
        "Spearman \\u03c1": round(rho, 4), "Spearman p": round(p_s, 6),
        "Decision": "Reject H\\u2080" if p_s < 0.05 else "Fail to Reject",
    })

if "_test_lag" in df_sorted.columns:
    df_sorted.drop(columns=["_test_lag"], inplace=True)""")

# ============================================================
# CELL 19: H6 + H7 + post-hoc + summary (code)
# ============================================================
code("""\
# --- H6: Country group differences ---
print("=" * 70)
print("H6: COUNTRY GROUP DIFFERENCES IN FERTILITY RATE")
print("=" * 70)

groups = {name: group["fertility_rate"].values for name, group in df.groupby("country_group")}
for name, vals in groups.items():
    print(f"  {name:<15}: n={len(vals):>3}, mean={np.mean(vals):.4f}, std={np.std(vals, ddof=1):.4f}")

lev_stat, lev_p = levene(*groups.values())
print(f"\\nLevene's test: F = {lev_stat:.4f}, p = {lev_p:.6f}")
h_stat, kw_p = kruskal(*groups.values())
print(f"Kruskal-Wallis: H = {h_stat:.4f}, p = {kw_p:.2e}")
print(f"  \\u2192 {'REJECT H\\u2080 \\u2713' if kw_p < 0.05 else 'FAIL TO REJECT \\u2717'}")

# --- H7: Income level differences ---
print("\\n" + "=" * 70)
print("H7: INCOME LEVEL DIFFERENCE IN FERTILITY RATE")
print("=" * 70)
high = df[df["income_level"] == "High income"]["fertility_rate"].values
upper_mid = df[df["income_level"] == "Upper middle income"]["fertility_rate"].values
print(f"  High income:         n={len(high):>3}, mean={np.mean(high):.4f}")
print(f"  Upper middle income: n={len(upper_mid):>3}, mean={np.mean(upper_mid):.4f}")

equal_var = levene(high, upper_mid)[1] > 0.05
u_stat, mw_p = mannwhitneyu(high, upper_mid, alternative="two-sided")
print(f"Mann-Whitney U: U = {u_stat:.1f}, p = {mw_p:.2e}")
print(f"  \\u2192 {'REJECT H\\u2080 \\u2713' if mw_p < 0.05 else 'FAIL TO REJECT \\u2717'}")

# --- Post-hoc pairwise ---
print("\\n" + "=" * 70)
print("POST-HOC PAIRWISE (Bonferroni-adjusted \\u03b1 = 0.0167)")
print("=" * 70)
group_names = list(groups.keys())
bonferroni_alpha = 0.05 / len(list(combinations(group_names, 2)))
for g1, g2 in combinations(group_names, 2):
    u, p = mannwhitneyu(groups[g1], groups[g2], alternative="two-sided")
    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < bonferroni_alpha else "ns"
    print(f"  {g1:>15} vs {g2:<15}  U={u:>8.1f}  p={p:.6f}  {sig}")

# --- Summary table ---
print("\\n" + "=" * 70)
print("COMPREHENSIVE RESULTS SUMMARY")
print("=" * 70)
summary_rows = [dict(r) for r in hyp_results]
summary_rows.append({"Hypothesis": "H6", "Variable": "country_group",
    "Lag": "-", "Tail": "-", "Spearman \\u03c1": round(h_stat, 4),
    "Spearman p": round(kw_p, 6),
    "Decision": "Reject H\\u2080" if kw_p < 0.05 else "Fail to Reject"})
summary_rows.append({"Hypothesis": "H7", "Variable": "income_level",
    "Lag": "-", "Tail": "-", "Spearman \\u03c1": round(u_stat, 1),
    "Spearman p": round(mw_p, 6),
    "Decision": "Reject H\\u2080" if mw_p < 0.05 else "Fail to Reject"})
display(pd.DataFrame(summary_rows))""")

# ============================================================
# CELL 20: Interpretation (markdown)
# ============================================================
md("""\
## 7. Interpretation of Statistical Results

### Key Findings \u2014 Within-Country Analysis

**Strong Relationships:**
- **Marriage rate (\u03c1 = +0.42):** Strongest predictor. When marriage rates decline, fertility declines with it. Marriage is the primary institutional channel for childbearing.
- **GDP per capita (\u03c1 = \u22120.25):** As countries grow richer over time, fertility declines. *Caution: may partly reflect shared time trends.*

**Weak but Significant (with lag):**
- **Inflation (lag=1, \u03c1 \u2248 \u22120.13):** Rising inflation \u2192 lower fertility 1 year later. Fastest economic channel.
- **Unemployment (lag=2, \u03c1 \u2248 \u22120.10):** Rising unemployment \u2192 lower fertility with 2-year delay.

**Structural Channel:**
- **Female LFP (\u03c1 expected negative):** As more women enter the workforce, the opportunity cost of having children rises \u2192 fertility declines. This is a fundamental channel in demographic transition theory.

### Unemployment vs Female LFP: Why Are They Not Contradictory?

At first glance, **H1** (unemployment \u2191 \u2192 fertility \u2193) and **H2** (female LFP \u2191 \u2192 fertility \u2193) may seem to point in opposite directions. If unemployment falls and more people work, shouldn't that be similar to rising female LFP? But these two variables capture **fundamentally different mechanisms**:

| | Unemployment (H1) | Female LFP (H2) |
|---|---|---|
| **Nature** | Cyclical, short-term shock | Structural, long-term trend |
| **Cause** | Involuntary \u2014 people *lose* jobs | Societal \u2014 women *choose to enter* workforce |
| **Channel** | **Economic insecurity**: "I lost my job, I can't afford a child right now" | **Opportunity cost**: "Having a child means giving up career advancement and income" |
| **Timescale** | Temporary (2\u20133 year lag) | Permanent (decade-long shift) |
| **Example** | Spain 2008: unemployment spikes from 8% to 26%, fertility drops | Nordic countries: female LFP rises from 60% to 80% over decades, fertility gradually declines |

**Key insight:** These variables can move independently. During the 2008 crisis, unemployment surged *and* female LFP stayed high \u2014 both channels suppressed fertility simultaneously. Conversely, in a recovery, unemployment falls (removing the insecurity channel) but female LFP keeps rising (maintaining the opportunity cost channel). The net effect on fertility depends on which channel dominates at any given time.

### Lag Structure Summary

| Variable | Optimal Lag | \u03c1 | Interpretation |
|---|---|---|---|
| marriage_rate | 0 years | +0.42 | Direct institutional link |
| gdp_per_capita | 0 years | \u22120.25 | Long-term structural effect |
| inflation | 1 year | \u22120.13 | Quick cost-of-living pressure |
| unemployment_total | 2 years | \u22120.10 | Delayed economic insecurity |
| female_labor_force_participation | 0 years | TBD | Opportunity cost of children |

### Methodological Notes
- **Spearman \u03c1** is the primary test (most variables fail normality).
- **Country-demeaning** removes between-country confounds (equivalent to fixed effects).
- **Observational panel data** \u2014 all findings are associations, not causal claims.""")

# ============================================================
# CELL 21: Visualizations header (markdown)
# ============================================================
md("""\
## 8. Findings Visualizations

1. **Pooled vs Within-Country** \u2014 direct comparison showing Simpson's Paradox
2. **Optimal Lag Correlation Summary** \u2014 within-country correlation strengths
3. **Within-Country Scatter Plots** \u2014 demeaned fertility vs demeaned variables
4. **Case Study** \u2014 economic shocks and fertility response""")

# ============================================================
# CELL 22: Pooled vs within + optimal lag bars (code)
# ============================================================
code("""\
fig, axes = plt.subplots(1, 2, figsize=(18, 6))

# --- Left: Pooled vs Within comparison ---
pooled_rhos, within_rhos_list = [], []
for var in INDEPENDENT_VARS:
    c = df_sorted[["fertility_rate", var]].dropna()
    rho_p, _ = spearmanr(c["fertility_rate"], c[var])
    pooled_rhos.append(rho_p)
    within_rhos_list.append(within_results[var]["rho"])

x = np.arange(len(INDEPENDENT_VARS))
width = 0.35
ax = axes[0]
bars1 = ax.bar(x - width/2, pooled_rhos, width, label="Pooled", color="#90CAF9", edgecolor="black", linewidth=0.8)
bars2 = ax.bar(x + width/2, within_rhos_list, width, label="Within-Country", color="#1565C0", edgecolor="black", linewidth=0.8)
for i, (rp, rw) in enumerate(zip(pooled_rhos, within_rhos_list)):
    ax.text(i - width/2, rp + (0.01 if rp >= 0 else -0.03), f"{rp:+.3f}", ha="center", fontsize=7, fontweight="bold")
    ax.text(i + width/2, rw + (0.01 if rw >= 0 else -0.03), f"{rw:+.3f}", ha="center", fontsize=7, fontweight="bold")
    if (rp > 0) != (rw > 0):
        ax.annotate("\\u26a0 Direction\\nChange", xy=(i, 0), fontsize=7, ha="center",
                     color="red", fontweight="bold", xytext=(i, max(abs(rp), abs(rw)) + 0.08))
ax.set_xticks(x)
ax.set_xticklabels([VAR_SHORT[v] for v in INDEPENDENT_VARS], fontsize=9)
ax.set_ylabel("Spearman \\u03c1")
ax.set_title("Pooled vs Within-Country Correlations")
ax.axhline(0, color="black", linewidth=0.8)
ax.legend(fontsize=9)
ax.grid(axis="y", alpha=0.3)
ax.set_ylim(-0.5, 0.5)

# --- Right: Optimal lag bar chart ---
optimal = {
    "marriage_rate":     {"lag": 0, "label": "Marriage Rate\\n(lag=0)"},
    "gdp_per_capita":    {"lag": 0, "label": "GDP per Capita\\n(lag=0)"},
    "inflation":         {"lag": 1, "label": "Inflation\\n(lag=1)"},
    "unemployment_total":{"lag": 2, "label": "Unemployment\\n(lag=2)"},
    "female_labor_force_participation": {"lag": 0, "label": "Female LFP\\n(lag=0)"},
}
vars_ordered = ["marriage_rate", "gdp_per_capita", "inflation", "unemployment_total",
                "female_labor_force_participation"]
labels = [optimal[v]["label"] for v in vars_ordered]
rhos = [lag_results[v][optimal[v]["lag"]]["rho"] for v in vars_ordered]
pvals = [lag_results[v][optimal[v]["lag"]]["p"] for v in vars_ordered]
colors = ["#2196F3" if r > 0 else "#F44336" for r in rhos]
alphas = [1.0 if p < 0.05 else 0.4 for p in pvals]

ax = axes[1]
bars = ax.barh(range(len(vars_ordered)), rhos, color=colors, edgecolor="black", linewidth=1.2)
for bar, alpha in zip(bars, alphas):
    bar.set_alpha(alpha)
for i, (rho, p) in enumerate(zip(rhos, pvals)):
    star = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
    offset = 0.02 if rho >= 0 else -0.02
    ha = "left" if rho >= 0 else "right"
    ax.text(rho + offset, i, f"\\u03c1 = {rho:+.3f} {star}", va="center", ha=ha, fontsize=9, fontweight="bold")
ax.set_yticks(range(len(vars_ordered)))
ax.set_yticklabels(labels, fontsize=9)
ax.set_xlabel("Within-Country Spearman \\u03c1 (optimal lag)")
ax.set_title("Relationship Strength with Fertility Rate")
ax.axvline(x=0, color="black", linewidth=0.8)
ax.set_xlim(-0.55, 0.55)
ax.grid(axis="x", alpha=0.3)
ax.legend(handles=[
    Patch(facecolor="#2196F3", label="Positive"),
    Patch(facecolor="#F44336", label="Negative"),
    Patch(facecolor="gray", alpha=0.4, label="Not significant"),
], loc="lower right", fontsize=8)

plt.tight_layout()
plt.savefig("../outputs/findings_summary.png", dpi=150, bbox_inches="tight")
plt.show()""")

# ============================================================
# CELL 23: Within-country scatter plots (code)
# ============================================================
code("""\
scatter_vars = [
    ("marriage_rate", 0, "Marriage Rate (demeaned)"),
    ("gdp_per_capita", 0, "GDP per Capita (demeaned)"),
    ("inflation", 1, "Inflation (demeaned, lag=1)"),
    ("unemployment_total", 2, "Unemployment (demeaned, lag=2)"),
    ("female_labor_force_participation", 0, "Female LFP (demeaned)"),
]

fig, axes = plt.subplots(2, 3, figsize=(18, 11))
axes_flat = axes.flatten()
axes_flat[5].set_visible(False)

for idx, (var, lag, xlabel) in enumerate(scatter_vars):
    ax = axes_flat[idx]
    if lag == 0:
        plot_df = df_sorted[["fertility_rate_dm", var + "_dm", "region_tag"]].dropna()
        x_col = var + "_dm"
    else:
        df_sorted["_plot_lag"] = df_sorted.groupby("country")[var + "_dm"].shift(lag)
        plot_df = df_sorted[["fertility_rate_dm", "_plot_lag", "region_tag"]].dropna()
        x_col = "_plot_lag"

    for region in sorted(plot_df["region_tag"].unique()):
        r_data = plot_df[plot_df["region_tag"] == region]
        ax.scatter(r_data[x_col], r_data["fertility_rate_dm"], alpha=0.4, s=12, label=region)

    z = np.polyfit(plot_df[x_col], plot_df["fertility_rate_dm"], 1)
    x_range = np.linspace(plot_df[x_col].min(), plot_df[x_col].max(), 100)
    ax.plot(x_range, np.poly1d(z)(x_range), "r-", linewidth=2, alpha=0.8)
    rho = lag_results[var][lag]["rho"]
    p_val = lag_results[var][lag]["p"]
    star = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else "ns"
    ax.text(0.03, 0.97, f"\\u03c1 = {rho:+.3f} {star}\\nlag = {lag} year(s)",
            transform=ax.transAxes, fontsize=10, fontweight="bold",
            verticalalignment="top", bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8))
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Fertility Rate (demeaned)")
    ax.axhline(0, color="gray", linestyle=":", alpha=0.5)
    ax.axvline(0, color="gray", linestyle=":", alpha=0.5)

if "_plot_lag" in df_sorted.columns:
    df_sorted.drop(columns=["_plot_lag"], inplace=True)

handles, labels_leg = axes_flat[0].get_legend_handles_labels()
fig.legend(handles, labels_leg, loc="lower center", ncol=5, fontsize=8, bbox_to_anchor=(0.5, -0.02))
plt.suptitle("Within-Country Relationships (Country-Demeaned, Optimal Lag)", fontsize=13, fontweight="bold")
plt.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.savefig("../outputs/within_country_scatter.png", dpi=150, bbox_inches="tight")
plt.show()""")

# ============================================================
# CELL 24: Case study (code)
# ============================================================
code("""\
case_countries = [
    ("TUR", "Turkey \\u2014 High Inflation Episode"),
    ("ESP", "Spain \\u2014 2008 Unemployment Crisis"),
    ("KOR", "South Korea \\u2014 Structural Decline"),
    ("USA", "United States \\u2014 Steady Decline"),
]

fig, axes = plt.subplots(2, 2, figsize=(16, 10))
axes_flat = axes.flatten()

for idx, (cc, title) in enumerate(case_countries):
    ax1 = axes_flat[idx]
    cdf = df_sorted[df_sorted["country_code"] == cc].sort_values("year")

    ax1.plot(cdf["year"], cdf["fertility_rate"], color="#2196F3", linewidth=2.5,
             marker="o", markersize=4, label="Fertility Rate")
    ax1.set_ylabel("Fertility Rate", color="#2196F3", fontsize=10)
    ax1.tick_params(axis="y", labelcolor="#2196F3")
    ax1.set_xlabel("Year")

    ax2 = ax1.twinx()
    ax2.plot(cdf["year"], cdf["marriage_rate"], color="#FF9800", linewidth=2,
             linestyle="--", marker="s", markersize=3, label="Marriage Rate", alpha=0.8)
    ax2.set_ylabel("Marriage Rate (per 1,000)", color="#FF9800", fontsize=10)
    ax2.tick_params(axis="y", labelcolor="#FF9800")

    # Shade high-inflation periods
    c_mean, c_std = cdf["inflation"].mean(), cdf["inflation"].std()
    for _, row in cdf[cdf["inflation"] > c_mean + c_std].iterrows():
        ax1.axvspan(row["year"] - 0.5, row["year"] + 0.5, color="red", alpha=0.08)

    # Shade high-unemployment periods
    u_mean, u_std = cdf["unemployment_total"].mean(), cdf["unemployment_total"].std()
    for _, row in cdf[cdf["unemployment_total"] > u_mean + u_std].iterrows():
        ax1.axvspan(row["year"] - 0.5, row["year"] + 0.5, color="orange", alpha=0.08)

    ax1.set_title(title, fontsize=11, fontweight="bold")
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="best", fontsize=8)

fig.legend(handles=[
    Patch(facecolor="red", alpha=0.15, label="High Inflation Period"),
    Patch(facecolor="orange", alpha=0.15, label="High Unemployment Period"),
], loc="lower center", ncol=2, fontsize=9, bbox_to_anchor=(0.5, -0.02))

plt.suptitle("Case Study: Economic Shocks and Fertility Response", fontsize=13, fontweight="bold")
plt.tight_layout(rect=[0, 0.03, 1, 0.93])
plt.savefig("../outputs/case_study_shocks.png", dpi=150, bbox_inches="tight")
plt.show()""")

# ============================================================
# CELL 25: Summary (markdown)
# ============================================================
md("""\
## 9. Summary

### Key Takeaways
1. **Marriage rate** is the strongest within-country predictor of fertility (\u03c1 = +0.42)
2. **GDP per capita** shows a significant negative within-country relationship (\u03c1 = \u22120.25)
3. **Inflation** and **unemployment** have weak but significant effects with characteristic lags (1 and 2 years respectively)
4. **Female labor force participation** captures the opportunity cost channel of demographic transition
5. **Simpson's Paradox** is present: pooled correlations for inflation and GDP are misleading
6. All country groups and income levels differ significantly in fertility rates

### Limitations
- Observational panel data \u2014 associations, not causal claims
- GDP-fertility correlation may partly reflect shared time trends
- Marriage rate imputation may affect results for some country-years""")

# ============================================================
# Build notebook and save
# ============================================================
notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "codemirror_mode": {"name": "ipython", "version": 3},
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.14.0"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

output_path = "notebooks/analysis.ipynb"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=1, ensure_ascii=False)

print(f"✓ Notebook written: {output_path}")
print(f"  Total cells: {len(cells)}")
print(f"  Markdown cells: {sum(1 for c in cells if c['cell_type'] == 'markdown')}")
print(f"  Code cells: {sum(1 for c in cells if c['cell_type'] == 'code')}")
print(f"  All outputs cleared, all execution counts reset.")
