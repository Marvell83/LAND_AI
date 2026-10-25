from datetime import date

import pytest

from land_radar.providers.copernicus_stac import build_search_payload, parse_scene_summary


def test_stac_payload_uses_current_collection():
    payload = build_search_payload(
        (26.0, 39.0, 27.0, 40.0),
        date(2025, 1, 1),
        date(2025, 2, 1),
        max_cloud_cover=15,
        limit=10,
    )
    assert payload["collections"] == ["sentinel-2-l2a"]
    assert payload["query"]["eo:cloud_cover"]["lte"] == 15.0


def test_stac_rejects_bad_date_order():
    with pytest.raises(ValueError):
        build_search_payload(
            (26.0, 39.0, 27.0, 40.0),
            date(2025, 2, 1),
            date(2025, 1, 1),
        )


def test_parse_scene_summary():
    payload = {
        "features": [
            {"id": "A", "properties": {"datetime": "2025-01-01T10:00:00Z", "eo:cloud_cover": 10}},
            {"id": "B", "properties": {"datetime": "2025-01-05T10:00:00Z", "eo:cloud_cover": 20}},
        ]
    }
    result = parse_scene_summary(payload)
    assert result.count == 2
    assert result.min_cloud_cover == 10.0
    assert result.median_cloud_cover == 15.0
