"""
data_cleaning.py - Veri Temizleme ve Ön İşleme Modülü 
=======================================================
Bu modül final_panel.csv'yi alır ve ML-ready hale getirir:

Adımlar:
  1. Zaman filtresi: sadece 2000+ yıllar
  2. Ülke filtresi: sadece 34 OECD ülkesi
  3. Kategorik etiketler: region_tag (9 bölge), country_group (3 analiz grubu)
  4. Outlier tespiti ve işaretleme
  5. Missing value raporu

Çıktılar:
  data/processed/final_panel_filtered.csv — Tüm ülkeler, 2000+
  data/processed/final_oecd.csv           — Sadece OECD, temizlenmiş, etiketli
"""

import pandas as pd
import numpy as np


# ── 34 OECD Ülkesi (ISO3 kodları) ──
OECD_COUNTRIES = [
    "USA", "CAN", "GBR", "DEU", "FRA", "ITA", "ESP", "NLD", "BEL", "CHE", "AUT",
    "SWE", "NOR", "DNK", "FIN", "IRL", "PRT", "GRC", "POL", "CZE", "HUN", "SVK",
    "SVN", "EST", "LVA", "LTU", "JPN", "KOR", "AUS", "NZL", "MEX", "CHL", "COL", "TUR"
]

# ── Coğrafi Bölge Etiketleri (9 bölge) ──
# Araştırmalarda kullanılan standart bölgesel gruplandırma
REGION_TAG_MAP = {
    "USA": "North America",
    "CAN": "North America",
    "MEX": "North America",
    "DEU": "Western Europe",
    "FRA": "Western Europe",
    "GBR": "Western Europe",
    "NLD": "Western Europe",
    "BEL": "Western Europe",
    "CHE": "Western Europe",
    "AUT": "Western Europe",
    "IRL": "Western Europe",
    "ITA": "Southern Europe",
    "ESP": "Southern Europe",
    "PRT": "Southern Europe",
    "GRC": "Southern Europe",
    "SWE": "Northern Europe",
    "NOR": "Northern Europe",
    "DNK": "Northern Europe",
    "FIN": "Northern Europe",
    "POL": "Eastern Europe",
    "CZE": "Eastern Europe",
    "HUN": "Eastern Europe",
    "SVK": "Eastern Europe",
    "SVN": "Eastern Europe",
    "EST": "Eastern Europe",
    "LVA": "Eastern Europe",
    "LTU": "Eastern Europe",
    "JPN": "East Asia",
    "KOR": "East Asia",
    "AUS": "Oceania",
    "NZL": "Oceania",
    "CHL": "Latin America",
    "COL": "Latin America",
    "TUR": "Middle East",
}

# ── Analiz Grupları (araştırma mantığına uygun) ──
# Aynı modelde çok farklı yapılar karıştırılmamalı.
# Bu gruplar filtreleme için kullanılacak:
#   - "developed"   → Benchmark grup: homojen, veri kaliteli, doğurganlık düşük
#   - "transition"  → Geçiş ülkeleri: gelişmişe yakın ama farklı dinamikler
#   - "special_case" → Literatürde özel olarak incelenen ülkeler (ultra-düşük fertility, kriz)
COUNTRY_GROUP_MAP = {
    # Gelişmiş ülkeler (benchmark) — High income, istikrarlı ekonomi
    "USA": "developed", "CAN": "developed", "GBR": "developed",
    "DEU": "developed", "FRA": "developed", "NLD": "developed",
    "BEL": "developed", "CHE": "developed", "AUT": "developed",
    "IRL": "developed", "SWE": "developed", "NOR": "developed",
    "DNK": "developed", "FIN": "developed", "AUS": "developed",
    "NZL": "developed",

    # Geçiş / gelişmekte olan ülkeler — Upper middle income veya geç OECD üyeliği
    "MEX": "transition", "COL": "transition", "TUR": "transition",
    "CHL": "transition", "POL": "transition", "CZE": "transition",
    "HUN": "transition", "SVK": "transition", "SVN": "transition",
    "EST": "transition", "LVA": "transition", "LTU": "transition",

    # Özel vaka ülkeleri — Literatürde sıkça incelenen, uç değerler
    "JPN": "special_case",  # Ultra düşük fertility + aging society
    "KOR": "special_case",  # Dünyanın en düşük fertility'si (~0.7)
    "ITA": "special_case",  # Düşük doğurganlık + ekonomik kriz geçmişi
    "ESP": "special_case",  # Düşük doğurganlık + yüksek genç işsizlik
    "PRT": "special_case",  # Güney Avrupa krizi
    "GRC": "special_case",  # Ekonomik kriz etkisi
}

