from land_radar.providers.osm import build_highway_query, parse_road_summary


def test_overpass_bbox_order():
    q = build_highway_query(26.0, 39.0, 27.0, 40.0)
    assert '(39.0,26.0,40.0,27.0)' in q


def test_parse_road_summary():
    payload = {
        "elements": [
            {"type": "way", "tags": {"highway": "primary"}, "center": {"lat": 40.0, "lon": 29.1}},
            {"type": "way", "tags": {"highway": "residential"}, "center": {"lat": 40.0, "lon": 29.05}},
            {"type": "node", "tags": {"highway": "traffic_signals"}},
        ]
    }
    result = parse_road_summary(payload, center_lat=40.0, center_lon=29.0)
    assert result.total_highway_ways == 2
    assert result.major_highway_ways == 1
    assert result.nearest_major_way_center_km is not None
    assert result.highway_classes[0] == ("primary", 1)
