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

## v0.18

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
- Top-30 için cached Sentinel-2 seasonal confirmation
- NDVI/NDBI/BSI/SCL değişimini ham kanıt olarak birleştiren `top30_with_sentinel.csv`
- hücre başına Candidate Evidence Packet
- Tarım ve Orman Bakanlığı KorunanAlanlarWFS doğrudan GeoJSON entegrasyonu
- USBS resmî taşkın risk katmanı doğrudan GeoJSON entegrasyonu
- Top-30 Official Constraints Scan
- protected-area + flood alt-kanıtlarının Evidence Packet entegrasyonu
- Top-30 hücre-bazlı emsal fiyat taraması
- MEDIUM/HIGH güven eşiğiyle `price_known`
- fiyat alt-kanıtının Evidence Packet entegrasyonu
- 30→10 Evidence Gate: eksik kritik kanıt varsa daraltmayı bloke eder
- e-Plan lifecycle / point-in-time Plan Evidence Registry
- resmî plan CSV importer
- Top-30 Planning Evidence Scan
- doğrulanmış TUCBS/ULASAV bölgesel ÇDP WMS registry
- FINALIZED + spatially verified UIP/NIP kuralıyla `planning_legal.known`
- planning kanıtının Evidence Packet ve Top-10 Gate entegrasyonu
- generic OGC WFS GeoJSON client
- configurable MTA/TUCBS heyelan envanter taraması
- USBS flood + MTA landslide core hazard coverage politikası
- AFAD duyarlılık katmanını erişim kısıtı nedeniyle ayrı/eksik tutma
- evidence coverage yalnız veri kapsamı olarak hesaplanır; yatırım puanı değildir
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
17. Sentinel Top-30 recent-change confirmation ✅
18. Candidate Evidence Packets ✅
19. Tarım ve Orman protected-area + USBS flood direct services ✅
20. Top-30 comparable-price evidence scan ✅
21. 30→10 Evidence Gate ✅
22. Planning Intelligence / e-Plan evidence registry ✅
23. MTA/TUCBS landslide inventory adapter ✅
24. OSB/demiryolu resmî güzergâh geometrisi / doğrulanmış geometry kaynakları
25. KGM stratejik karayolu proje akışı
26. e-Plan public interface için stabil otomatik vektör/veri adaptörü bulunursa doğrudan entegrasyon
27. AFAD erişilebilir duyarlılık / diğer resmî risk servisleri
28. Otomatik point-in-time fiyat veri hattı ve Mispricing kalibrasyonu
29. Backtest ve ağırlık kalibrasyonu
30. Gate sonrası evidence-based Top-10 review → parsel elemesi

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

Top-30 için Sentinel iki-dönem fiziksel değişim teyidi:

```
SENTINEL_TOP30.bat
```

veya:

```bash
python scripts/sentinel_confirm.py
```

Çıktı ham NDVI/NDBI/BSI/SCL değişimidir; otomatik yapılaşma etiketi değildir.

Detay: [docs/SENTINEL_TOP30.md](docs/SENTINEL_TOP30.md)

Top-30 için tek hücrelik kanıt paketleri:

```
KANIT_PAKETLERI.bat
```

veya:

```bash
python scripts/build_evidence_packets.py
```

Çıktılar tarihsel büyüme, terrain, hazard, catalyst ve varsa Sentinel kanıtını tek kayıtta birleştirir; planning/legal ve fiyat eksikse bunu açıkça gösterir.

Detay: [docs/EVIDENCE_PACKETS.md](docs/EVIDENCE_PACKETS.md)

Top-30 için resmî korunan alan ve USBS taşkın taraması:

```bash
bash OFFICIAL_KISITLAR_TOP30.sh
```

veya:

```bash
python scripts/official_constraints_scan.py
```

Ardından Evidence Packet'leri yeniden üret:

```bash
python scripts/build_evidence_packets.py
```

Korunan alan eşleşmesi otomatik hard-veto değildir; e-Plan ayrı kanıt kanalı olarak hâlâ eksiktir.

Detay: [docs/OFFICIAL_CONSTRAINTS.md](docs/OFFICIAL_CONSTRAINTS.md)

Top-30 için hücre-bazlı emsal fiyat kanıtı:

```bash
bash PRICE_TOP30.sh data/processed/comparables.csv
```

veya:

```bash
python scripts/candidate_price_scan.py --comparables data/processed/comparables.csv
```

Fiyat katmanı yalnız MEDIUM/HIGH emsal güveninde `known=true` olur.

Ardından Evidence Packet'leri yeniden üret:

```bash
python scripts/build_evidence_packets.py
```

Detay: [docs/TOP30_PRICE.md](docs/TOP30_PRICE.md)

Top-10 incelemesine geçmeden önce kanıt kapısını çalıştır:

```bash
bash TOP10_GATE.sh
```

veya:

```bash
python scripts/selection_gate.py --target 10
```

Eksik kritik kanıt varsa sistem Top-10 daraltmasını bilinçli olarak bloke eder; puan veya otomatik yatırım sıralaması üretmez.

Detay: [docs/SELECTION_GATE.md](docs/SELECTION_GATE.md)

Planning Intelligence:

```bash
bash PLAN_KANIT_TOP30.sh
```

Resmî e-Plan/belediye plan kaydını CSV'den registry'ye almak için:

```bash
python scripts/import_plan_evidence.py --csv data/processed/plans.csv
python scripts/planning_scan.py
python scripts/build_evidence_packets.py
bash TOP10_GATE.sh
```

`planning_legal.known` yalnız tarih-kesitinde geçerli, FINALIZED, spatially verified UIP/NIP kanıtıyla açılır. Bölgesel ÇDP WMS kapsamı tek başına imar hakkı sayılmaz.

Detay: [docs/PLANNING_INTELLIGENCE.md](docs/PLANNING_INTELLIGENCE.md)

MTA/TUCBS heyelan envanter WFS bilgisi doğrulandıktan sonra Top-30 taraması:

```bash
bash MTA_HEYELAN_TOP30.sh
```

Servis URL/typeName bilinmiyorsa LAND RADAR bunları tahmin etmez ve heyelan envanterini unchecked bırakır.

Detay: [docs/LANDSLIDE_INTELLIGENCE.md](docs/LANDSLIDE_INTELLIGENCE.md)

## Veri kurulumu

GHSL ve Copernicus veri kurulumu için [docs/DATA_SETUP.md](docs/DATA_SETUP.md), fiyat metodolojisi için [docs/PRICE_MODEL.md](docs/PRICE_MODEL.md), spatial mimari için [docs/SPATIAL_INTELLIGENCE.md](docs/SPATIAL_INTELLIGENCE.md), risk veri stratejisi için [docs/RISK_DATA.md](docs/RISK_DATA.md) dosyasına bak.
