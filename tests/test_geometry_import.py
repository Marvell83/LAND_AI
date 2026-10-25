from datetime import date

import pytest

from land_radar.geometry_import import (
    GeometryImportError,
    make_registry_entries,
    raw_geojson_geometries,
    raw_kml_geometries,
)


def test_raw_kml_linestring_import():
    kml = """<?xml version="1.0" encoding="UTF-8"?>
    <kml xmlns="http://www.opengis.net/kml/2.2">
      <Document>
        <Placemark>
          <name>Test Route</name>
          <LineString>
            <coordinates>29.0,40.0,0 29.1,40.1,0</coordinates>
          </LineString>
        </Placemark>
      </Document>
    </kml>
    """
    raw = raw_kml_geometries(kml)
    assert len(raw) == 1
    assert raw[0].name == "Test Route"
    assert raw[0].geometry_geojson["type"] == "LineString"


def test_raw_geojson_feature_collection():
    raw = raw_geojson_geometries(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "Route A"},
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[29.0, 40.0], [29.1, 40.1]],
                    },
                }
            ],
        }
    )
    assert raw[0].name == "Route A"


def test_digitized_map_confidence_is_capped():
    raw = raw_geojson_geometries(
        {
            "type": "LineString",
            "coordinates": [[29.0, 40.0], [29.1, 40.1]],
        }
    )
    with pytest.raises(GeometryImportError):
        make_registry_entries(
            raw,
            catalyst_id="road:kgm:test",
            source="KGM map digitization",
            source_url="https://www.kgm.gov.tr/map.jpg",
            observed_date=date(2026, 10, 25),
            confidence=95,
            geometry_role="digitized_official_map",
            manual_verified=True,
        )


def test_schematic_route_requires_manual_verification():
    raw = raw_geojson_geometries(
        {
            "type": "LineString",
            "coordinates": [[29.0, 40.0], [29.1, 40.1]],
        }
    )
    with pytest.raises(GeometryImportError):
        make_registry_entries(
            raw,
            catalyst_id="road:kgm:test",
            source="KGM schematic map",
            source_url="https://www.kgm.gov.tr/map.jpg",
            observed_date=date(2026, 10, 25),
            confidence=50,
            geometry_role="schematic_route",
            manual_verified=False,
        )


def test_official_vector_route_accepts_high_confidence():
    raw = raw_geojson_geometries(
        {
            "type": "LineString",
            "coordinates": [[29.0, 40.0], [29.1, 40.1]],
        }
    )
    entries = make_registry_entries(
        raw,
        catalyst_id="road:kgm:test",
        source="Official vector service",
        source_url="https://example.gov.tr/route.geojson",
        observed_date=date(2026, 10, 25),
        confidence=98,
        geometry_role="official_vector_route",
        manual_verified=False,
    )
    assert entries[0].evidence.confidence == 98
