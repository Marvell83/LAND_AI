import pytest

from land_radar.hazard import HazardSeverity
from land_radar.providers.mta_landslide import (
    MTALandslideConfigError,
    feature_to_landslide_hazard,
    resolve_mta_landslide_config,
)


def test_mta_config_requires_url_and_typename_together():
    with pytest.raises(MTALandslideConfigError):
        resolve_mta_landslide_config(
            {"MTA_LANDSLIDE_WFS_URL": "https://example.gov.tr/wfs"}
        )


def test_landslide_inventory_stays_unknown_severity():
    feature = {
        "type": "Feature",
        "id": "landslide.1",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [29.0, 40.0],
                [29.1, 40.0],
                [29.1, 40.1],
                [29.0, 40.1],
                [29.0, 40.0],
            ]],
        },
        "properties": {"DURUM": "Aktif"},
    }
    hazard = feature_to_landslide_hazard(
        feature,
        index=1,
        source_url="https://example.gov.tr/wfs",
    )
    assert hazard is not None
    assert hazard.category == "landslide_inventory"
    assert hazard.severity == HazardSeverity.UNKNOWN
    assert hazard.hard_veto is False
    assert "DURUM=Aktif" in hazard.note
