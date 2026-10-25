from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .spatial.catalyst_geometry import CatalystSpatialLink
from .spatial.hazard_overlap import CellHazardSummary
from .terrain_scan import TerrainScanRecord
from .urban_scan import UrbanScanRecord


@dataclass(frozen=True)
class CandidatePolicy:
    urban_top_n: int = 100
    max_p90_slope_deg: float | None = 12.0
    max_catalyst_distance_km: float | None = 20.0
    require_catalyst: bool = False
    exclude_hard_veto: bool = True

    def __post_init__(self) -> None:
        if self.urban_top_n <= 0:
            raise ValueError("urban_top_n must be positive")
        if self.max_p90_slope_deg is not None and self.max_p90_slope_deg < 0:
            raise ValueError("max_p90_slope_deg cannot be negative")
        if (
            self.max_catalyst_distance_km is not None
            and self.max_catalyst_distance_km < 0
        ):
            raise ValueError("max_catalyst_distance_km cannot be negative")


@dataclass(frozen=True)
class CandidateRecord:
    cell_id: str
    center_lat: float
    center_lon: float
    urban_rank: int
    acceleration_pp_per_year: float | None
    cagr_2015_2020_pct: float | None
    p90_slope_deg: float | None
    nearest_catalyst_km: float | None
    catalyst_stage_max: int | None
    hard_veto: bool
    max_hazard_severity: int | None
    status: str
    reasons: tuple[str, ...]


def _urban_order(records: Iterable[UrbanScanRecord]) -> list[UrbanScanRecord]:
    measurable = [
        record
        for record in records
        if record.acceleration_pp_per_year is not None
    ]
    return sorted(
        measurable,
        key=lambda record: (
            record.acceleration_pp_per_year,
            record.cagr_2015_2020_pct
            if record.cagr_2015_2020_pct is not None
            else float("-inf"),
            record.built_2020_m2,
        ),
        reverse=True,
    )


def build_candidate_funnel(
    urban_records: Iterable[UrbanScanRecord],
    *,
    terrain_records: Iterable[TerrainScanRecord] = (),
    hazard_summaries: Iterable[CellHazardSummary] = (),
    catalyst_links: Iterable[CatalystSpatialLink] = (),
    policy: CandidatePolicy = CandidatePolicy(),
) -> list[CandidateRecord]:
    """Build a transparent research funnel without a magic opportunity score."""
    urban_ranked = _urban_order(urban_records)[: policy.urban_top_n]
    terrain_by_cell: Mapping[str, TerrainScanRecord] = {
        record.cell_id: record
        for record in terrain_records
    }
    hazard_by_cell: Mapping[str, CellHazardSummary] = {
        summary.cell_id: summary
        for summary in hazard_summaries
    }

    catalyst_by_cell: dict[str, list[CatalystSpatialLink]] = {}
    for link in catalyst_links:
        catalyst_by_cell.setdefault(link.cell_id, []).append(link)

    output: list[CandidateRecord] = []

    for rank, urban in enumerate(urban_ranked, start=1):
        reasons: list[str] = []
        status = "PASS"

        terrain = terrain_by_cell.get(urban.cell_id)
        p90 = terrain.p90_slope_deg if terrain else None

        if policy.max_p90_slope_deg is not None:
            if p90 is None:
                reasons.append("terrain_unknown")
            elif p90 > policy.max_p90_slope_deg:
                status = "DROP"
                reasons.append("slope_above_limit")

        hazard = hazard_by_cell.get(urban.cell_id)
        hard_veto = bool(hazard.hard_veto) if hazard else False
        max_hazard_severity = (
            int(hazard.max_severity)
            if hazard is not None
            else None
        )
        if policy.exclude_hard_veto and hard_veto:
            status = "DROP"
            reasons.append("hard_veto_hazard")

        links = catalyst_by_cell.get(urban.cell_id, [])
        nearest_catalyst = None
        max_stage = None
        if links:
            nearest_catalyst = min(link.distance_km for link in links)
            max_stage = max(link.catalyst_stage for link in links)

        if policy.max_catalyst_distance_km is not None:
            eligible_links = [
                link
                for link in links
                if link.distance_km <= policy.max_catalyst_distance_km
            ]
        else:
            eligible_links = list(links)

        if policy.require_catalyst and not eligible_links:
            status = "DROP"
            reasons.append("no_catalyst_in_range")
        elif not links:
            reasons.append("catalyst_unknown")

        if status == "PASS" and reasons:
            status = "PASS_WITH_GAPS"

        output.append(
            CandidateRecord(
                cell_id=urban.cell_id,
                center_lat=urban.center_lat,
                center_lon=urban.center_lon,
                urban_rank=rank,
                acceleration_pp_per_year=urban.acceleration_pp_per_year,
                cagr_2015_2020_pct=urban.cagr_2015_2020_pct,
                p90_slope_deg=p90,
                nearest_catalyst_km=nearest_catalyst,
                catalyst_stage_max=max_stage,
                hard_veto=hard_veto,
                max_hazard_severity=max_hazard_severity,
                status=status,
                reasons=tuple(reasons),
            )
        )

    return output


def surviving_candidates(
    records: Iterable[CandidateRecord],
) -> list[CandidateRecord]:
    return [
        record
        for record in records
        if record.status in {"PASS", "PASS_WITH_GAPS"}
    ]
