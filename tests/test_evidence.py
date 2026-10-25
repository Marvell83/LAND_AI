from datetime import date

from land_radar.evidence import filter_point_in_time, point_in_time_safe
from land_radar.models import Evidence


def test_future_publication_is_rejected():
    item = Evidence(
        source="official",
        claim="test",
        observed_date=date(2015, 1, 1),
        published_date=date(2016, 1, 1),
    )
    assert point_in_time_safe(item, date(2015, 12, 31)) is False


def test_point_in_time_filter():
    old = Evidence(source="A", claim="old", published_date=date(2014, 1, 1))
    future = Evidence(source="B", claim="future", published_date=date(2018, 1, 1))
    result = filter_point_in_time([old, future], date(2015, 1, 1))
    assert result == [old]
