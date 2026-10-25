# LAND RADAR — transparent 100 → 30 deep scan

## Purpose

The first real scan produces a GHSL-only historical acceleration shortlist.

The deep scan takes that shortlist and adds available evidence without inventing missing data.

Default flow:

```
Top 100 GHSL candidates
          ↓
Copernicus DEM / terrain
          ↓
Hazard Registry
          ↓
Catalyst Geometry Registry + official status
          ↓
explicit rules
          ↓
PASS / PASS_WITH_GAPS / DROP
          ↓
first 30 surviving research candidates
```

No aggregate Opportunity Score is used.

## Run

Windows:

```
DERIN_TARAMA_100_30.bat
```

Python:

```bash
python scripts/deep_scan.py --top 30
```

## Terrain

If CDSE OAuth is configured, the deep scan uses cached Copernicus DEM GLO-90 results.

Default physical rule:

```
P90 slope > 12 degrees -> DROP
```

This threshold is a research policy, not a universal land-investment law. It can be changed:

```bash
python scripts/deep_scan.py --max-p90-slope 15
```

If DEM is unavailable:

```
terrain_unknown
```

The cell is not silently treated as flat.

## Hazard Registry

Default path:

```
data/processed/hazard_registry.geojson
```

If absent:

```
hazard_unknown
```

If present, every shortlisted cell receives a hazard summary, including zero linked findings when the loaded registry was actually checked.

A hard-veto can drop a cell only when:

1. the hazard intersects the cell, and
2. the imported feature explicitly contains `hard_veto=true`.

## Catalyst Geometry Registry

Default path:

```
data/processed/geometry_registry.geojson
```

When present, the script attempts to obtain current OSBÜK and AYGM status evidence and link matching catalyst IDs to stored geometry.

If geometry is absent or official status cannot be resolved:

```
catalyst_unknown
```

The scan continues with a visible data gap.

## Default catalyst policy

By default catalyst evidence is **not mandatory** because the official geometry registry is still incomplete.

To make a verified catalyst within the selected radius mandatory:

```bash
python scripts/deep_scan.py --require-catalyst
```

Default distance:

```
20 km
```

Change it with:

```bash
python scripts/deep_scan.py --max-catalyst-km 10
```

## Outputs

```
data/output/deep_scan/deep_scan_all_candidates.csv
data/output/deep_scan/deep_scan_top30.csv
data/output/deep_scan/deep_scan_top30.geojson
data/output/deep_scan/deep_scan_summary.json
```

The full CSV keeps dropped candidates and their reasons.

That is important: LAND RADAR should be able to explain **why a candidate disappeared**.

## Interpretation

`PASS`

All currently required evidence checks passed with no missing layer recorded by this funnel.

`PASS_WITH_GAPS`

No explicit drop rule fired, but one or more evidence layers are unavailable.

`DROP`

At least one explicit exclusion rule fired, for example:

- P90 slope above the selected threshold,
- intersecting explicit hard-veto hazard,
- verified catalyst required but not present within range.

## Next stage

The 30 surviving candidates are the appropriate set for expensive analyses:

1. Sentinel recent-change confirmation,
2. road/access detail,
3. planning and legal constraints,
4. local comparable-price collection,
5. liquidity / future-buyer analysis.

Only after that stage should LAND RADAR move toward:

```
30 → 10 → parcel
```
