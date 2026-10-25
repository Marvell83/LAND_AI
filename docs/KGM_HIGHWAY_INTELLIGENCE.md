# LAND RADAR — KGM Highway Catalyst Intelligence

## Purpose

The highway catalyst layer separates two different facts:

1. official project status,
2. route geometry.

LAND RADAR never treats project-description prose as a route geometry.

## Official status source

Current source:

```
https://www.kgm.gov.tr/Sayfalar/KGM/SiteTr/Projeler/Projeler-Otoyol.aspx
```

The official KGM page lists motorway projects and links to project-detail
pages.

The detail pages can contain explicit lifecycle statements such as:

- tender completed,
- implementation contract signed,
- construction continuing,
- project opened to operation.

## Conservative stage mapping

LAND RADAR maps only explicit phrases:

```
official project page only -> OFFICIAL_INTENT
explicit approval / EIA approval -> PLAN_OR_APPROVAL
explicit tender / contract -> BUDGET_OR_TENDER
explicit construction continuing -> CONSTRUCTION_STARTED
explicit project opened/completed -> COMPLETED
```

Construction has priority over older tender statements.

Completion detection is deliberately conservative because a project page may
mention an already-completed connecting motorway.

## Geometry remains separate

Catalyst id format:

```
road:kgm:<project-page-slug>
```

Example:

```
road:kgm:ankarakirikkaledelice
```

A KGM project can have excellent official status evidence while still having:

```
spatial_known = false
```

if no matching route geometry exists in:

```
data/processed/geometry_registry.geojson
```

This is intentional.

## Geometry Registry example

A verified route can be stored with the same catalyst id:

```json
{
  "type": "Feature",
  "geometry": {
    "type": "LineString",
    "coordinates": []
  },
  "properties": {
    "catalyst_id": "road:kgm:ankarakirikkaledelice",
    "source": "verified official/manual route source",
    "feature_name": "Ankara-Kırıkkale-Delice Otoyolu",
    "observed_date": "2026-10-25",
    "source_url": "https://www.kgm.gov.tr/...",
    "confidence": 95,
    "geometry_role": "project_route",
    "manual_verified": true
  }
}
```

Do not create geometry from a textual route description alone.

## Top-30 scan

Codespaces:

```bash
bash KGM_OTOYOL_TOP30.sh
```

or:

```bash
python scripts/kgm_highway_scan.py
```

Outputs:

```
data/output/kgm_highway_scan/kgm_highway_projects.csv
data/output/kgm_highway_scan/kgm_highway_links.csv
data/output/kgm_highway_scan/kgm_highway_top30.csv
data/output/kgm_highway_scan/kgm_highway_scan_summary.json
```

## Candidate-level fields

```
status_checked
geometry_registry_checked
kgm_geometry_count
linked_project_count
spatial_known
nearest_project_id
nearest_project_name
nearest_project_stage
nearest_project_distance_km
nearest_influence_code
nearest_evidence_complete
```

## Evidence Packet integration

After the scan:

```bash
python scripts/build_evidence_packets.py
```

Each candidate packet gains:

```
catalyst.kgm_highway
```

## Deep scan integration

The normal deep-scan command now loads:

- OSBÜK OSB status,
- AYGM railway status,
- KGM highway-project status,

when a Geometry Registry exists.

Only catalysts with matching geometry can produce spatial links.

## Current limitation

KGM publishes current road-network and project information, but LAND RADAR
does not currently have a verified public vector route service for every
future motorway project.

Until such a service is verified, route geometry remains explicit registry
evidence rather than inferred geometry.
