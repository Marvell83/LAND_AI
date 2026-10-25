# LAND RADAR official risk-data strategy

## 1. Current rule

LAND RADAR does not label a cell "safe" merely because no risk layer was loaded.

No hazard data means:

```
UNKNOWN
```

not:

```
LOW
```

A high-severity finding is also not automatically a hard veto. A hard veto must be explicit in the imported source interpretation.

## 2. Official source families

### AFAD

AFAD states that landslide, rockfall and avalanche susceptibility / hazard maps produced in ARAS have been served to other public institutions through Türkiye Ulusal Coğrafi Bilgi Sistemi (TUCBS).

Reference:
https://www.afad.gov.tr/kurumlar/afad.gov.tr/e_Kutuphane/Kurumsal-Raporlar/2020_IdareFaaliyetRaporu_v2.pdf

AFAD disaster-analysis portal:
https://www.afad.gov.tr/afet-analiz

### TUCBS

TUCBS supports OGC geographic services such as WMS, WFS, WCS and WMTS. Specific data-sharing conditions are controlled by the publishing institution.

Reference:
https://akademi.tucbs.gov.tr/egitim-dokumani.html

LAND RADAR does not hard-code a hazard WFS endpoint until the exact layer URL, access conditions and schema have been verified.

### USBS / flood management

The Ministry of Agriculture and Forestry states that flood hazard/risk maps prepared under flood-management plans are shared with the public through the Ulusal Su Bilgi Sistemi (USBS).

Portal:
https://usbs.tarimorman.gov.tr/portal/

Reference:
https://www.tarimorman.gov.tr/SYGM/Sayfalar/GormeEngellilerDetay.aspx?Liste=Haber&OgeId=1387

## 3. Hazard Registry format

Until stable machine-readable service endpoints are verified, LAND RADAR accepts a dated GeoJSON FeatureCollection.

Required properties for every feature:

```
hazard_id
category
severity
source
```

Optional but strongly recommended:

```
observed_date
source_url
hard_veto
confidence
note
```

Severity values:

```
NONE
LOW
MEDIUM
HIGH
CRITICAL
```

Example:

```json
{
  "type": "Feature",
  "geometry": {
    "type": "Polygon",
    "coordinates": []
  },
  "properties": {
    "hazard_id": "usbs:flood:example",
    "category": "flood",
    "severity": "HIGH",
    "source": "USBS official export",
    "observed_date": "2026-10-25",
    "hard_veto": false,
    "confidence": 95
  }
}
```

## 4. Cell calculations

For every hazard geometry and research cell LAND RADAR calculates:

- whether the hazard intersects the cell,
- minimum edge-to-hazard distance,
- percentage of the research cell overlapped by the hazard polygon,
- maximum severity among linked hazards,
- explicit hard-veto categories.

Hard-veto is activated only when:

1. the hazard geometry intersects the cell, and
2. the imported hazard feature explicitly contains `hard_veto=true`.

This prevents a nearby but non-intersecting hazard polygon from automatically eliminating a cell.

## 5. Terrain is separate from hazard

Copernicus DEM GLO-90 provides:

- elevation,
- mean slope,
- P90 slope,
- maximum slope.

Terrain is a physical suitability layer. It is not a substitute for an official landslide or flood hazard map.

A steep cell may be physically unattractive without being inside an official landslide hazard polygon.

A flat cell may still be inside an official flood hazard polygon.

The two layers therefore remain separate.

## 6. Candidate Funnel

Current funnel:

```
broad GHSL scan pool
        ↓
top cells by measurable historical acceleration
        ↓
DEM terrain batch
        ↓
official/manual hazard registry
        ↓
catalyst geometry registry
        ↓
PASS / PASS_WITH_GAPS / DROP
```

No aggregate Opportunity Score is produced at this stage.

A cell is dropped only for explicit rules such as:

- P90 slope above the selected threshold,
- an intersecting explicit hard-veto hazard,
- required catalyst missing within the selected radius.

Missing evidence creates a data-gap flag rather than a false negative or false positive.

## 7. Next risk milestone

The next step is to verify stable public service endpoints or downloadable datasets for:

1. flood hazard / flood risk,
2. landslide susceptibility / hazard,
3. protected forest / pasture / agricultural-protection constraints,
4. active fault and geologic context.

When a service is confirmed, its data should be transformed into the same Hazard Registry schema rather than bypassing the evidence model.
