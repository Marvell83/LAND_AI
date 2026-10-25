from land_radar.grid import GridCell
from land_radar.planning import LegalEffect, PlanningConstraint
from land_radar.spatial.planning_overlap import (
    batch_link_constraints,
    link_constraint_to_cell,
    summarize_cell_planning,
)


def _constraint(hard_veto=False):
    return PlanningConstraint(
        constraint_id="protected:test",
        category="national_park",
        geometry_geojson={
            "type": "Polygon",
            "coordinates": [[
                [28.99, 39.99],
                [29.01, 39.99],
                [29.01, 40.01],
                [28.99, 40.01],
                [28.99, 39.99],
            ]],
        },
        source="official",
        legal_effect=LegalEffect.REVIEW_REQUIRED,
        hard_veto=hard_veto,
        confidence=95,
    )


def test_constraint_intersection_requires_legal_review():
    cell = GridCell(cell_id="A", center_lat=40.0, center_lon=29.0, size_km=5.0)
    link = link_constraint_to_cell(cell, _constraint())
    summary = summarize_cell_planning("A", [link], checked=True)

    assert link.intersects_cell is True
    assert link.overlap_ratio > 0
    assert summary.checked is True
    assert summary.legal_review_required is True
    assert summary.hard_veto is False


def test_constraint_hard_veto_must_be_explicit():
    cell = GridCell(cell_id="A", center_lat=40.0, center_lon=29.0, size_km=5.0)
    link = link_constraint_to_cell(cell, _constraint(hard_veto=True))
    summary = summarize_cell_planning("A", [link], checked=True)
    assert summary.hard_veto is True
    assert summary.hard_veto_categories == ("national_park",)


def test_checked_zero_findings_is_distinct_from_unknown():
    known = summarize_cell_planning("A", [], checked=True)
    unknown = summarize_cell_planning("A", [], checked=False)
    assert known.checked is True
    assert unknown.checked is False
