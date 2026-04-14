# DSA 210 - Doğurganlık Oranı Analiz Projesi

## Proje Özeti

OECD ve diğer büyük ülkelerde **doğurganlık oranını** etkileyen ekonomik ve sosyal faktörleri analiz eden bir veri bilimi projesi. Uzun vadede bulgular **interaktif bir web sitesine** dönüştürülecek.

**Bağımlı değişken:** `fertility_rate` (doğurganlık oranı)
**Bağımsız değişkenler:** enflasyon, işsizlik, genç kadın işsizliği, evlilik oranı, GDP per capita
**Kategorik etiketler:** bölgesel tag, ekonomik düzey tag'i

---

## Mevcut Veri Durumu

| Değişken | Kaynak | Durum |
|---|---|---|
| `fertility_rate` | World Bank API (`SP.DYN.TFRT.IN`) | ✅ Mevcut |
| `inflation` | World Bank API (`FP.CPI.TOTL.ZG`) | ✅ Mevcut |
| `unemployment_total` | World Bank API (`SL.UEM.TOTL.ZS`) | ✅ Mevcut |
| `female_youth_unemployment_15_24` | World Bank API (`SL.UEM.1524.FE.ZS`) | ✅ Mevcut |
| `marriage_rate` | OECD Family Database (SF3.1) | ✅ Mevcut (973 satır, programatik indirme) |
| `gdp_per_capita` | World Bank API (`NY.GDP.PCAP.PP.CD`) | ✅ Mevcut (PPP, current international $) |
| `homeownership_rate` | OECD Affordable Housing Database (HM1.3) | ❌ Kapsam dışı bırakıldı (%53 eksik veri) |
| `region_tag` | Manuel mapping (`data_cleaning.py`) | ✅ Mevcut (9 bölge) |
| `income_level` | World Bank API (`incomeLevel.value`) | ✅ Mevcut (High income / Upper middle income) |

**Mevcut kapsam:** 34 OECD ülkesi, 2000-2024, 850 satır, 14 sütun, **%100 dolu**
**Dosya:** `data/processed/final_oecd.csv`
**Sütunlar:** `country, country_code, year, fertility_rate, inflation, unemployment_total, female_youth_unemployment_15_24, gdp_per_capita, marriage_rate, income_level, region_tag, country_group, marriage_rate_imputed, has_outlier`

**Analiz Grupları (country_group):**
| Grup | Ülke Sayısı | Ülkeler | Açıklama |
|---|---|---|---|
| `developed` | 16 | USA, CAN, GBR, DEU, FRA, NLD, BEL, CHE, AUT, IRL, SWE, NOR, DNK, FIN, AUS, NZL | Benchmark grup: homojen, veri kaliteli |
| `transition` | 12 | MEX, COL, TUR, CHL, POL, CZE, HUN, SVK, SVN, EST, LVA, LTU | Geçiş ülkeleri: farklı dinamikler |
| `special_case` | 6 | JPN, KOR, ITA, ESP, PRT, GRC | Literatürde özel incelenen uç vakalar |

---

## Eksik Verilerin Kaynakları

### 1. Evlilik Oranı (marriage_rate)

**Kaynak:** OECD Family Database - SF3.1 Marriage and Divorce Rates
- **PDF raporu:** https://webfs.oecd.org/els-com/Family_Database/SF_3_1_Marriage_and_divorce_rates.pdf
- **Indirme sayfası:** https://www.oecd.org/en/data/datasets/oecd-family-database.html
  - "Structure of Families" bölümü altında **SF3.1** satırındaki **XLSx** butonundan indirilir
- **Veri formatı:** Crude marriage rate (1.000 kişi başına evlenme sayısı), ülke x yıl
- **Beklenen dosya yolu:** `data/raw/oecd_marriage_rate.csv`
- **Beklenen sütunlar:** `country, country_code, year, marriage_rate`
- **Not:** `data_collection.py` içinde `load_oecd_marriage_csv()` fonksiyonu zaten bu dosyayı bekliyor. Indirilen Excel dosyası düzenlenerek bu formata getirilmeli.

### 2. Konut Sahipliği Oranı (homeownership_rate)

**Kaynak:** OECD Affordable Housing Database - HM1.3 Housing Tenures
- **PDF raporu:** https://www.oecd.org/content/dam/oecd/en/data/datasets/affordable-housing-database/hm1-3-housing-tenures.pdf
- **Doğrudan XLSX indirme:** https://webfs.oecd.org/els-com/Affordable_Housing_Database/ dizininden `HM1-3-Housing-tenures.xlsx` dosyası
- **Indirme sayfası:** https://www.oecd.org/en/data/datasets/oecd-affordable-housing-database.html
  - "Housing Market" bölümünde **HM1.3** satırındaki **XLSx** butonundan indirilir
