# LAND RADAR Spatial Intelligence

## 1. Why spatial evidence is separate

LAND RADAR keeps two evidence channels separate:

### Status evidence

Examples:

- OSBÜK says an OSB is operating.
- AYGM says a railway project is ongoing.
- A ministry publishes an approved plan.

This evidence answers:

> What is the official maturity/status?

### Geometry evidence

Examples:

- OpenStreetMap industrial boundary.
- Official GeoJSON/shapefile.
- A manually imported route geometry.
- A point fallback derived from a published location.

This evidence answers:

> Where is it?

A reliable status does not automatically mean reliable geometry, and a precise geometry does not automatically prove the project's current legal/status stage.

## 2. Distance calculation

Research grid cells are WGS84 polygons.

For each cell, LAND RADAR creates a local azimuthal-equidistant CRS centered on the cell and transforms both:

- the grid cell polygon,
- the catalyst geometry,

into metres.

The engine then calculates **minimum edge-to-geometry distance**.

If the geometry intersects the cell:

```
distance = 0 km
```

This avoids calculating distance from cell-centre to feature-centre, which can materially overstate or understate proximity.

## 3. Influence bands

Current default bands are **context labels only**:

| Code | Distance |
|---|---:|
| INTERSECTS | cell intersection |
| VERY_NEAR | <= 2 km |
| NEAR | <= 5 km |
| CORRIDOR | <= 10 km |
| REGIONAL | <= 20 km |
| OUTSIDE | > 20 km |

These are not valuation weights and do not claim a causal economic impact.

The thresholds are configurable and must eventually be calibrated by historical tests.

## 4. OpenStreetMap geometry evidence

The current OSM provider can query nearby:

- named industrial land-use geometries,
- rail / construction / proposed railway geometries.

Overpass is requested with full geometry.

Geometry confidence is intentionally lower than official status confidence.

Typical roles:

- `full_way_polygon` — 70
- `full_way_line` — 65
- `relation_member_geometry` — 55
- `relation_bounds_center_fallback` — 30
- `relation_center_fallback` — 25

These numbers are provenance/geometry-quality indicators, not investment probabilities.

## 5. Name matching

LAND RADAR can propose OSBÜK ↔ OSM matches using normalized token overlap.

Turkish characters are folded for matching and generic terms such as:

- OSB
- organize
- sanayi
- bölgesi

are removed.

The output is an **automatic candidate**, not an official identity match.

A later version should add:

- province/district consistency,
- official OSB identifiers where available,
- geometry overlap with MEYDİP/official sources,
- manual confirmation workflow.

## 6. Current limitations

The current version does **not** claim:

- an OSM boundary is an official cadastral OSB boundary,
- an OSM railway segment is the exact AYGM project route,
- proximity automatically creates land value,
- a 5 km catalyst is twice as valuable as a 10 km catalyst.

Those claims require separate evidence and calibration.

## 7. Next spatial milestone

Build a persistent Geometry Registry:

```
catalyst_id
geometry_source
source_feature_id
geometry
observed_date
geometry_role
geometry_confidence
manual_verified
```

Then batch-link that registry against the pilot grid.

That enables:

```
500 cells
  ↓
urban growth
  ↓
terrain
  ↓
road access
  ↓
catalyst distance
  ↓
risk
  ↓
top research candidates
```

without re-querying public endpoints for every cell.
