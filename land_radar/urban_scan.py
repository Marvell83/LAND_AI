from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .geometry import bbox_for_cell
from .grid import GridCell
from .providers.ghsl import GHSLProviderError, GHSLRasterStack
from .urban_growth import calculate_urban_growth


@dataclass(frozen=True)
class UrbanScanRecord:
    cell_id: str
    center_lat: float
    center_lon: float
    built_2010_m2: float
    built_2015_m2: float
    built_2020_m2: float
    cagr_2010_2015_pct: float | None
    cagr_2015_2020_pct: float | None
    acceleration_pp_per_year: float | None
    occupied_share_acceleration_pp: float
    signal: str


def scan_grid_ghsl(
    cells: Iterable[GridCell],
    ghsl_directory: str | Path,
    *,
    limit: int | None = None,
) -> list[UrbanScanRecord]:
    selected = list(cells)
    if limit is not None:
        if limit <= 0:
            raise ValueError("limit must be positive")
        selected = selected[:limit]

    records: list[UrbanScanRecord] = []

    with GHSLRasterStack(ghsl_directory, epochs=(2010, 2015, 2020)) as stack:
        if stack.missing_epochs:
            missing = ", ".join(map(str, stack.missing_epochs))
            raise GHSLProviderError(f"Missing GHSL epochs required for scan: {missing}")

        for cell in selected:
            bbox = bbox_for_cell(cell)
            s2010 = stack.summarize(2010, bbox)
            s2015 = stack.summarize(2015, bbox)
            s2020 = stack.summarize(2020, bbox)
            growth = calculate_urban_growth(s2010, s2015, s2020)

            records.append(
                UrbanScanRecord(
                    cell_id=cell.cell_id,
                    center_lat=cell.center_lat,
                    center_lon=cell.center_lon,
                    built_2010_m2=s2010.total_built_up_m2,
                    built_2015_m2=s2015.total_built_up_m2,
                    built_2020_m2=s2020.total_built_up_m2,
                    cagr_2010_2015_pct=growth.first_period.annualized_growth_pct,
                    cagr_2015_2020_pct=growth.second_period.annualized_growth_pct,
                    acceleration_pp_per_year=growth.acceleration_pp_per_year,
                    occupied_share_acceleration_pp=growth.occupied_share_acceleration_pp,
                    signal=growth.signal,
                )
            )

    return records


def rank_accelerating(records: Iterable[UrbanScanRecord]) -> list[UrbanScanRecord]:
    """Rank only on measurable acceleration, never on investment attractiveness."""
    return sorted(
        records,
        key=lambda r: (
            r.acceleration_pp_per_year is not None,
            r.acceleration_pp_per_year if r.acceleration_pp_per_year is not None else float("-inf"),
            r.built_2020_m2,
        ),
        reverse=True,
    )
