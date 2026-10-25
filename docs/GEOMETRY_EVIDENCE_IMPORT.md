# LAND RADAR — Geometry Evidence Import

## Why this exists

Catalyst status and catalyst geometry are different evidence.

A project can be officially under construction while LAND RADAR still does
not know its exact route geometry.

The geometry importer lets verified raw spatial data enter the Geometry
Registry without pretending that every source has the same precision.

## Supported formats

- GeoJSON / JSON
- KML

Supported KML Placemark geometry:

- LineString / MultiLineString
- Polygon / MultiPolygon

## Required provenance

Every import requires:

- `catalyst_id`
- source name
- HTTPS source URL
- observed date
- confidence
- geometry role

## Geometry roles

### official_vector_route

Use only for a route supplied as actual vector geometry by an authoritative
source.

Typical confidence:

```
90–100
```

### digitized_official_map

Use when a human has digitized an official map.

Rules:

- `manual_verified=true`
- confidence cannot exceed 80

This is not equivalent to official vector geometry.

### schematic_route

Use when the source itself is schematic or approximate.

Rules:

- `manual_verified=true`
- confidence cannot exceed 60

A schematic route should never drive parcel-level distance conclusions.

### official_boundary

Use for authoritative polygon boundaries such as an OSB boundary.

### observed_geometry

Generic observed spatial geometry when none of the stricter roles apply.

## CLI

Example official vector route:

```bash
python scripts/import_geometry_evidence.py   --input data/raw/project_route.kml   --catalyst-id road:kgm:ankarakirikkaledelice   --source "KGM official vector source"   --source-url "https://..."   --role official_vector_route   --confidence 98
```

Example manually digitized official map:

```bash
python scripts/import_geometry_evidence.py   --input data/raw/project_route.geojson   --catalyst-id road:kgm:kinalimalkara   --source "KGM 2026 Otoyollar Haritası / manual digitization"   --source-url "https://www.kgm.gov.tr/SiteCollectionImages/KGMimages/Otoyollar/otoyollarharitasi.jpg"   --role digitized_official_map   --confidence 75   --manual-verified
```

The 2026 motorway map is a schematic image, so a digitized route from that
map remains lower-confidence geometry.

## Codespaces helper

```bash
bash GEOMETRI_KANIT_IMPORT.sh   data/raw/project_route.kml   road:kgm:project-id   "Official source"   "https://..."   official_vector_route   98
```

## Output

```
data/processed/geometry_registry.geojson
```

Existing registry entries are preserved.

Exact duplicates based on catalyst id, feature id and feature name are not
appended twice.

## Streamlit

Spatial Intelligence now contains:

```
Ham GeoJSON / KML → Geometry Registry
```

The same provenance and confidence rules are enforced in the UI.

## KGM workflow

1. Fetch KGM official project status.
2. Note the stable LAND RADAR project id:
   `road:kgm:<slug>`.
3. Obtain or verify a spatial route source.
4. Import the geometry with the exact same catalyst id.
5. Run:
   `python scripts/kgm_highway_scan.py`.
6. Only then can LAND RADAR calculate project-to-cell distance.

## Reliability rule

A JPG map, route description, or planning narrative is evidence, but it is not
an exact vector route.

LAND RADAR preserves that distinction.