- **Veri formatı:** Homeownership rate (%), ülke x yıl
- **Beklenen dosya yolu:** `data/raw/oecd_homeownership.xlsx` veya `data/raw/oecd_homeownership.csv`
- **Beklenen sütunlar:** `country, country_code, year, homeownership_rate`
- **Not:** `data_collection.py` içinde `load_oecd_homeownership_xlsx()` fonksiyonu zaten bu dosyayı bekliyor. OECD Excel formatı karmaşık olabiliyor; sheet ve sütun adları incelenerek standart formata dönüştürülmeli.

### 3. Bölgesel Etiket (region_tag)

**Kaynak:** World Bank API + manuel düzenleme
- **API endpoint:** `https://api.worldbank.org/v2/country?format=json&per_page=400`
  - Her ülke kaydında `region.value` alanı mevcut (örn: "Europe & Central Asia", "East Asia & Pacific")
- **Not:** World Bank bölgeleri geniş kapsamlı. Kullanıcının istediği daha spesifik etiketler için manuel mapping gerekebilir:

| Tag | Örnek Ülkeler |
|---|---|
| `North America` | USA, CAN, MEX |
| `Western Europe` | DEU, FRA, GBR, NLD, BEL, CHE, AUT, IRL |
| `Southern Europe` | ITA, ESP, PRT, GRC |
| `Northern Europe` | SWE, NOR, DNK, FIN |
| `Eastern Europe` | POL, CZE, HUN, SVK, SVN, EST, LVA, LTU |
| `East Asia` | JPN, KOR |
| `Oceania` | AUS, NZL |
| `Latin America` | CHL, COL |
| `Middle East` | TUR (mevcut OECD listesinde tek Ortadoğu temsilcisi) |

- **Uygulanacak yer:** `data_cleaning.py` içinde mapping dict ile oluşturulabilir

### 4. Ekonomik Düzey Etiketi (income_level)

**Kaynak:** World Bank API
- **API endpoint:** `https://api.worldbank.org/v2/country?format=json&per_page=400`
  - Her ülke kaydında `incomeLevel.value` alanı mevcut
  - Değerler: `High income`, `Upper middle income`, `Lower middle income`, `Low income`
- **Not:** `get_real_country_codes()` fonksiyonu zaten bu endpoint'i çağırıyor. `incomeLevel` bilgisi de aynı anda çekilebilir - fonksiyon genişletilmeli.
- OECD ülkelerinin çoğu `High income` kategorisinde. MEX, COL, TUR gibi ülkeler `Upper middle income` olabilir.

---

## Proje Aşamaları ve Yapılacaklar

### ASAMA 1: Veri Zenginleştirme ✅
- [x] **1.1** OECD Family Database'den evlilik oranı verisini indir ve `data/raw/oecd_marriage_rate.csv` olarak kaydet
- [x] **1.2** OECD Affordable Housing Database'den konut sahipliği verisini indir ve `data/raw/oecd_homeownership.csv` olarak kaydet
- [x] **1.3** Indirilen dosyaları beklenen formata dönüştür (`prepare_oecd_marriage_data()` ve `prepare_oecd_homeownership_data()` fonksiyonları)
- [x] **1.4** `data_collection.py` - `get_real_country_codes()` genişletildi: `income_level` ve `wb_region` bilgilerini de çekiyor
- [x] **1.5** `data_cleaning.py` - `REGION_TAG_MAP` dict ile 9 bölgesel tag eklendi
- [x] **1.6** `data_collection.py` çalıştırıldı, `final_panel.csv` güncellendi (14392 satır, 10 sütun)
- [x] **1.7** `data_cleaning.py` çalıştırıldı, `final_oecd.csv` güncellendi (950 satır, 11 sütun)

### ASAMA 2: Keşifsel Veri Analizi (EDA) ✅
- [x] **2.1** `notebooks/analysis.ipynb` içinde kapsamlı EDA yapıldı (23 hücre)
- [x] **2.2** Temel istatistikler: shape, describe, missing values, dtypes
- [x] **2.3** Missing value analizi: heatmap, ülke/yıl bazlı eksik veri oranları
- [x] **2.4** Dağılım grafikleri: her değişken için histogram + boxplot
- [x] **2.5** Zaman serisi grafikleri: bölge bazlı doğurganlık trendi + ülke bazlı facet grid
- [x] **2.6** Korelasyon matrisi (Pearson heatmap)
- [x] **2.7** Scatter plotlar: fertility_rate vs her bağımsız değişken (bölge renkli + trend çizgisi)
- [x] **2.8** Ülke/bölge bazlı karşılaştırma bar grafikleri + boxplotlar
- [x] **2.9** income_level bazlı gruplandırılmış analizler (trend + ortalama tabloları)
- [x] **2.10** Grafikleri `outputs/` klasörüne kaydet (savefig her grafik için mevcut)
- **Not:** Notebook'u çalıştırmak için: Jupyter'da aç ve "Run All" yap