# ── Numeric columns used for analysis and modeling ──
# homeownership_rate removed: 53% missing, only 2010-2021 available
NUMERIC_COLS = [
    "fertility_rate", "inflation", "unemployment_total",
    "female_labor_force_participation", "marriage_rate", "gdp_per_capita",
    "income_share_top10", "wealth_share_top10", "income_wealth_ratio"
]


def add_labels(df):
    """Bölge, analiz grubu etiketlerini ekler."""
    df["region_tag"] = df["country_code"].map(REGION_TAG_MAP)
    df["country_group"] = df["country_code"].map(COUNTRY_GROUP_MAP)
    return df


def flag_outliers(df, cols=None, threshold=3.0):
    """
    Z-score bazlı outlier tespiti. Veriyi SİLMEZ, sadece işaretler.
    ML modelinde outlier'ları dahil edip etmemeye sonra karar verilir.

    Args:
        df: DataFrame
        cols: Kontrol edilecek sütunlar (default: NUMERIC_COLS)
        threshold: Z-score eşiği (default: 3.0)

    Yeni sütun: has_outlier (bool) — herhangi bir sütunda outlier varsa True
    """
    if cols is None:
        cols = NUMERIC_COLS

    outlier_mask = pd.DataFrame(False, index=df.index, columns=cols)

    for col in cols:
        if col not in df.columns:
            continue
        data = df[col]
        mean = data.mean()
        std = data.std()
        if std > 0:
            z_scores = ((data - mean) / std).abs()
            outlier_mask[col] = z_scores > threshold

    # Herhangi bir sütunda outlier varsa True
    df["has_outlier"] = outlier_mask.any(axis=1)

    n_outliers = df["has_outlier"].sum()
    print(f"  Outlier işaretlendi: {n_outliers} satır ({n_outliers/len(df)*100:.1f}%)")

    return df


def impute_marriage_rate(df):
    """
    marriage_rate eksik değerlerini ülke bazlı dağılım analizine göre doldurur.

    Karar kuralı:
      - |skewness| > 0.5 veya IQR bazlı outlier varsa → median
      - Aksi halde → mean

    Yeni sütun: marriage_rate_imputed
      - "mean"     → eksik veri mean ile dolduruldu
      - "median"   → eksik veri median ile dolduruldu
      - "original" → orijinal veri, dokunulmadı
    """
    df["marriage_rate_imputed"] = "original"

    n_mean = 0
    n_median = 0

    for code in df["country_code"].unique():
        mask = df["country_code"] == code
        country_data = df.loc[mask, "marriage_rate"]
        missing_mask = mask & df["marriage_rate"].isna()

        if missing_mask.sum() == 0:
            continue

        valid = country_data.dropna()

        if len(valid) < 3:
            # Yetersiz veri — median kullan
            fill_value = valid.median()
            method = "median"
        else:
            skew = valid.skew()
            q1 = valid.quantile(0.25)
            q3 = valid.quantile(0.75)
            iqr = q3 - q1
            n_outliers = ((valid < q1 - 1.5 * iqr) | (valid > q3 + 1.5 * iqr)).sum()

            if abs(skew) > 0.5 or n_outliers > 0:
                fill_value = valid.median()
                method = "median"
            else:
                fill_value = valid.mean()
                method = "mean"

        # Doldur ve işaretle
        df.loc[missing_mask, "marriage_rate"] = round(fill_value, 3)
        df.loc[missing_mask, "marriage_rate_imputed"] = method

        if method == "mean":
            n_mean += missing_mask.sum()
        else:
            n_median += missing_mask.sum()

        print(f"    {code}: {missing_mask.sum()} eksik → {method} ({fill_value:.3f})")

    print(f"  Toplam: {n_mean} satır mean, {n_median} satır median ile dolduruldu")

    return df


def report_missing(df):
    """Eksik veri raporunu yazdırır."""
    print("\n=== EKSİK VERİ RAPORU ===")
    total = len(df)

    for col in NUMERIC_COLS:
        if col not in df.columns:
            continue
        n_miss = df[col].isna().sum()
        pct = n_miss / total * 100
        if n_miss > 0:
            # Hangi ülkelerde eksik olduğunu göster
            miss_countries = df[df[col].isna()]["country_code"].unique()
            print(f"  {col}: {n_miss} eksik ({pct:.1f}%) — {len(miss_countries)} ülke")
        else:
            print(f"  {col}: ✓ Tam")

    print(f"\n  Toplam satır: {total}")
    print(f"  Tamamen dolu satır: {df.dropna(subset=NUMERIC_COLS).shape[0]}")


