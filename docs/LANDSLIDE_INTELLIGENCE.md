# LAND RADAR — Landslide Intelligence

## Source discipline

MTA states that the 1/25,000 Türkiye Landslide Inventory vector layers are
shared with TUCBS through WMS/WFS services.

LAND RADAR does not guess the exact WFS endpoint or feature type name.

The configured service must be supplied explicitly as:

```
MTA_LANDSLIDE_WFS_URL
MTA_LANDSLIDE_TYPENAME
```

## Why inventory is not susceptibility

A landslide inventory answers:

> Where have mapped landslide features been recorded?

It does not automatically answer:

> What is the current landslide susceptibility of this parcel?

Therefore imported MTA/TUCBS inventory features use:

```
severity = UNKNOWN
hard_veto = false
```

unless a separate authoritative source explicitly supplies a severity or legal
restriction.

## AFAD susceptibility

AFAD documents landslide susceptibility/hazard products, but current sharing
conditions for the 200 m susceptibility layer are restricted.

LAND RADAR therefore keeps:

```
AFAD susceptibility = restricted_or_not_configured
```

rather than pretending that the layer is public and complete.

## Run

Set Codespaces environment variables:

```bash
export MTA_LANDSLIDE_WFS_URL="https://..."
export MTA_LANDSLIDE_TYPENAME="workspace:layer"
```

Then:

```bash
bash MTA_HEYELAN_TOP30.sh
```

or:

```bash
python scripts/landslide_scan.py
```

## Outputs

```
data/output/landslide_scan/landslide_top30.csv
data/output/landslide_scan/landslide_features.geojson
data/output/landslide_scan/landslide_scan_summary.json
```

Each Top-30 candidate gets:

- checked flag,
- finding count,
- maximum overlap ratio,
- nearest inventory geometry distance,
- explicit hard-veto state.

## Evidence Packet policy

Core hazard evidence can become known when both:

1. official USBS flood-risk screening has been checked, and
2. MTA/TUCBS landslide inventory screening has been checked.

This is a practical LAND RADAR screening policy, not a claim that every natural
hazard is fully characterized.

AFAD susceptibility remains a separate evidence limitation.
