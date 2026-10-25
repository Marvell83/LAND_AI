from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Iterable, Protocol

from .geometry import bbox_for_cell
from .grid import GridCell
from .providers.sentinel_surface import (
    SurfaceChange,
    SurfaceSummary,
    compare_surface,
)


class SurfaceClient(Protocol):
    def summary(
        self,
        bbox: tuple[float, float, float, float],
        start_date: date,
        end_date: date,
        *,
        width: int = 128,
        height: int = 128,
        max_cloud_coverage: int = 30,
    ) -> SurfaceSummary:
        ...


@dataclass(frozen=True)
class SentinelChangeRecord:
    cell_id: str
    center_lat: float
    center_lon: float
    first_start: date
    first_end: date
    second_start: date
    second_end: date
    first_ndvi: float | None
    second_ndvi: float | None
    delta_ndvi: float | None
    first_ndbi: float | None
    second_ndbi: float | None
    delta_ndbi: float | None
    first_bsi: float | None
    second_bsi: float | None
    delta_bsi: float | None
    first_vegetation_share: float
    second_vegetation_share: float
    delta_vegetation_share_pp: float
    first_bare_soil_share: float
    second_bare_soil_share: float
    delta_bare_soil_share_pp: float
    first_water_share: float
    second_water_share: float
    delta_water_share_pp: float
    first_valid_land_pixels: int
    second_valid_land_pixels: int
    cache_hit: bool


def _cache_key(
    cell: GridCell,
    *,
    first_start: date,
    first_end: date,
    second_start: date,
    second_end: date,
    width: int,
    height: int,
    max_cloud_coverage: int,
) -> str:
    raw = "|".join(
        [
            cell.cell_id,
            f"{cell.center_lat:.6f}",
            f"{cell.center_lon:.6f}",
            f"{cell.size_km:.3f}",
            first_start.isoformat(),
            first_end.isoformat(),
            second_start.isoformat(),
            second_end.isoformat(),
            str(width),
            str(height),
            str(max_cloud_coverage),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _record_from_change(
    cell: GridCell,
    change: SurfaceChange,
    *,
    cache_hit: bool,
) -> SentinelChangeRecord:
    first = change.first
    second = change.second
    return SentinelChangeRecord(
        cell_id=cell.cell_id,
        center_lat=cell.center_lat,
        center_lon=cell.center_lon,
        first_start=first.start_date,
        first_end=first.end_date,
        second_start=second.start_date,
        second_end=second.end_date,
        first_ndvi=first.median_ndvi,
        second_ndvi=second.median_ndvi,
        delta_ndvi=change.delta_ndvi,
        first_ndbi=first.median_ndbi,
        second_ndbi=second.median_ndbi,
        delta_ndbi=change.delta_ndbi,
        first_bsi=first.median_bsi,
        second_bsi=second.median_bsi,
        delta_bsi=change.delta_bsi,
        first_vegetation_share=first.vegetation_share,
        second_vegetation_share=second.vegetation_share,
        delta_vegetation_share_pp=change.delta_vegetation_share_pp,
        first_bare_soil_share=first.bare_soil_share,
        second_bare_soil_share=second.bare_soil_share,
        delta_bare_soil_share_pp=change.delta_bare_soil_share_pp,
        first_water_share=first.water_share,
        second_water_share=second.water_share,
        delta_water_share_pp=change.delta_water_share_pp,
        first_valid_land_pixels=first.valid_land_pixels,
        second_valid_land_pixels=second.valid_land_pixels,
        cache_hit=cache_hit,
    )


def _summary_to_json(summary: SurfaceSummary) -> dict:
    data = asdict(summary)
    data["start_date"] = summary.start_date.isoformat()
    data["end_date"] = summary.end_date.isoformat()
    return data


def _summary_from_json(payload: dict) -> SurfaceSummary:
    return SurfaceSummary(
        start_date=date.fromisoformat(payload["start_date"]),
        end_date=date.fromisoformat(payload["end_date"]),
        median_ndvi=payload.get("median_ndvi"),
        median_ndbi=payload.get("median_ndbi"),
        median_bsi=payload.get("median_bsi"),
        vegetation_share=float(payload["vegetation_share"]),
        bare_soil_share=float(payload["bare_soil_share"]),
        water_share=float(payload["water_share"]),
        valid_land_pixels=int(payload["valid_land_pixels"]),
        total_valid_pixels=int(payload["total_valid_pixels"]),
    )


def _load_cache(path: Path) -> SurfaceChange | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return compare_surface(
            _summary_from_json(payload["first"]),
            _summary_from_json(payload["second"]),
        )
    except Exception:
        return None


def _save_cache(path: Path, change: SurfaceChange) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "first": _summary_to_json(change.first),
                "second": _summary_to_json(change.second),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def scan_sentinel_change(
    cells: Iterable[GridCell],
    client: SurfaceClient,
    *,
    first_start: date,
    first_end: date,
    second_start: date,
    second_end: date,
    cache_dir: str | Path = "data/cache/sentinel",
    width: int = 128,
    height: int = 128,
    max_cloud_coverage: int = 30,
    use_cache: bool = True,
) -> list[SentinelChangeRecord]:
    if first_start > first_end:
        raise ValueError("first_start cannot be after first_end")
    if second_start > second_end:
        raise ValueError("second_start cannot be after second_end")

    records: list[SentinelChangeRecord] = []
    cache_dir = Path(cache_dir)

    for cell in cells:
        key = _cache_key(
            cell,
            first_start=first_start,
            first_end=first_end,
            second_start=second_start,
            second_end=second_end,
            width=width,
            height=height,
            max_cloud_coverage=max_cloud_coverage,
        )
        path = cache_dir / f"{key}.json"
        change = _load_cache(path) if use_cache else None
        cache_hit = change is not None

        if change is None:
            bbox = bbox_for_cell(cell)
            first = client.summary(
                bbox,
                first_start,
                first_end,
                width=width,
                height=height,
                max_cloud_coverage=max_cloud_coverage,
            )
            second = client.summary(
                bbox,
                second_start,
                second_end,
                width=width,
                height=height,
                max_cloud_coverage=max_cloud_coverage,
            )
            change = compare_surface(first, second)
            if use_cache:
                _save_cache(path, change)

        records.append(
            _record_from_change(
                cell,
                change,
                cache_hit=cache_hit,
            )
        )

    return records
