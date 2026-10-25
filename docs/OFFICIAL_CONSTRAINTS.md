# LAND RADAR — Official protected-area and flood scan

## Sources

LAND RADAR v0.14 uses public ArcGIS REST services published by the
Republic of Türkiye Ministry of Agriculture and Forestry.

Protected-area service:

```
https://cbs1.tarimorman.gov.tr/server/rest/services/KorunanAlanlarWFS/MapServer
```

Queried feature layers:

- Milli Parklar
- Tabiat Parkları
- Tabiatı Koruma Alanları
- Tabiat Anıtları
- Ramsar sulak alanları
- Ulusal öneme haiz sulak alanlar
- Mahalli öneme haiz sulak alanlar
- Yaban hayatı geliştirme sahaları

USBS flood-risk layer:

```
https://cbs1.tarimorman.gov.tr/server/rest/services/SYGM_USBS/SYGM_USBS/MapServer/5
```

Both services advertise GeoJSON query support.

## Run in Codespaces

```bash
bash OFFICIAL_KISITLAR_TOP30.sh
```

or:

```bash
python scripts/official_constraints_scan.py
```

The command reads:

```
data/output/deep_scan/deep_scan_top30.csv
```

and queries one bounding envelope around the Top-30 candidate cells.

## Protected areas

A protected-area intersection is recorded as:

```
LegalEffect.REVIEW_REQUIRED
```

It is **not** automatically treated as a hard veto.

Why?

A grid-cell overlap is not equivalent to a parcel-level legal conclusion.
The exact parcel, plan note, protection regime, boundary precision and current
legislation still require review.

LAND RADAR therefore stores:

- official source,
- category,
- geometry,
- cell overlap,
- minimum distance,
- legal-review flag,
- evidence confidence.

## Flood risk

The USBS layer exposes fields including:

- `KATEGORI`
- `RISK50`
- `RISK100`
- `RISK500`
- enum variants of those fields.

LAND RADAR only maps clearly readable text categories:

- Düşük → LOW
- Orta → MEDIUM
- Yüksek → HIGH
- Çok Yüksek → CRITICAL

If the category cannot be interpreted:

```
UNKNOWN
```

It is never guessed from an undocumented enum scale.

A flood polygon is not automatically a hard veto either.

## Outputs

```
data/output/official_constraints/protected_area_top30.csv
data/output/official_constraints/flood_risk_top30.csv
data/output/official_constraints/protected_area_features.geojson
data/output/official_constraints/flood_risk_features.geojson
data/output/official_constraints/official_constraints_summary.json
```

## Evidence Packet integration

After the official scan:

```bash
python scripts/build_evidence_packets.py
```

Candidate packets gain:

```
planning_legal.protected_area
hazard.official_flood
```

However:

```
planning_legal.known = false
```

until the separate e-Plan / active-zoning evidence channel is checked.

This is intentional. Protected-area screening does not prove that zoning and
planning status are fully understood.

## Next legal milestone

The next planning/legal step is a trustworthy e-Plan evidence adapter.

The Ministry's public e-Plan system exposes active and suspended plans to
citizens, but LAND RADAR should not scrape undocumented browser internals and
pretend they are a stable API.

Until a stable service/interface is verified, e-Plan remains a separate
explicit evidence gap.
