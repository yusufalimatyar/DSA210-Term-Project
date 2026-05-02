"""
data_collection.py - Veri Toplama Modülü
=========================================
Bu modül tüm ham verileri toplar ve birleştirir:

Kaynaklar:
  1. World Bank API v2 → fertility_rate, inflation, unemployment, female_labor_force_participation, gdp_per_capita
  2. OECD Family Database SF3.1 → marriage_rate (crude marriage rate per 1000)
  3. OECD Affordable Housing Database HM1.3 → homeownership_rate (%)
  4. World Inequality Database (WID) → income_share_top10, wealth_share_top10
  5. World Bank API → income_level metadata (ülke bazlı)

Çıktı:
  data/processed/final_panel.csv — Tüm ülkeler, tüm yıllar (1960-2025), ~14000 satır
"""

import re
import requests
import pandas as pd
from pathlib import Path


# ── Dizin Ayarları ──
RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


WID_ISO2_TO_ISO3 = {
    "US": "USA", "CA": "CAN", "GB": "GBR", "DE": "DEU", "FR": "FRA",
    "IT": "ITA", "ES": "ESP", "NL": "NLD", "BE": "BEL", "CH": "CHE",
    "AT": "AUT", "SE": "SWE", "NO": "NOR", "DK": "DNK", "FI": "FIN",
    "IE": "IRL", "PT": "PRT", "GR": "GRC", "PL": "POL", "CZ": "CZE",
    "HU": "HUN", "SK": "SVK", "SI": "SVN", "EE": "EST", "LV": "LVA",
    "LT": "LTU", "JP": "JPN", "KR": "KOR", "AU": "AUS", "NZ": "NZL",
    "MX": "MEX", "CL": "CHL", "CO": "COL", "TR": "TUR",
}

WID_ISO3_TO_COUNTRY = {
    "USA": "United States", "CAN": "Canada", "GBR": "United Kingdom", "DEU": "Germany", "FRA": "France",
    "ITA": "Italy", "ESP": "Spain", "NLD": "Netherlands", "BEL": "Belgium", "CHE": "Switzerland",
    "AUT": "Austria", "SWE": "Sweden", "NOR": "Norway", "DNK": "Denmark", "FIN": "Finland",
    "IRL": "Ireland", "PRT": "Portugal", "GRC": "Greece", "POL": "Poland", "CZE": "Czech Republic",
    "HUN": "Hungary", "SVK": "Slovakia", "SVN": "Slovenia", "EST": "Estonia", "LVA": "Latvia",
    "LTU": "Lithuania", "JPN": "Japan", "KOR": "South Korea", "AUS": "Australia", "NZL": "New Zealand",
    "MEX": "Mexico", "CHL": "Chile", "COL": "Colombia", "TUR": "Turkey",
}


def get_real_country_codes():
    """
    World Bank API'den gerçek ülke kodlarını ve metadata'yı çeker.

    World Bank API'de bazı kodlar aggregate (bölgesel toplam) oluyor.
    Bu fonksiyon sadece gerçek ülkeleri filtreler.

    Returns:
        tuple: (set of ISO3 codes, dict of {code: {income_level, wb_region}})
    """
    url = "https://api.worldbank.org/v2/country?format=json&per_page=400"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()

    rows = data[1]
    real_codes = []
    country_metadata = {}  # Her ülke için income_level ve wb_region

    for row in rows:
        region = row["region"]["value"]
        code = row["id"]

        # region == "Aggregates" olanlar bölgesel toplam, gerçek ülke değil
        if region != "Aggregates":
            real_codes.append(code)
            country_metadata[code] = {
                "income_level": row["incomeLevel"]["value"],
                "wb_region": region,
            }

    return set(real_codes), country_metadata


