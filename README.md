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

## v0.4

Mevcut sürüm bir **çok-kaynaklı araştırma çekirdeğidir**:

- Streamlit arayüzü
- Sakarya–Çanakkale pilot grid üretimi
- OpenStreetMap / Overpass tek-hücre yol probe
- Copernicus STAC üzerinden Sentinel-2 L2A sahne keşfi
- GHSL GHS-BUILT-S yerel GeoTIFF analizi
- 2010→2015 ve 2015→2020 built-up büyüme / acceleration motoru
- kontrollü GHSL batch grid taraması
- Copernicus DEM GLO-90 OAuth/Process API adaptörü
- yükseklik ve eğim istatistikleri
- kanıt/evidence veri modeli
- point-in-time backtest güvenlik altyapısı
- hard-risk veto mantığı
- veri kaynağı kayıt defteri
- GitHub Actions otomatik testleri

**Henüz gerçek fiyat motoru yoktur. Bu nedenle gerçek lokasyonlar için Mispricing üretilmez.**

## Kurulum

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
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
5. Sentinel piksel değişim motoru
6. OSB/yol/demiryolu resmî katalizör veritabanı
7. Hard-risk coğrafi katmanları
8. Point-in-time fiyat verisi ve Mispricing
9. Backtest ve ağırlık kalibrasyonu
10. 100 → 30 → 10 → parsel elemesi

## Güvenilirlik kuralı

**Kaynak yoksa katalizör yoktur. Geçmiş veri yoksa ivme yoktur. Fiyat verisi yoksa mispricing yoktur. Kanıt yoksa AI yorum yapmaz.**

Bu yazılım yatırım tavsiyesi vermez; araştırma adaylarını ve bunların lehine/aleyhine kanıtları düzenler.


## Veri kurulumu

GHSL ve Copernicus veri kurulumu için [docs/DATA_SETUP.md](docs/DATA_SETUP.md) dosyasına bak.
