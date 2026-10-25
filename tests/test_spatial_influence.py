from land_radar.spatial.influence import classify_influence


def test_intersection_has_explicit_band():
    band = classify_influence(0.0, intersects_cell=True)
    assert band.code == "INTERSECTS"


def test_context_bands_are_distance_based():
    assert classify_influence(1.5).code == "VERY_NEAR"
    assert classify_influence(4.0).code == "NEAR"
    assert classify_influence(8.0).code == "CORRIDOR"
    assert classify_influence(15.0).code == "REGIONAL"
    assert classify_influence(25.0).code == "OUTSIDE"