def fetch_world_bank_indicator(indicator_code, column_name, real_country_codes):
    """
    World Bank API'den tek bir gösterge (indicator) çeker.

    Args:
        indicator_code: World Bank indicator kodu (örn: "SP.DYN.TFRT.IN")
        column_name: DataFrame'deki sütun adı (örn: "fertility_rate")
        real_country_codes: Sadece bu ülke kodlarını filtrele

    Returns:
        DataFrame: country, country_code, year, <column_name>
    """
    url = f"https://api.worldbank.org/v2/country/all/indicator/{indicator_code}?format=json&per_page=25000"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()

    rows = data[1]
    cleaned = []

    for row in rows:
        country = row["country"]["value"]
        code = row["countryiso3code"]
        year = row["date"]
        value = row["value"]

        # Aggregate kodları çıkar, sadece gerçek ülkeleri al
        if code in real_country_codes:
            cleaned.append({
                "country": country,
                "country_code": code,
                "year": year,
                column_name: value
            })

    df = pd.DataFrame(cleaned)
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.dropna(subset=["year"])
    df["year"] = df["year"].astype(int)

    return df


def load_wid_inequality_csv():
    """
    WID ham export dosyasını standardize edip inequality verisini yükler.

    Desteklenen girişler:
      - data/raw/wid_inequality.csv (önceden dönüştürülmüş)
      - data/raw/WID_Data_*.csv (WID ham export)

    Çıktı sütunları:
      country, country_code, year, income_share_top10, wealth_share_top10, income_wealth_ratio
    """
    standardized_path = RAW_DIR / "wid_inequality.csv"

    if standardized_path.exists():
        df = pd.read_csv(standardized_path)
        expected = {
            "country", "country_code", "year",
            "income_share_top10", "wealth_share_top10", "income_wealth_ratio",
        }
        if not expected.issubset(df.columns):
            raise ValueError(
                "wid_inequality.csv içinde şu sütunlar olmalı: "
                "country, country_code, year, income_share_top10, wealth_share_top10, income_wealth_ratio"
            )
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df = df.dropna(subset=["year"]).copy()
        df["year"] = df["year"].astype(int)
        return df

    candidates = sorted(RAW_DIR.glob("WID_Data_*.csv"))
    if not candidates:
        print("WID dosyası bulunamadı, atlanıyor.")
        return None

    wid_raw_path = candidates[-1]
    raw_df = pd.read_csv(wid_raw_path, sep=";", skiprows=1)

    raw_df.columns = [str(c).strip() for c in raw_df.columns]
    raw_df = raw_df.rename(columns={"Percentile": "Percentile", "Percentile ": "Percentile", "Year": "Year", "Year ": "Year"})

    if "Percentile" in raw_df.columns:
        raw_df = raw_df[raw_df["Percentile"].astype(str).str.strip() == "p90p100"].copy()

    raw_df["Year"] = pd.to_numeric(raw_df["Year"], errors="coerce")
    raw_df = raw_df.dropna(subset=["Year"]).copy()
    raw_df["Year"] = raw_df["Year"].astype(int)
    raw_df = raw_df[(raw_df["Year"] >= 2000) & (raw_df["Year"] <= 2024)].copy()

    income_cols = {}
    wealth_cols = {}
    for col in raw_df.columns:
        m = re.match(r"^(sptinc_z|shweal_z)_([A-Z]{2})", col)
        if not m:
            continue
        metric, iso2 = m.group(1), m.group(2)
        iso3 = WID_ISO2_TO_ISO3.get(iso2)
        if iso3 is None:
            continue
        if metric == "sptinc_z":
            income_cols[iso3] = col
        elif metric == "shweal_z":
            wealth_cols[iso3] = col

    records = []
    for _, row in raw_df.iterrows():
        year = int(row["Year"])
        for iso3 in WID_ISO3_TO_COUNTRY:
            inc_col = income_cols.get(iso3)
            wea_col = wealth_cols.get(iso3)
            if not inc_col or not wea_col:
                continue

            inc_val = pd.to_numeric(row.get(inc_col), errors="coerce")
            wea_val = pd.to_numeric(row.get(wea_col), errors="coerce")
            if pd.isna(inc_val) or pd.isna(wea_val):
                continue

            ratio = inc_val / wea_val if wea_val != 0 else None
            records.append({
                "country": WID_ISO3_TO_COUNTRY[iso3],
                "country_code": iso3,
                "year": year,
                "income_share_top10": float(inc_val),
                "wealth_share_top10": float(wea_val),
                "income_wealth_ratio": float(ratio) if ratio is not None else None,
            })

    result = pd.DataFrame(records)
    if result.empty:
        print("WID ham dosyası parse edilemedi, atlanıyor.")
        return None

    result = result.sort_values(["country_code", "year"]).drop_duplicates(
        subset=["country_code", "year"],
        keep="last"
    ).reset_index(drop=True)
    result.to_csv(standardized_path, index=False)
    print(f"WID verisi standardize edildi: {standardized_path} ({len(result)} satır)")

    return result


