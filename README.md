# LAND RADAR / Arsa Cerrahı

LAND RADAR, Türkiye'de arazi ve arsa fırsatlarını **bölge → mikro bölge → parsel** akışıyla incelemeyi hedefleyen jeo-uzamsal yatırım araştırma projesidir.

## Temel prensip

Amaç "ucuz arsa bulmak" değildir. Amaç:

> Fiziksel dönüşüm, şehirleşme ivmesi ve resmî katalizörler güçlenirken fiyatın bunu ne ölçüde yansıttığını; hukuki/fiziksel riskleri ve bekleme maliyetini ayrı ayrı ölçmek.

Bu nedenle sistem tek bir sihirli puana dayanmaz. Ana bileşenler ayrı gösterilir:

- Urban Pressure
- Development Acceleration
- Catalyst Maturity
- Story Maturity
- Physical Quality
- Mispricing
- Exit Demand
- Risk / hard veto
- Data Confidence
- Evidence trail

## İlk pilot

İlk araştırma evreni Sakarya → Bursa/Balıkesir → Çanakkale koridorudur. İlk aşamada parsel bazına inmeden grid/hücre seviyesinde tarama yapılacaktır.

## v0.11

Mevcut sürüm bir **çok-kaynaklı mekânsal araştırma çekirdeğidir**:

- Streamlit arayüzü
- Sakarya–Çanakkale pilot grid üretimi
- OpenStreetMap / Overpass yol probe
- OSM industrial + railway geometry evidence provider
- hücre → katalizör gerçek minimum mesafe motoru
- yerel azimuthal-equidistant projeksiyonla metre/km hesaplama
- configurable spatial influence bands
- statü kanıtı ile geometri kanıtını ayrı tutan Catalyst Spatial Link
- GeoJSON Geometry Registry + batch cell linking
- OSBÜK resmî OSB durum akışı
- AYGM/UAB resmî demiryolu proje durum akışı
- OSBÜK statüsü + OSM geometri adı için kontrollü aday eşleştirme
- Copernicus STAC üzerinden Sentinel-2 L2A sahne keşfi
- GHSL GHS-BUILT-S yerel GeoTIFF analizi
- 2010→2015 ve 2015→2020 built-up büyüme / acceleration motoru
- kontrollü GHSL batch grid taraması
- Copernicus DEM GLO-90 OAuth/Process API adaptörü
- yükseklik ve eğim istatistikleri
- Sentinel-2 iki dönem NDVI/NDBI/BSI + SCL yüzey değişim motoru
- kanıt zorunlu 0→6 Catalyst State Machine
- pilot grid ve GHSL aday haritaları
- GHSL batch sonuçlarını CSV dışa aktarma
- robust emsal fiyat laboratuvarı (CSV)
- isteğe bağlı CPI/TÜFE ile reel fiyat düzeltmesi
- evidence-backed risk finding / explicit hard-veto modeli
- GeoJSON Hazard Registry + hücre kesişim/overlap/distance motoru
- Copernicus DEM cached batch terrain scan
- şeffaf Candidate Funnel: geniş GHSL havuzu → finalist → DEM/risk/katalizör
- PASS / PASS_WITH_GAPS / DROP gerekçeli eleme
- güvenli GHSL ZIP installer + CRS/dtype/epoch doğrulaması
- GHSL çoklu-tile güvenli toplama
- Data Readiness Checker
- ilk gerçek 500 → 100 GHSL scan exporter (CSV + GeoJSON + JSON özet)
- transparent 100 → 30 deep scan (DEM + hazard + catalyst geometry)
- eksik hazard katmanını açıkça `hazard_unknown` olarak işaretleme
- Windows GHSL kurulum, ilk tarama ve derin tarama başlatıcıları
- Windows tek-tık başlatıcı ve güvenli secrets örneği
- kanıt/evidence veri modeli
- point-in-time backtest güvenlik altyapısı
- GitHub Actions compile + test kontrolü

**Otomatik, güvenilir işlem-fiyatı veri hattı henüz yoktur. Bu nedenle gerçek lokasyonlar için kalibre edilmiş Mispricing Score üretilmez.**

