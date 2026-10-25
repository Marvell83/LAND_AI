# LAND RADAR price model discipline

## Why the price layer is deliberately conservative

LAND RADAR separates:

1. **Observed price** — what was actually seen in a dataset.
2. **Comparable distribution** — how similar observations are distributed.
3. **Comparable gap** — how far a subject price sits from that distribution.
4. **Mispricing hypothesis** — a later model that also requires development, risk, liquidity and source-quality evidence.

A low asking price is not automatically a bargain.

## Current CSV schema

Required columns:

- `observed_date`
- `price_tl`
- `area_m2`

Optional columns:

- `source_type`
- `lat`
- `lon`
- `land_type`
- `province`
- `district`
- `neighborhood`
- `listing_id`

Recommended `source_type` values:

- `asking`
- `transaction`
- `appraisal`
- `assessed`
- `auction`
- `other`

Do not merge these into a single indistinguishable price series.

## Point-in-time rule

An observation after the requested analysis date is excluded.

This is mandatory for honest backtests.

## Robust filtering

The current engine:

- rejects non-positive price/area observations,
- calculates TL/m²,
- optionally filters by land type,
- optionally filters by distance when coordinates exist,
- optionally restricts age,
- detects extreme observations using robust z-scores on log(TL/m²).

The output reports the median and IQR rather than using the arithmetic mean as the primary reference.

## Comparable gap

For a subject parcel:

```
subject_ppm = subject_price / subject_area
gap_pct = comparable_median_ppm / subject_ppm - 1
```

A positive gap means the subject is below the comparable median.

This is **not** automatically a Mispricing Score.

## Source-quality problem

Public parcel geometry and cadastral attributes do not imply access to a reliable market transaction-price series. The price engine therefore accepts explicit user/institutional datasets instead of pretending that cadastral data is transaction-price data.

## Next price milestones

1. retain listing history and price revisions,
2. deduplicate repeated listings,
3. build real-price series using a separately versioned CPI index,
4. compare land price momentum against development acceleration,
5. estimate liquidity from listing duration / turnover proxies,
6. calibrate a Mispricing model only after backtests.

The target divergence signal is:

> physical/catalyst fundamentals improve while real land prices remain flat or lag.

That signal must be supported by time-aligned evidence; it is not inferred from a single listing.