def merge_panel(dfs):
    """
    Birden fazla DataFrame'i country_code + year üzerinden birleştirir.
    Outer join kullanır — eksik olan yıl/ülke kombinasyonları NaN olarak kalır.

    NOT: Sadece country_code + year kullanıyoruz çünkü farklı kaynaklar
    aynı ülke için farklı isim kullanabiliyor (örn: "Korea" vs "Korea, Rep.").
    country adı sonra eklenir.
    """
    # Her df'den country sütununu ayır, sadece country_code + year + value ile merge yap
    country_names = {}  # {country_code: country_name} — en son gelen kazanır

    cleaned_dfs = []
    for df in dfs:
        df_copy = df.copy()
        if "country" in df_copy.columns:
            # Ülke adlarını topla (NaN olmayan ilk adı al)
            for _, row in df_copy.dropna(subset=["country"]).iterrows():
                code = row["country_code"]
                name = row["country"]
                if code not in country_names:
                    country_names[code] = name
            df_copy = df_copy.drop(columns=["country"])
        cleaned_dfs.append(df_copy)

    merged = cleaned_dfs[0]
    for df in cleaned_dfs[1:]:
        merged = merged.merge(
            df,
            on=["country_code", "year"],
            how="outer"
        )

    # country adını geri ekle (country_code'dan)
    merged.insert(0, "country", merged["country_code"].map(country_names))

    return merged


# ── OECD Excel dosyalarındaki ülke adlarını ISO3 kodlara çeviren sözlük ──
# OECD farklı yazımlar kullanabiliyor (örn: "Türkiye" vs "Turkey", "Czechia" vs "Czech Republic")
COUNTRY_NAME_TO_ISO3 = {
    "Australia": "AUS", "Austria": "AUT", "Belgium": "BEL", "Canada": "CAN",
    "Chile": "CHL", "Colombia": "COL", "Costa Rica": "CRI", "Czechia": "CZE",
    "Czech Republic": "CZE", "Denmark": "DNK", "Estonia": "EST", "Finland": "FIN",
    "France": "FRA", "Germany": "DEU", "Greece": "GRC", "Hungary": "HUN",
    "Iceland": "ISL", "Ireland": "IRL", "Israel": "ISR", "Italy": "ITA",
    "Japan": "JPN", "Korea": "KOR", "Latvia": "LVA", "Lithuania": "LTU",
    "Luxembourg": "LUX", "Mexico": "MEX", "Netherlands": "NLD",
    "New Zealand": "NZL", "Norway": "NOR", "Poland": "POL", "Portugal": "PRT",
    "Slovak Republic": "SVK", "Slovakia": "SVK", "Slovenia": "SVN", "Spain": "ESP",
    "Sweden": "SWE", "Switzerland": "CHE", "Türkiye": "TUR", "Turkey": "TUR",
    "United Kingdom": "GBR", "United States": "USA",
    "Argentina": "ARG", "Brazil": "BRA", "Bulgaria": "BGR", "China": "CHN",
    "Croatia": "HRV", "Cyprus": "CYP", "India": "IND", "Indonesia": "IDN",
    "Lithuania ": "LTU", "Malta": "MLT", "Peru": "PER", "Romania": "ROU",
    "Russia": "RUS", "Russian Federation": "RUS", "Saudi Arabia": "SAU",
    "South Africa": "ZAF", "Türkiye ": "TUR",
}


