from land_radar.providers.arcgis_geojson import query_layer_geojson


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url, params=None, timeout=None, headers=None):
        self.calls.append((url, params))
        offset = int(params["resultOffset"])
        if offset == 0:
            return FakeResponse(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "properties": {"OBJECTID": 1},
                            "geometry": {
                                "type": "Point",
                                "coordinates": [29.0, 40.0],
                            },
                        },
                        {
                            "type": "Feature",
                            "properties": {"OBJECTID": 2},
                            "geometry": {
                                "type": "Point",
                                "coordinates": [29.1, 40.0],
                            },
                        },
                    ],
                    "properties": {"exceededTransferLimit": True},
                }
            )
        return FakeResponse(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"OBJECTID": 3},
                        "geometry": {
                            "type": "Point",
                            "coordinates": [29.2, 40.0],
                        },
                    }
                ],
            }
        )


def test_arcgis_query_pages_geojson():
    session = FakeSession()
    result = query_layer_geojson(
        "https://example.gov.tr/arcgis/MapServer/0",
        (28.0, 39.0, 30.0, 41.0),
        page_size=2,
        session=session,
    )
    assert len(result.features) == 3
    assert result.pages == 2
    assert session.calls[0][1]["f"] == "geojson"
    assert session.calls[0][1]["outSR"] == "4326"
