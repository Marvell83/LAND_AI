# LAND RADAR — Top-30 comparable-price evidence

## Purpose

The Top-30 price scan does not estimate a parcel's fair value.

It answers a narrower question:

> Is there enough recent, geographically relevant comparable-price evidence
> around this candidate cell to establish a usable local TL/m² reference?

## Input

Candidate cells:

```
data/output/deep_scan/deep_scan_top30.csv
```

Comparable CSV required fields:

```
observed_date
price_tl
area_m2
```

Strongly recommended:

```
lat
lon
source_type
land_type
listing_id
province
district
neighborhood
```

Without coordinates, the Top-30 geographic scan cannot establish local
comparability reliably.

## Run in Codespaces

```bash
bash PRICE_TOP30.sh data/processed/comparables.csv
```

or:

```bash
python scripts/candidate_price_scan.py   --comparables data/processed/comparables.csv   --radius-km 10   --max-age-days 730   --land-type tarla
```

## Optional CPI adjustment

If a monthly CPI/index CSV is available:

```bash
python scripts/candidate_price_scan.py   --comparables data/processed/comparables.csv   --cpi data/processed/cpi.csv
```

CPI schema:

```
date,index
```

Every observation is moved to the selected analysis-date price level before
the robust comparable distribution is calculated.

## Robust filtering

The engine applies the existing LAND RADAR price discipline:

- point-in-time cutoff,
- maximum observation age,
- optional land-type filter,
- geographic radius filter,
- TL/m² normalization,
- log-price robust outlier filtering,
- median and IQR as primary distribution statistics.

## Confidence

A candidate price layer is marked `known=true` only when the comparable
summary has:

```
MEDIUM
```

or:

```
HIGH
```

confidence.

`LOW` means:

> checked, but not sufficient to promote the price layer to known.

`NONE` means:

> no usable comparable observations survived the filters.

## Output

```
data/output/price_scan/price_top30.csv
data/output/price_scan/price_scan_summary.json
```

Important fields:

- `checked`
- `known`
- `price_basis`
- `used_rows`
- `median_price_per_m2`
- `p25_price_per_m2`
- `p75_price_per_m2`
- `dispersion_ratio`
- `median_age_days`
- `confidence_label`
- `source_mix`

## Evidence Packet

After the price scan:

```bash
python scripts/build_evidence_packets.py
```

The packet's `price.known` field follows the confidence rule above.

This still does not create a Mispricing Score.

Mispricing requires a subject parcel price plus development, legal, liquidity
and point-in-time calibration evidence.