def report_groups(df):
    """Grup dağılımlarını yazdırır."""
    print("\n=== GRUP DAĞILIMLARI ===")

    print("\nBölge (region_tag):")
    for region, count in df["region_tag"].value_counts().items():
        n_countries = df[df["region_tag"] == region]["country_code"].nunique()
        print(f"  {region:<20s}  {count:>4d} satır  ({n_countries} ülke)")

    print("\nAnaliz Grubu (country_group):")
    for group, count in df["country_group"].value_counts().items():
        n_countries = df[df["country_group"] == group]["country_code"].nunique()
        countries = sorted(df[df["country_group"] == group]["country_code"].unique())
        print(f"  {group:<14s}  {count:>4d} satır  ({n_countries} ülke): {', '.join(countries)}")

    print("\nGelir Düzeyi (income_level):")
    for level, count in df["income_level"].value_counts().items():
        print(f"  {level:<22s}  {count:>4d} satır")


def report_inequality_quality(df):
    """WID eşitsizlik değişkenlerinin kapsama kalitesini raporlar."""
    vars_ineq = ["income_share_top10", "wealth_share_top10", "income_wealth_ratio"]
    print("\n=== EŞİTSİZLİK VERİ KALİTESİ ===")

    for col in vars_ineq:
        if col not in df.columns:
            print(f"  {col}: bulunamadı")
            continue

        valid = df[col].notna().sum()
        pct = valid / len(df) * 100 if len(df) else 0
        print(f"  {col:<22s} {valid:>4d}/{len(df)} satır ({pct:.1f}%)")

    for col in vars_ineq:
        if col in df.columns:
            by_country = df.groupby("country_code")[col].apply(lambda s: s.notna().sum())
            low_cov = (by_country < 15).sum()
            print(f"  {col:<22s} düşük kapsama (<15 yıl) ülke sayısı: {low_cov}")


def main():
    """
    Ana veri temizleme pipeline'ı:
    1. final_panel.csv yükle
    2. 2000+ filtrele
    3. OECD ülkelerini seç
    4. Etiketleri ekle (region_tag, country_group)
    5. Outlier tespiti
    6. Rapor yazdır ve kaydet
    """
    print("=" * 60)
    print("VERİ TEMİZLEME BAŞLADI")
    print("=" * 60)

    # Adım 1: Ham veriyi yükle
    df = pd.read_csv("data/processed/final_panel.csv")
    print(f"\n1. Ham veri yüklendi: {df.shape[0]} satır, {df.shape[1]} sütun")

    # Adım 2: 2000-2024 yıl aralığı
    # - 2000 öncesi: veri kalitesi düşük
    # - 2025: fertility_rate ve inflation henüz yayınlanmadı
    df = df[(df["year"] >= 2000) & (df["year"] <= 2024)]
    df.to_csv("data/processed/final_panel_filtered.csv", index=False)
    print(f"2. Yıl filtresi (2000-2024): {df.shape[0]} satır kaldı")

    # Adım 3: Sadece OECD ülkeleri — homojen ve veri kalitesi yüksek grup
    df_oecd = df[df["country_code"].isin(OECD_COUNTRIES)].copy()
    print(f"3. OECD filtresi: {df_oecd.shape[0]} satır, {df_oecd['country_code'].nunique()} ülke")

    # Adım 4: homeownership_rate sütununu kaldır (%53 eksik, analizi bozar)
    if "homeownership_rate" in df_oecd.columns:
        df_oecd = df_oecd.drop(columns=["homeownership_rate"])
        print("4. homeownership_rate kaldırıldı (%53 eksik veri)")

    # Adım 5: Kategorik etiketler
    df_oecd = add_labels(df_oecd)
    print("5. Etiketler eklendi: region_tag, country_group")

    # Adım 6: marriage_rate eksik değerlerini doldur (ülke bazlı mean/median)
    print("6. marriage_rate imputation:")
    df_oecd = impute_marriage_rate(df_oecd)

    # Adım 7: Outlier tespiti (silmiyoruz, sadece işaretliyoruz)
    print("7. Outlier tespiti (z-score > 3):")
    df_oecd = flag_outliers(df_oecd)

    # Adım 8: Sırala ve kaydet
    df_oecd = df_oecd.sort_values(["country_code", "year"]).reset_index(drop=True)
    df_oecd.to_csv("data/processed/final_oecd.csv", index=False)
    print(f"\n8. Kaydedildi: data/processed/final_oecd.csv")
    print(f"   → {df_oecd.shape[0]} satır, {df_oecd.shape[1]} sütun")
    print(f"   → Sütunlar: {df_oecd.columns.tolist()}")

    # Raporlar
    report_missing(df_oecd)
    report_inequality_quality(df_oecd)
    report_groups(df_oecd)

    print("\n" + "=" * 60)
    print("VERİ TEMİZLEME TAMAMLANDI")
    print("=" * 60)


if __name__ == "__main__":
    main()