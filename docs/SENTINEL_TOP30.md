# LAND RADAR — Sentinel Top-30 confirmation

## Purpose

After the 100 → 30 deep scan, LAND RADAR can compare two seasonal Sentinel-2 L2A windows for every surviving candidate.

The output remains **raw physical-change evidence**.

It does not automatically say:

- new construction occurred,
- zoning changed,
- land value will rise,
- the candidate should be purchased.

## Run

Windows:

```
SENTINEL_TOP30.bat
```

Python:

```bash
python scripts/sentinel_confirm.py
```

CDSE OAuth credentials are required.

## Default comparison

If dates are not supplied, the script compares:

- the most recent 60-day window,
- approximately the same 60-day window one year earlier.

Explicit reproducible windows are preferable for research:

```bash
python scripts/sentinel_confirm.py \
  --first-start 2025-08-01 \
  --first-end 2025-09-30 \
  --second-start 2026-08-01 \
  --second-end 2026-09-30
```

## Measurements

For each cell:

- median NDVI,
- median NDBI,
- median BSI,
- vegetation SCL share,
- bare-soil SCL share,
- water SCL share,
- valid land-pixel count,

for both periods, plus deltas.

## Interpretation discipline

Examples of potentially interesting combinations:

- NDVI down,
- NDBI up,
- BSI up,
- bare-soil share up.

But these can also be caused by:

- harvest,
- seasonal agricultural cycles,
- soil exposure,
- quarry activity,
- temporary works,
- different atmospheric conditions,
- residual cloud/shadow effects.

Therefore LAND RADAR does not convert these values directly into a construction score.

Recent physical change becomes stronger evidence only when combined with other sources such as:

- GHSL historical acceleration,
- OSM/official road or industrial geometry,
- official catalyst status,
- planning evidence,
- time-series persistence.

## Cache

Each cell/date-window request is cached under:

```
data/cache/sentinel/
```

The first Top-30 run normally requires two Process API requests per cell.

Re-running the exact same windows uses cached summaries.

## Outputs

```
data/output/sentinel_confirm/sentinel_top30_change.csv
data/output/sentinel_confirm/top30_with_sentinel.csv
data/output/sentinel_confirm/sentinel_summary.json
```

`top30_with_sentinel.csv` joins the deep-scan candidate fields with the Sentinel evidence so the next research stage can work from a single table.
