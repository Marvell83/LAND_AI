# LAND RADAR data setup

## 1. GHSL built-up history

LAND RADAR currently supports local GeoTIFF analysis of:

- GHS-BUILT-S R2023A
- epochs 2010, 2015, 2020
- source CRS may be WGS84 or Mollweide; the engine transforms the WGS84 pilot bbox automatically.

Official dataset page:

https://human-settlement.emergency.copernicus.eu/ghs_buS2023.php

Download page:

https://human-settlement.emergency.copernicus.eu/download.php?ds=bu

Extract the official GeoTIFF files under:

```
data/raw/ghsl/
```

LAND RADAR discovers the epoch from filenames containing `_E2010_`, `_E2015_`, or `_E2020_`.

### Important interpretation rule

GHS-BUILT-S R2023A time slices are a harmonized multi-temporal product and include spatial-temporal interpolation/extrapolation. They are used as a **structural historical baseline**, not treated as literal annual observations. Recent physical change must be confirmed with Sentinel imagery.

## 2. Copernicus Sentinel-2 catalogue

No OAuth secret is required for the current CDSE STAC discovery probe.

Current STAC endpoint:

```
https://stac.dataspace.copernicus.eu/v1/
```

LAND RADAR searches the collection:

```
sentinel-2-l2a
```

The probe currently measures scene availability and cloud cover only. It does not yet convert Sentinel pixels into a development score.

## 3. Copernicus DEM

LAND RADAR uses the Sentinel Hub Process API and defaults to:

```
COPERNICUS_90
```

The 30 m instance requires additional CCM eligibility in current CDSE access rules, so it is not the default.

Create an OAuth client in the Copernicus Sentinel Hub dashboard, then use either environment variables:

```
CDSE_CLIENT_ID=...
CDSE_CLIENT_SECRET=...
```

or create a local file:

```
.streamlit/secrets.toml
```

with:

```toml
CDSE_CLIENT_ID = "..."
CDSE_CLIENT_SECRET = "..."
```

Never commit the real secret. The repository ignores `.streamlit/secrets.toml`.

## 4. OpenStreetMap

The current access probe queries OpenStreetMap through Overpass.

It is intentionally a **single-cell research probe**, not a bulk nationwide scraper. Bulk road-network processing will later use cached/local extracts to avoid abusing public Overpass infrastructure.

## 5. Price data

No reliable price provider is integrated yet.

Therefore:

**LAND RADAR must not calculate Mispricing for a real location until the price-data layer is resolved.**
