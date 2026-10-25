from land_radar.providers.osm_geometry import (
    best_name_matches,
    build_industrial_geometry_query,
    build_rail_geometry_query,
    name_similarity,
    parse_osm_geometries,
)


def test_queries_request_geometry():
    industrial = build_industrial_geometry_query((26.0, 39.0, 27.0, 40.0))
    rail = build_rail_geometry_query((26.0, 39.0, 27.0, 40.0))
    assert "out body geom;" in industrial
    assert "out body geom;" in rail


def test_parse_way_polygon_and_relation_fallback():
    payload = {
        "elements": [
            {
                "type": "way",
                "id": 1,
                "tags": {"name": "Bursa Organize Sanayi Bölgesi", "landuse": "industrial"},
                "geometry": [
                    {"lat": 40.0, "lon": 29.0},
                    {"lat": 40.0, "lon": 29.01},
                    {"lat": 40.01, "lon": 29.01},
                    {"lat": 40.01, "lon": 29.0},
                    {"lat": 40.0, "lon": 29.0},
                ],
            },
            {
                "type": "relation",
                "id": 2,
                "tags": {"name": "Test Rail", "railway": "rail"},
                "bounds": {
                    "minlat": 40.0,
                    "minlon": 29.0,
                    "maxlat": 40.1,
                    "maxlon": 29.1,
                },
            },
        ]
    }
    features = parse_osm_geometries(payload)
    assert len(features) == 2
    assert features[0].geometry_role == "full_way_polygon"
    assert features[0].confidence == 70.0
    assert features[1].geometry_role == "relation_bounds_center_fallback"
    assert features[1].confidence == 30.0


def test_turkish_name_similarity_and_match():
    payload = {
        "elements": [
            {
                "type": "way",
                "id": 1,
                "tags": {"name": "Bursa Organize Sanayi Bölgesi"},
                "geometry": [
                    {"lat": 40.0, "lon": 29.0},
                    {"lat": 40.0, "lon": 29.01},
                ],
            },
            {
                "type": "way",
                "id": 2,
                "tags": {"name": "Bandırma Limanı"},
                "geometry": [
                    {"lat": 40.3, "lon": 27.9},
                    {"lat": 40.31, "lon": 27.91},
                ],
            },
        ]
    }
    features = parse_osm_geometries(payload)
    score = name_similarity("Bursa OSB", "Bursa Organize Sanayi Bölgesi")
    assert score == 1.0

    matches = best_name_matches("Bursa OSB", features)
    assert matches[0][0].osm_id == 1
    assert matches[0][1] == 1.0
