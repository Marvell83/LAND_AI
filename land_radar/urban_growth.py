from __future__ import annotations

from dataclasses import dataclass

from .providers.ghsl import BuiltUpSummary


@dataclass(frozen=True)
class GrowthPeriod:
    start_epoch: int
    end_epoch: int
    absolute_change_m2: float
    percent_change: float | None
    annualized_growth_pct: float | None
    occupied_share_change_pp: float


@dataclass(frozen=True)
class UrbanGrowthMetrics:
    first_period: GrowthPeriod
    second_period: GrowthPeriod
    acceleration_pp_per_year: float | None
    occupied_share_acceleration_pp: float
    signal: str


def _period(start: BuiltUpSummary, end: BuiltUpSummary) -> GrowthPeriod:
    if start.epoch is None or end.epoch is None:
        raise ValueError("GHSL summaries must contain epochs")
    if end.epoch <= start.epoch:
        raise ValueError("end epoch must be after start epoch")

    years = end.epoch - start.epoch
    absolute = end.total_built_up_m2 - start.total_built_up_m2

    percent = None
    annualized = None
    if start.total_built_up_m2 > 0:
        percent = absolute / start.total_built_up_m2 * 100.0
        if end.total_built_up_m2 >= 0:
            ratio = end.total_built_up_m2 / start.total_built_up_m2
            annualized = (ratio ** (1.0 / years) - 1.0) * 100.0

    return GrowthPeriod(
        start_epoch=start.epoch,
        end_epoch=end.epoch,
        absolute_change_m2=round(absolute, 2),
        percent_change=round(percent, 3) if percent is not None else None,
        annualized_growth_pct=round(annualized, 3) if annualized is not None else None,
        occupied_share_change_pp=round(
            (end.occupied_pixel_share - start.occupied_pixel_share) * 100.0,
            3,
        ),
    )


def calculate_urban_growth(
    epoch_a: BuiltUpSummary,
    epoch_b: BuiltUpSummary,
    epoch_c: BuiltUpSummary,
) -> UrbanGrowthMetrics:
    """Compare two consecutive GHSL periods without inventing a 0-100 score."""
    first = _period(epoch_a, epoch_b)
    second = _period(epoch_b, epoch_c)

    acceleration = None
    if first.annualized_growth_pct is not None and second.annualized_growth_pct is not None:
        acceleration = second.annualized_growth_pct - first.annualized_growth_pct

    occupied_accel = second.occupied_share_change_pp - first.occupied_share_change_pp

    if acceleration is None:
        signal = "insufficient_base"
    elif acceleration > 0.5:
        signal = "accelerating"
    elif acceleration < -0.5:
        signal = "decelerating"
    else:
        signal = "stable"

    return UrbanGrowthMetrics(
        first_period=first,
        second_period=second,
        acceleration_pp_per_year=round(acceleration, 3) if acceleration is not None else None,
        occupied_share_acceleration_pp=round(occupied_accel, 3),
        signal=signal,
    )
