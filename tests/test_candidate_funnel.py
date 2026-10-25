from land_radar.candidate_funnel import (
    CandidatePolicy,
    build_candidate_funnel,
    surviving_candidates,
)
from land_radar.hazard import HazardSeverity
from land_radar.spatial.hazard_overlap import CellHazardSummary
from land_radar.terrain_scan import TerrainScanRecord
from land_radar.urban_scan import UrbanScanRecord


def _urban(cell_id, acceleration):
    return UrbanScanRecord(
        cell_id=cell_id,
        center_lat=40.0,
        center_lon=29.0,
        built_2010_m2=100,
        built_2015_m2=150,
        built_2020_m2=300,
        cagr_2010_2015_pct=8.0,
        cagr_2015_2020_pct=14.0,
        acceleration_pp_per_year=acceleration,
        occupied_share_acceleration_pp=5.0,
        signal="accelerating",
    )


def _terrain(cell_id, p90):
    return TerrainScanRecord(
        cell_id=cell_id,
        center_lat=40.0,
        center_lon=29.0,
        mean_elevation_m=100,
        min_elevation_m=90,
        max_elevation_m=120,
        mean_slope_deg=3,
        p90_slope_deg=p90,
        max_slope_deg=20,
        valid_pixels=100,
        dem_instance="COPERNICUS_90",
        cache_hit=False,
    )


def test_funnel_drops_steep_and_hard_veto_cells():
    urban = [_urban("A", 4.0), _urban("B", 3.0), _urban("C", 2.0)]
    terrain = [_terrain("A", 5.0), _terrain("B", 20.0), _terrain("C", 4.0)]
    hazards = [
        CellHazardSummary(
            cell_id="C",
            finding_count=1,
            hard_veto=True,
            hard_veto_categories=("flood",),
            max_severity=HazardSeverity.CRITICAL,
            max_overlap_ratio=0.5,
            nearest_hazard_km=0.0,
        )
    ]

    result = build_candidate_funnel(
        urban,
        terrain_records=terrain,
        hazard_summaries=hazards,
        policy=CandidatePolicy(
            urban_top_n=3,
            max_p90_slope_deg=12,
            require_catalyst=False,
        ),
    )

    status = {row.cell_id: row.status for row in result}
    assert status["A"] == "PASS_WITH_GAPS"
    assert status["B"] == "DROP"
    assert status["C"] == "DROP"
    assert [row.cell_id for row in surviving_candidates(result)] == ["A"]


def test_unknown_terrain_does_not_fake_low_risk():
    result = build_candidate_funnel(
        [_urban("A", 4.0)],
        policy=CandidatePolicy(urban_top_n=1),
    )
    assert result[0].status == "PASS_WITH_GAPS"
    assert "terrain_unknown" in result[0].reasons
    assert "hazard_unknown" in result[0].reasons