def prepare_oecd_marriage_data():
    """
    OECD Family Database SF3.1'den evlilik oranı verisini indirir ve parse eder.

    Kaynak: https://webfs.oecd.org/els-com/Family_Database/SF_3_1_Marriage_divorce_rates.xlsx
    Sheet: "MarriageRates" — Crude marriage rate (1000 kişi başına evlenme sayısı)
    Format: Wide (ülke x yıl) → Long (country, country_code, year, marriage_rate) dönüşümü yapılır.
    """
    raw_path = RAW_DIR / "oecd_marriage_raw.xlsx"
    out_path = RAW_DIR / "oecd_marriage_rate.csv"

    if not raw_path.exists():
        url = "https://webfs.oecd.org/els-com/Family_Database/SF_3_1_Marriage_divorce_rates.xlsx"
        print("Evlilik oranı verisi indiriliyor...")
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        with open(raw_path, "wb") as f:
            f.write(r.content)
        print(f"Indirildi: {len(r.content)} bytes")

    # Excel yapısı: Satır 3 = başlık (yıllar), Sütun 0 = ISO3 kod, Sütun 1 = ülke adı
    df = pd.read_excel(raw_path, sheet_name="MarriageRates", header=None)

    years = df.iloc[3, 3:].values  # Yıl başlıkları (1960, 1961, ..., 2022)
    rows = []

    # Satır 4'ten itibaren ülke verileri başlıyor
    for i in range(4, len(df)):
        code = df.iloc[i, 0]
        name = df.iloc[i, 1]
        if pd.isna(name) or pd.isna(code):
            continue
        name = str(name).strip()
        code = str(code).strip()

        if len(code) != 3:
            continue

        for j, year in enumerate(years):
            val = df.iloc[i, j + 3]
            if pd.isna(val) or val == ".." or val == "..":
                continue
            try:
                val = float(val)
                yr = int(float(year))
            except (ValueError, TypeError):
                continue
            if yr >= 2000:
                rows.append({
                    "country": name,
                    "country_code": code,
                    "year": yr,
                    "marriage_rate": val,
                })

    result = pd.DataFrame(rows)
    result.to_csv(out_path, index=False)
    print(f"Marriage rate verisi kaydedildi: {out_path} ({len(result)} satır)")
    return result


