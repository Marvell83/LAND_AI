from land_radar.providers.tucbs_plan_wms import services_for_point


def test_balikesir_canakkale_service_coverage():
    services = services_for_point(40.0, 27.5)
    ids = {service.service_id for service in services}
    assert "csb_cdp_cb" in ids


def test_bilecik_service_coverage():
    services = services_for_point(40.0, 30.0)
    ids = {service.service_id for service in services}
    assert "csb_cdp_bilecik" in ids


def test_uncovered_point_remains_unknown():
    assert services_for_point(38.0, 35.0) == []