### ASAMA 3: İstatistiksel Analiz & Hipotez Testleri ❌
- [ ] **3.1** Pearson & Spearman korelasyon testleri (p-value'larıyla)
- [ ] **3.2** Hipotez: "Enflasyon arttıkça doğurganlık düşer mi?"
- [ ] **3.3** Hipotez: "İşsizlik arttıkça doğurganlık düşer mi?"
- [ ] **3.4** Hipotez: "Evlilik oranı ile doğurganlık arasında pozitif ilişki var mı?"
- [ ] **3.5** Bölgeler arası ANOVA / Kruskal-Wallis testi
- [ ] **3.6** Gelir düzeyleri arası karşılaştırma testleri

### ASAMA 4: Modelleme ❌
- [ ] **4.1** Basit doğrusal regresyon (OLS) - her bağımsız değişken için ayrı ayrı
- [ ] **4.2** Çoklu doğrusal regresyon - tüm değişkenlerle
- [ ] **4.3** Multicollinearity kontrolü (VIF)
- [ ] **4.4** Model performans metrikleri: R2, Adjusted R2, RMSE, MAE
- [ ] **4.5** Residual analizi
- [ ] **4.6** (Opsiyonel) Panel regresyon veya Fixed Effects modeli (statsmodels)
- [ ] **4.7** (Opsiyonel) Random Forest / Gradient Boosting karşılaştırması

### ASAMA 5: Interaktif Web Sitesi (Uzun Vade) ❌
- [ ] **5.1** Teknoloji seçimi (React + D3.js / Plotly Dash / Streamlit vb.)
- [ ] **5.2** Ana sayfa: genel doğurganlık trendi haritası
- [ ] **5.3** Ülke bazlı detay sayfası: tüm değişkenler zaman serisi olarak
- [ ] **5.4** Karşılaştırma aracı: iki ülke/bölge yan yana
- [ ] **5.5** Korelasyon keşif aracı: interaktif scatter plot
- [ ] **5.6** Filtreleme: bölge, gelir düzeyi, yıl aralığı
- [ ] **5.7** Deploy (Netlify / Vercel / GitHub Pages)

### ASAMA 6: Dokümantasyon ❌
- [ ] **6.1** README.md oluştur (proje açıklaması, kurulum, kullanım)
- [ ] **6.2** Bulguları özetleyen sonuç bölümü
- [ ] **6.3** Kaynakça

---

## Dosya Yapısı

```
dsa 210-project/
├── AGENTS.md              <- Bu dosya (proje planı & bağlam)
├── README.md              <- Proje açıklaması (henüz yok)
├── data/
│   ├── raw/               <- Ham veriler (API'den veya manuel indirilen)
│   │   ├── fertility_rate.csv
│   │   ├── oecd_marriage_rate.csv      <- ✅ Eklendi (programatik)
│   │   ├── oecd_marriage_raw.xlsx      <- OECD'den indirilen ham Excel
│   │   ├── oecd_homeownership.csv      <- ✅ Eklendi (programatik)
│   │   └── oecd_homeownership_raw.xlsx <- OECD'den indirilen ham Excel
│   └── processed/         <- Temizlenmiş & birleştirilmiş veriler
│       ├── final_panel.csv
│       ├── final_panel_filtered.csv
│       ├── final_oecd.csv              <- Ana analiz dosyası
│       ├── fertility_rate.csv
│       └── gdp_per_capita.csv
├── notebooks/
│   └── analysis.ipynb     <- Ana analiz notebook'u
├── outputs/               <- Grafik ve model çıktıları
└── src/
    ├── data_collection.py <- World Bank API + OECD veri yükleme
    ├── data_cleaning.py   <- Filtreleme, OECD subset, tag ekleme
    └── eda.py             <- Basit EDA (konsol çıktısı)
```

---

## Teknik Notlar

- **Python sürümü:** 3.x
- **Ana kütüphaneler:** pandas, matplotlib, seaborn, scipy, scikit-learn, statsmodels
- **Veri API:** World Bank API v2 (`https://api.worldbank.org/v2/`)
- **OECD verileri:** Programatik indirme yapılıyor (`prepare_oecd_marriage_data()` ve `prepare_oecd_homeownership_data()`)
- `data_collection.py` -> `get_real_country_codes()` artık `income_level` ve `wb_region` bilgilerini de döndürüyor (tuple: `real_codes, country_metadata`)
- `data_collection.py` -> `COUNTRY_NAME_TO_ISO3` dict ile OECD ülke adları ISO3 kodlara çevriliyor
- `data_cleaning.py` -> `REGION_TAG_MAP` dict ile 9 bölgesel etiket atanıyor
- `data_cleaning.py` -> `COUNTRY_GROUP_MAP` dict ile 3 analiz grubu (developed, transition, special_case)
- `data_cleaning.py` -> `flag_outliers()` z-score > 3 olan satırları `has_outlier=True` olarak işaretliyor
- `data_cleaning.py` -> `main()` fonksiyonu olarak refactor edildi (`if __name__ == "__main__"` ile)
- Tüm Python dosyalarına detaylı docstring ve commentler eklendi