from land_radar.providers.ghsl import BuiltUpSummary
from land_radar.urban_growth import calculate_urban_growth


def _summary(epoch: int, total: float, share: float) -> BuiltUpSummary:
    return BuiltUpSummary(
        epoch=epoch,
        total_built_up_m2=total,
        mean_built_up_m2_per_pixel=0.0,
        occupied_pixel_share=share,
        valid_pixels=100,
        source_path=f"{epoch}.tif",
    )


def test_acceleration_detected():
    a = _summary(2010, 100.0, 0.10)
    b = _summary(2015, 150.0, 0.15)
    c = _summary(2020, 300.0, 0.30)

    result = calculate_urban_growth(a, b, c)

    assert result.first_period.percent_change == 50.0
    assert result.second_period.percent_change == 100.0
    assert result.acceleration_pp_per_year is not None
    assert result.acceleration_pp_per_year > 0
    assert result.signal == "accelerating"


def test_zero_base_does_not_fake_growth_rate():
    a = _summary(2010, 0.0, 0.00)
    b = _summary(2015, 10.0, 0.02)
    c = _summary(2020, 20.0, 0.04)

    result = calculate_urban_growth(a, b, c)

    assert result.first_period.percent_change is None
    assert result.acceleration_pp_per_year is None
    assert result.signal == "insufficient_base"
