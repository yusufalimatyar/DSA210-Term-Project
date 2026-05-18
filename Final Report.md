**Live Demo:** [Interactive Website](https://rococo-arithmetic-2c8174.netlify.app)

# **Fertility Rate Dynamics in OECD Countries (2000–2024)  
A Panel Data Analysis of Economic, Social, and Inequality Factors**

#### Abstract:
This project investigates factors that determine fertility rate across 34 OECD countries between 2000 and 2024. The dependent variable is fertility rate and independent variables include GDP per capita, inflation rates, marriage rates, female labor participation (FLP), and top 10 wealth/income share. Therefore, this projects both evaluates economic and social dynamics. Data set is enriched by social metrics in later stages of project. Most of the data integrated from World Bank database and OECD; however detailed inequality data is drawn from WID (World Inequality Database). After the data collection EDA (exploratory data analysis) techniques are applied and it revealed that pooled correlations can be misleading due to Simpson's Paradox (Actually it wasn't an issue for project's sake since initial hypothesis was based on with-in country analysis). Results show that marriage rate (lag=2, ρ≈+0.53) is the strongest positive predictor, while GDP per capita (lag=5, ρ≈−0.49) and female labor force participation (lag=5, ρ≈−0.35) are negatively associated with fertility. Both GDP increase and the drop in the fertility rates can be explained by trends. Moreover, against the initial assumption women who participate the labor force decrease fertility rates. The hypothesis was " if women earn more money than they would be more financially more comfortable with child care", however data analysis revealed that it is indeed not the case at all. Latter conclusion was women who work more have fewer time and effort to give birth and raise the child. Analysis also revealed the importance of the lag. Economic metrics affect fertility rate with a lag since both having a child takes 9 months and economic changes affect people with few years delay. Several group-based hypotheses are supported, while inequality-based hypotheses remain weak or unsupported. A machine learning pipeline (Linear Regression, Random Forest, Gradient Boosting) achieved strong pre-COVID fit but negative post-COVID test R², interpreted as a structural break rather than simple model failure. The project concludes that fertility dynamics are delayed, context-dependent, and difficult to predict with macroeconomic variables alone.

#### Introduction

Fertility decline is a major demographic and policy concern in developed and emerging economies. Literature suggests links with labor markets, income, social structure, and gender dynamics. This projects tries to figure out: **Which macroeconomic and social determinants are most associated with fertility changes in OECD countries?** Core contribution:

- Integrated multi-source panel dataset

- Within-country lag-based hypothesis testing

- Honest ML evaluation under temporal shift (COVID structural break)

- Integrating inequality data to macroeconomic variables

#### Data and Variables
##### Data Sources

- World Bank API
    
- OECD Family Database (marriage rate)
    
- World Inequality Database (top10 income/wealth share)
    

#####  Scope

- 34 OECD countries
    
- 2000–2024
    
- 850 rows, 17 columns, 100% complete final panel
    

##### Variables

- **Dependent:** `fertility_rate`
    
- **Independent:** `inflation`, `unemployment_total`, `female_labor_force_participation`, `gdp_per_capita`, `marriage_rate`, `income_share_top10`, `wealth_share_top10`, `income_wealth_ratio`
    
- **Tags:** `region_tag`, `income_level`, `country_group`

#### Methodology

##### Data Processing and EDA

WID and OECD data are drawn through API and WID data is installed and integrated manually since there was no other choice. Each data set is examined to find out whether there data is missing or consistent. After that data is scaled appropriately for later steps. All data sets are merged into a final OECD panel. After the construction of "final" version of panel, inequality data is integrated and panel is upgraded. EDA methods are applied on data sets and data visualizations (Distribution plots, boxplots, correlation heatmaps, region and country trend visualizations, -scatter analyses for each predictor vs fertility) are prepared. Necessary statistical analysis (Pearson/Spearman tests (pooled + within-country), lag scan (0–5 years) to capture delayed effects, hypothesis tests (H1–H9), plus group-difference tests (ANOVA/Kruskal/Mann-Whitney where appropriate) ) are implemented.

#### ML
The machine learning component was designed to evaluate the out-of-sample predictive capacity of the macroeconomic and social indicators identified in the statistical analysis. Specifically, it assessed whether relationships observed in the within-country and lag-based framework could be translated into reliable forecasting performance. To preserve temporal realism, the dataset was split chronologically into training (≤2018), validation (2019–2021), and test (2022–2024) periods, rather than using random partitioning. Feature engineering incorporated lagged predictors based on previously estimated optimal lag structure (e.g., marriage rate at 2 years, GDP per capita at 5 years), while country-demeaning was applied to isolate within-country variation and reduce bias from cross-country level differences. All numeric inputs were standardized, and multicollinearity diagnostics (VIF) were used to ensure a stable feature space. Three model families—Linear Regression, Random Forest, and Gradient Boosting—were compared using R², RMSE, and MAE. Results indicate strong fit in pre-COVID periods but substantial deterioration in the post-COVID test window, including negative R² values. This pattern is interpreted as evidence of a post-pandemic structural break in fertility dynamics, suggesting that models trained on pre-2020 macro patterns have limited generalization under regime change.


#### Results

Strongest positive channel is **marriage_rate (lag=2)** . Strong negative channel is **gdp_per_capita (lag=5)** and **female_labor_force_participation (lag=5)**. Unemployment has weak negative delayed relation. Inflation has sign/magnitude sensitive; weaker than expected relation. Inequality variables have weak and mostly non-robust relation with hypothesis direction
Pooled correlations mix between-country and within-country effects. Some variables reverse sign when switching to within-country framework. 
Fertility response appears **slow-moving** (2–5 year lags), consistent with family planning behavior. Marriage remains a central institutional/social channel. Economic modernization variables (GDP, female labor participation) show expected long-run negative association in within-country setting.
##### ML Performance
Good fit pre-COVID but much weaker/negative R² post-COVID. This is because of the structural break that covid caused. It is nor a regime shift or algorithmic underfitting. Emphasizing this result (negative R² values) is a deliberate choice and necessity of academic honesty. One practical takeaway is that macro variables alone are insufficent to explain the decline in fertility rates. Predictive modeling is constrained by:

- structural shocks (COVID),

- limited panel size,

- omitted social-policy/cultural variables.

#### Conclusion

This project finds that fertility dynamics in OECD countries are best understood through a within-country, lag-aware framework rather than pooled contemporaneous correlations. Marriage rate emerges as the strongest positive factor, while GDP per capita and female labor participation exhibit delayed negative associations. ML models confirm that pre-shock patterns are learnable but fail to extrapolate across post-COVID structural change. 


#### AI Disclaimer

In this project, AI tools were used at multiple stages, particularly during the implementation of machine learning models and parts of the exploratory data analysis (EDA). However, all core decisions—including project design, methodological choices, problem-solving strategy, interpretation of results, and final presentation—were made by me. AI was also used as a coding assistant during the implementation of the interactive website and its data visualizations. The final report was written by me, while AI support was limited to suggestions and technical guidance.