def prepare_oecd_homeownership_data():
    """
    OECD Affordable Housing Database HM1.3'den konut sahipliği verisini indirir ve parse eder.

    Kaynak: https://webfs.oecd.org/els-com/Affordable_Housing_Database/HM1-3-Housing-tenures.xlsx
    Sheet: "HM1.3.A1" — Housing tenure distribution by year
    Homeownership = "Own outright" + "Owner with mortgage" toplamı olarak hesaplanır.
    """
    raw_path = RAW_DIR / "oecd_homeownership_raw.xlsx"
    out_path = RAW_DIR / "oecd_homeownership.csv"

    if not raw_path.exists():
        url = "https://webfs.oecd.org/els-com/Affordable_Housing_Database/HM1-3-Housing-tenures.xlsx"
        print("Konut sahipliği verisi indiriliyor...")
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        with open(raw_path, "wb") as f:
            f.write(r.content)
        print(f"Indirildi: {len(r.content)} bytes")

    df = pd.read_excel(raw_path, sheet_name="HM1.3.A1", header=None)

    years = df.iloc[4, 2:].values
    year_cols = []
    for y in years:
        try:
            year_cols.append(int(float(y)))
        except (ValueError, TypeError):
            year_cols.append(None)

    # Konut sahipliği = tamamen sahip + ipotekli sahip toplamı
    ownership_types = {"Own outright", "Owner with mortgage"}

    country_data = {}   # {(ülke, yıl): toplam sahiplik oranı}
    current_country = None

    # Her ülke için birden fazla satır var (farklı tenure tipleri)
    # Ülke adı sadece ilk satırda yazılı, sonrakiler boş
    for i in range(5, len(df)):
        c = df.iloc[i, 0]
        if pd.notna(c):
            current_country = str(c).strip()

        tenure = df.iloc[i, 1]
        if pd.isna(tenure) or current_country is None:
            continue
        tenure = str(tenure).strip()

        if tenure not in ownership_types:
            continue

        for j, yr in enumerate(year_cols):
            if yr is None or yr < 2000:
                continue
            val = df.iloc[i, j + 2]
            if pd.isna(val) or str(val).strip() == "..":
                continue
            try:
                val = float(val)
            except (ValueError, TypeError):
                continue

            key = (current_country, yr)
            if key not in country_data:
                country_data[key] = 0.0
            country_data[key] += val

    rows = []
    for (country, year), rate in country_data.items():
        iso3 = COUNTRY_NAME_TO_ISO3.get(country)
        if iso3 is None:
            continue
        rows.append({
            "country": country,
            "country_code": iso3,
            "year": year,
            "homeownership_rate": round(rate, 2),
        })

    result = pd.DataFrame(rows)
    result = result.sort_values(["country_code", "year"]).reset_index(drop=True)
    result.to_csv(out_path, index=False)
    print(f"Homeownership verisi kaydedildi: {out_path} ({len(result)} satır)")
    return result


def load_oecd_marriage_csv():
    """
    Beklenen dosya:
    data/raw/oecd_marriage_rate.csv

    Beklenen sütunlar:
    country, country_code, year, marriage_rate
    """
    path = RAW_DIR / "oecd_marriage_rate.csv"
    if not path.exists():
        print("Marriage CSV bulunamadı, atlanıyor.")
        return None

    df = pd.read_csv(path)
    expected = {"country", "country_code", "year", "marriage_rate"}

    if not expected.issubset(df.columns):
        raise ValueError(
            "oecd_marriage_rate.csv içinde şu sütunlar olmalı: "
            "country, country_code, year, marriage_rate"
        )

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.dropna(subset=["year"])
    df["year"] = df["year"].astype(int)

    return df


def load_oecd_homeownership_xlsx():
    """
    Beklenen dosya:
    data/raw/oecd_homeownership.xlsx

    Not:
    OECD HM1.3 dosya yapısı ülke / sütun isimleri bazen değişebiliyor.
    Bu yüzden burada iki seçenek var:
    1) Dosyayı kendin sadeleştirip aşağıdaki standarda getirirsin
    2) Ya da sheet/sütun adlarını bana sonra gösterirsin, birlikte uyarlarız

    Beklenen sade format:
    country, country_code, year, homeownership_rate
    """
    xlsx_path = RAW_DIR / "oecd_homeownership.xlsx"
    csv_path = RAW_DIR / "oecd_homeownership.csv"

    if csv_path.exists():
        df = pd.read_csv(csv_path)
    elif xlsx_path.exists():
        df = pd.read_excel(xlsx_path)
    else:
        print("Homeownership dosyası bulunamadı, atlanıyor.")
        return None

    expected = {"country", "country_code", "year", "homeownership_rate"}

    if not expected.issubset(df.columns):
        raise ValueError(
            "oecd_homeownership dosyasında şu sütunlar olmalı: "
            "country, country_code, year, homeownership_rate"
        )

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.dropna(subset=["year"])
    df["year"] = df["year"].astype(int)

    return df


