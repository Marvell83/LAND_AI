# LAND RADAR — Candidate Evidence Packets

## Purpose

After the first scan, deep scan and optional Sentinel confirmation, every Top-30 research cell should have one inspectable evidence record.

The packet is designed to answer:

> What do we actually know about this cell, and what is still missing?

It is not designed to answer:

> Should I buy this land?

## Build

Windows:

```
KANIT_PAKETLERI.bat
```

Python:

```bash
python scripts/build_evidence_packets.py
```

## Inputs

Primary:

```
data/output/deep_scan/deep_scan_top30.csv
```

Historical GHSL detail, when available:

```
data/output/first_scan/ghsl_top_candidates.csv
```

Optional Sentinel evidence:

```
data/output/sentinel_confirm/sentinel_top30_change.csv
```

If Sentinel has not been run, the packet remains valid but marks that layer missing.

## Evidence layers

Each packet tracks:

1. `urban_history`
2. `terrain`
3. `hazard`
4. `catalyst`
5. `sentinel_recent_change`
6. `planning_legal`
7. `price`

## Urban history

When the first-scan output is available, the packet retains:

- built-up m² in 2010,
- built-up m² in 2015,
- built-up m² in 2020,
- 2010–2015 CAGR,
- 2015–2020 CAGR,
- acceleration in percentage-points/year,
- occupied-pixel-share acceleration,
- raw signal label.

This preserves the historical evidence instead of reducing it to one rank.

## Evidence coverage

The packet calculates:

```
known evidence layers / expected evidence layers
```

and reports it as `evidence_coverage_pct`.

Example:

```
5 / 7 = 71.4%
```

This is strictly a **data completeness metric**.

It is not:

- an Opportunity Score,
- a probability of appreciation,
- an investment score,
- a safety score.

A candidate with 100% evidence coverage can still be a bad investment.

## Missing layers

At the current stage, two important layers remain deliberately incomplete:

### planning_legal

Requires authoritative plan/zoning/protection/legal evidence.

### price

Requires cell- or parcel-relevant comparable data and ultimately a point-in-time price history.

LAND RADAR does not fill those gaps with AI guesses.

## Outputs

Master packet:

```
data/output/evidence_packets/candidate_evidence_packets.json
```

Matrix:

```
data/output/evidence_packets/candidate_evidence_matrix.csv
```

Individual cell packets:

```
data/output/evidence_packets/cells/LR-xxx-xxx.json
```

## Why individual packets matter

When the system eventually narrows from 30 to 10, every decision should be auditable.

A reviewer should be able to open one cell file and see:

- why it entered the shortlist,
- what risk evidence was checked,
- whether terrain is known,
- whether a catalyst has verified status and geometry,
- whether recent satellite change exists,
- which critical evidence layers are still missing.

That audit trail is more important than producing a flashy single score too early.