## Kurulum

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

Windows'ta alternatif olarak:

```
LAND_RADAR_BASLAT.bat
```

Test:

```bash
pytest -q
```

## Yol haritası

1. Pilot grid ✅
2. GHSL geçmiş yapılaşma motoru ✅
3. Sentinel-2 STAC keşfi ✅
4. DEM/eğim motoru ✅
5. Sentinel piksel değişim motoru ✅
6. Catalyst State Machine ✅
7. OSBÜK + AYGM durum akışları ✅
8. Emsal fiyat + CPI/reel fiyat laboratuvarı ✅
9. Evidence-backed risk modeli ✅
10. Spatial Intelligence / catalyst geometry engine ✅
11. Geometry Registry + batch cell linking ✅
12. Hazard Registry + overlap/hard-veto engine ✅
13. Cached DEM batch terrain scan ✅
14. Transparent Candidate Funnel ✅
15. GHSL installer + readiness + first real 500→100 scan workflow ✅
16. Transparent 100→30 deep scan workflow ✅
17. OSB/demiryolu resmî güzergâh geometrisi / doğrulanmış geometry kaynakları
18. KGM stratejik karayolu proje akışı
19. AFAD/USBS/TUCBS doğrulanmış doğrudan servis entegrasyonları
20. Otomatik point-in-time fiyat veri hattı ve Mispricing kalibrasyonu
21. Backtest ve ağırlık kalibrasyonu
22. 30 → 10 → parsel elemesi

## Güvenilirlik kuralı

**Kaynak yoksa katalizör yoktur. Geçmiş veri yoksa ivme yoktur. Fiyat verisi yoksa mispricing yoktur. Kanıt yoksa AI yorum yapmaz.**

Ek spatial kural:

**Katalizör statüsü ile katalizör geometrisi aynı şey değildir.** Örneğin OSB statüsü OSBÜK'ten, sınır/geometri OSM'den geliyorsa iki kaynak ve iki güven seviyesi ayrı tutulur.

Bu yazılım yatırım tavsiyesi vermez; araştırma adaylarını ve bunların lehine/aleyhine kanıtları düzenler.

## İlk gerçek tarama

Resmî GHSL 2010 / 2015 / 2020 R2023A 100 m ZIP dosyalarını indirdikten sonra Windows'ta:

```
GHSL_ZIP_KUR.bat "C:\\...\\official-ghsl.zip"
```

Tüm zorunlu epoch'lar hazır olduğunda:

```
ILK_GERCEK_TARAMA.bat
```

Python karşılıkları:

```bash
python scripts/check_readiness.py
python scripts/first_real_scan.py --cell-km 5 --pool 500 --top 100
```

İlk scan çıktıları:

```
data/output/first_scan/ghsl_top_candidates.csv
data/output/first_scan/ghsl_top_candidates.geojson
data/output/first_scan/ghsl_scan_summary.json
```

Bu liste yalnız tarihsel GHSL built-up ivme shortlist'idir; yatırım sıralaması değildir.

Detay: [docs/FIRST_REAL_SCAN.md](docs/FIRST_REAL_SCAN.md)

İlk 100 aday çıktıktan sonra:

```
DERIN_TARAMA_100_30.bat
```

veya:

```bash
python scripts/deep_scan.py --top 30
```

Bu aşama mevcut DEM, hazard ve catalyst geometry kanıtlarını ekler; eksik katmanları gizlemek yerine veri açığı olarak gösterir.

Detay: [docs/DEEP_SCAN_100_30.md](docs/DEEP_SCAN_100_30.md)

## Veri kurulumu

GHSL ve Copernicus veri kurulumu için [docs/DATA_SETUP.md](docs/DATA_SETUP.md), fiyat metodolojisi için [docs/PRICE_MODEL.md](docs/PRICE_MODEL.md), spatial mimari için [docs/SPATIAL_INTELLIGENCE.md](docs/SPATIAL_INTELLIGENCE.md), risk veri stratejisi için [docs/RISK_DATA.md](docs/RISK_DATA.md) dosyasına bak.
