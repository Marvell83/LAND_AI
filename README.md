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

## v0.1

İlk sürüm bir **araştırma çekirdeğidir**:

- Streamlit arayüzü
- pilot grid üretimi
- kanıt/evidence veri modeli
- hard-risk veto mantığı
- bileşen bazlı araştırma öncelik skoru
- veri kaynağı kayıt defteri
- otomatik testler

Gerçek uydu, fiyat ve resmî katalizör verileri entegre edilmeden sistem bunları varmış gibi göstermez.

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

1. Pilot grid
2. GHSL geçmiş yapılaşma
3. Copernicus/Sentinel değişim teyidi
4. DEM/eğim ve fiziksel kalite
5. OSB/yol/demiryolu katalizörleri
6. Hard-risk katmanı
7. Point-in-time fiyat verisi ve Mispricing
8. Backtest
9. 100 → 30 → 10 → parsel elemesi

## Güvenilirlik kuralı

**Kaynak yoksa katalizör yoktur. Geçmiş veri yoksa ivme yoktur. Fiyat verisi yoksa mispricing yoktur. Kanıt yoksa AI yorum yapmaz.**

Bu yazılım yatırım tavsiyesi vermez; araştırma adaylarını ve bunların lehine/aleyhine kanıtları düzenler.
