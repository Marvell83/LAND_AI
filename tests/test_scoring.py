from land_radar.models import CellMetrics, HardRiskFlags, LandCell
from land_radar.scoring import score_cell


def test_hard_risk_blocks_cell():
    cell = LandCell(
        cell_id="X",
        center_lat=40.0,
        center_lon=29.0,
        metrics=CellMetrics(urban_pressure=90),
        hard_risks=HardRiskFlags(legal_restriction=True),
    )
    result = score_cell(cell)
    assert result.blocked is True
    assert result.research_priority_score is None


def test_no_price_means_no_priority_score():
    cell = LandCell(
        cell_id="X",
        center_lat=40.0,
        center_lon=29.0,
        metrics=CellMetrics(
            urban_pressure=80,
            development_acceleration=85,
            catalyst_maturity=70,
            story_maturity=65,
            physical_quality=75,
            mispricing=None,
            exit_demand=70,
            risk=20,
            confidence=80,
        ),
    )
    result = score_cell(cell)
    assert result.blocked is False
    assert result.transition_score is not None
    assert result.research_priority_score is None
    assert "mispricing" in result.missing_metrics


def test_complete_metrics_produce_bounded_priority():
    cell = LandCell(
        cell_id="X",
        center_lat=40.0,
        center_lon=29.0,
        metrics=CellMetrics(
            urban_pressure=80,
            development_acceleration=90,
            catalyst_maturity=75,
            story_maturity=70,
            physical_quality=80,
            mispricing=85,
            exit_demand=75,
            risk=15,
            confidence=90,
        ),
    )
    result = score_cell(cell)
    assert 0 <= result.research_priority_score <= 100
