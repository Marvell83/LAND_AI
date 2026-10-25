from land_radar.providers.ogc_wfs import query_wfs_geojson


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url, params=None, timeout=None, headers=None):
        self.calls.append((url, params))
        start = int(params["startIndex"])
        if start == 0:
            return FakeResponse(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {"type": "Feature", "id": "a", "properties": {}, "geometry": {"type": "Point", "coordinates": [29, 40]}},
                        {"type": "Feature", "id": "b", "properties": {}, "geometry": {"type": "Point", "coordinates": [29.1, 40]}},
                    ],
                }
            )
        return FakeResponse(
            {
                "type": "FeatureCollection",
                "features": [
                    {"type": "Feature", "id": "c", "properties": {}, "geometry": {"type": "Point", "coordinates": [29.2, 40]}},
                ],
            }
        )


def test_wfs_pagination_and_bbox():
    session = FakeSession()
    result = query_wfs_geojson(
        "https://example.gov.tr/geoserver/wfs",
        "workspace:landslide",
        (28.0, 39.0, 30.0, 41.0),
        page_size=2,
        session=session,
    )
    assert len(result.features) == 3
    assert result.pages == 2
    assert session.calls[0][1]["outputFormat"] == "application/json"
    assert session.calls[0][1]["srsName"] == "EPSG:4326"
