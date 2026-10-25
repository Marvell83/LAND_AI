# LAND RADAR — first real 500 → 100 scan

## Goal

The first real scan is deliberately narrow:

```
Sakarya → Bursa/Balıkesir → Çanakkale pilot envelope
                  ↓
              5 km grid
                  ↓
        first 500 research cells
                  ↓
  GHSL 2010 / 2015 / 2020 built-up history
                  ↓
measurable historical development acceleration
                  ↓
             top 100 cells
```

This is **not** the final opportunity ranking.

It answers only:

> Which scanned cells show the strongest measurable change in historical built-up growth rate?

Terrain, hazards, catalysts, prices and liquidity are added after this shortlist.

## 1. Obtain official GHSL data

Use the official GHSL GHS-BUILT-S R2023A download page:

https://human-settlement.emergency.copernicus.eu/download.php?ds=bu

Required product:

```
GHS-BUILT-S_GLOBE_R2023A
World Mollweide / ESRI:54009
100 m
```

Required epochs:

```
2010
2015
2020
```

The official product page confirms that 100 m GHS-BUILT-S values are square metres of built-up surface in each grid cell.

Do not substitute:

- GHS-BUILT-V,
- NRES-only built surface,
- 1 km data,
- obsolete R2022A data,

for this first benchmark.

## 2. Install downloaded ZIP files

Windows:

Drag each official ZIP onto:

```
GHSL_ZIP_KUR.bat
```

or:

```cmd
GHSL_ZIP_KUR.bat "C:\Users\YOU\Downloads\official-ghsl.zip"
```

Python:

```bash
python scripts/install_ghsl.py --zip /path/to/official-ghsl.zip
```

The installer:

- extracts only GHS-BUILT-S R2023A / Mollweide / 100 m GeoTIFFs,
- accepts only requested epochs,
- validates CRS, raster band count and dtype,
- safely handles nested ZIP paths,
- keeps multiple tiles for the same epoch.

If the official site exposes a direct ZIP URL, it can also be supplied with:

```bash
python scripts/install_ghsl.py --url "https://...europa.eu/...zip"
```

The installer rejects non-EU download domains.

## 3. Verify readiness

```bash
python scripts/check_readiness.py
```

Required:

```
ghsl_2010  READY
ghsl_2015  READY
ghsl_2020  READY
```

The same report is visible in the first Streamlit tab.

## 4. Run the first scan

Windows:

```
ILK_GERCEK_TARAMA.bat
```

Python:

```bash
python scripts/first_real_scan.py --cell-km 5 --pool 500 --top 100
```

Outputs:

```
data/output/first_scan/ghsl_top_candidates.csv
data/output/first_scan/ghsl_top_candidates.geojson
data/output/first_scan/ghsl_scan_summary.json
```

## 5. What the columns mean

Important fields:

- `built_2010_m2`
- `built_2015_m2`
- `built_2020_m2`
- `cagr_2010_2015_pct`
- `cagr_2015_2020_pct`
- `acceleration_pp_per_year`
- `occupied_share_acceleration_pp`
- `signal`

`acceleration_pp_per_year` compares annualized built-up growth rates between the two five-year periods.

A high value means:

> built-up growth was faster in 2015–2020 than in 2010–2015.

It does **not** mean:

> buy land here.

## 6. Why the scan stops at 100

The top 100 become the expensive-analysis set.

Next layers:

1. cached Copernicus DEM slope,
2. official hazard registry,
3. catalyst geometry + status,
4. Sentinel recent-change confirmation,
5. price and real-price comparison.

Only then should the funnel move toward:

```
100 → 30 → 10 → parcel
```

## 7. Multi-tile safety

GHSL can be distributed as tiles.

LAND RADAR opens every matching tile for an epoch and uses only those that intersect each research cell.

This is critical for the Sakarya–Çanakkale envelope because a broad pilot can cross tile boundaries.

## 8. Point-in-time caution

This first scan is a present-day research scan.

For a historical backtest, the analysis must later freeze all evidence to the historical cutoff date. Current catalyst status, current road geometry or current price information must never leak into an older backtest.