def main():
    """
    Ana veri toplama pipeline'ı:
    1. World Bank API'den ülke kodları ve metadata çek
    2. 4 ekonomik göstergeyi World Bank'tan çek
    3. OECD evlilik ve konut sahipliği verilerini indir/parse et
    4. WID eşitsizlik verisini yükle/standardize et
    5. Hepsini birleştirip final_panel.csv olarak kaydet
    """
    # Adım 1: Ülke kodları + income_level metadata
    real_country_codes, country_metadata = get_real_country_codes()

    # Adım 2: World Bank göstergelerini çek ve raw olarak kaydet
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    fertility_df = fetch_world_bank_indicator(
        "SP.DYN.TFRT.IN",
        "fertility_rate",
        real_country_codes
    )
    fertility_df.to_csv(RAW_DIR / "fertility_rate.csv", index=False)
    print(f"  Raw kaydedildi: fertility_rate.csv ({len(fertility_df)} satır)")

    inflation_df = fetch_world_bank_indicator(
        "FP.CPI.TOTL.ZG",
        "inflation",
        real_country_codes
    )
    inflation_df.to_csv(RAW_DIR / "inflation.csv", index=False)
    print(f"  Raw kaydedildi: inflation.csv ({len(inflation_df)} satır)")

    unemployment_df = fetch_world_bank_indicator(
        "SL.UEM.TOTL.ZS",
        "unemployment_total",
        real_country_codes
    )
    unemployment_df.to_csv(RAW_DIR / "unemployment_total.csv", index=False)
    print(f"  Raw kaydedildi: unemployment_total.csv ({len(unemployment_df)} satır)")

    female_lfp_df = fetch_world_bank_indicator(
        "SL.TLF.CACT.FE.ZS",
        "female_labor_force_participation",
        real_country_codes
    )
    female_lfp_df.to_csv(RAW_DIR / "female_labor_force_participation.csv", index=False)
    print(f"  Raw saved: female_labor_force_participation.csv ({len(female_lfp_df)} rows)")

    # GDP per capita PPP (purchasing power parity, current international $)
    # PPP adjusts for inflation and exchange rate differences across countries
    # Source: World Bank indicator NY.GDP.PCAP.PP.CD
    gdp_df = fetch_world_bank_indicator(
        "NY.GDP.PCAP.PP.CD",
        "gdp_per_capita",
        real_country_codes
    )
    gdp_df.to_csv(RAW_DIR / "gdp_per_capita.csv", index=False)
    print(f"  Raw saved: gdp_per_capita.csv ({len(gdp_df)} rows)")

    dfs = [
        fertility_df,
        inflation_df,
        unemployment_df,
        female_lfp_df,
        gdp_df
    ]

    # Adım 3: OECD verilerini hazırla (yoksa indir ve parse et)
    if not (RAW_DIR / "oecd_marriage_rate.csv").exists():
        prepare_oecd_marriage_data()
    if not (RAW_DIR / "oecd_homeownership.csv").exists():
        prepare_oecd_homeownership_data()

    marriage_df = load_oecd_marriage_csv()
    if marriage_df is not None:
        dfs.append(marriage_df)

    homeownership_df = load_oecd_homeownership_xlsx()
    if homeownership_df is not None:
        dfs.append(homeownership_df)

    wid_df = load_wid_inequality_csv()
    if wid_df is not None:
        dfs.append(wid_df)

    # Adım 5: Tüm veri kaynaklarını birleştir
    final_df = merge_panel(dfs)

    # income_level sütununu World Bank metadata'sından ekle
    final_df["income_level"] = final_df["country_code"].map(
        lambda c: country_metadata.get(c, {}).get("income_level", None)
    )

    final_df = final_df.sort_values(["country_code", "year"]).reset_index(drop=True)

    final_df.to_csv(PROCESSED_DIR / "final_panel.csv", index=False)

    print("Final panel kaydedildi.")
    print(final_df.head())
    print("\nSütunlar:")
    print(final_df.columns.tolist())
    print("\nBoyut:")
    print(final_df.shape)


if __name__ == "__main__":
    main()