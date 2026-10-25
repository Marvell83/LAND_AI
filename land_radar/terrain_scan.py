from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Iterable, Protocol

from .geometry import bbox_for_cell
from .grid import GridCell
from .providers.copernicus_dem import TerrainSummary


class TerrainClient(Protocol):
    def terrain_summary(
        self,
        bbox: tuple[float, float, float, float],
        *,
        width: int = 96,
        height: int = 96,
        dem_instance: str = "COPERNICUS_90",
    ) -> TerrainSummary:
        ...


@dataclass(frozen=True)
class TerrainScanRecord:
    cell_id: str
    center_lat: float
    center_lon: float
    mean_elevation_m: float
    min_elevation_m: float
    max_elevation_m: float
    mean_slope_deg: float
    p90_slope_deg: float
    max_slope_deg: float
    valid_pixels: int
    dem_instance: str
    cache_hit: bool


def _cache_key(
    cell: GridCell,
    *,
    width: int,
    height: int,
    dem_instance: str,
) -> str:
    raw = (
        f"{cell.cell_id}|{cell.center_lat:.6f}|{cell.center_lon:.6f}|"
        f"{cell.size_km:.3f}|{width}|{height}|{dem_instance}"
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _cache_path(
    cache_dir: str | Path,
    key: str,
) -> Path:
    return Path(cache_dir) / f"{key}.json"


def _load_cached(path: Path) -> TerrainSummary | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return TerrainSummary(**payload)
    except Exception:
        return None


def _save_cached(path: Path, summary: TerrainSummary) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(summary), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def scan_terrain(
    cells: Iterable[GridCell],
    client: TerrainClient,
    *,
    limit: int | None = None,
    cache_dir: str | Path = "data/cache/terrain",
    width: int = 96,
    height: int = 96,
    dem_instance: str = "COPERNICUS_90",
    use_cache: bool = True,
) -> list[TerrainScanRecord]:
    selected = list(cells)
    if limit is not None:
        if limit <= 0:
            raise ValueError("limit must be positive")
        selected = selected[:limit]

    records: list[TerrainScanRecord] = []
    for cell in selected:
        key = _cache_key(
            cell,
            width=width,
            height=height,
            dem_instance=dem_instance,
        )
        path = _cache_path(cache_dir, key)
        summary = _load_cached(path) if use_cache else None
        cache_hit = summary is not None

        if summary is None:
            summary = client.terrain_summary(
                bbox_for_cell(cell),
                width=width,
                height=height,
                dem_instance=dem_instance,
            )
            if use_cache:
                _save_cached(path, summary)

        records.append(
            TerrainScanRecord(
                cell_id=cell.cell_id,
                center_lat=cell.center_lat,
                center_lon=cell.center_lon,
                mean_elevation_m=summary.mean_elevation_m,
                min_elevation_m=summary.min_elevation_m,
                max_elevation_m=summary.max_elevation_m,
                mean_slope_deg=summary.mean_slope_deg,
                p90_slope_deg=summary.p90_slope_deg,
                max_slope_deg=summary.max_slope_deg,
                valid_pixels=summary.valid_pixels,
                dem_instance=summary.dem_instance,
                cache_hit=cache_hit,
            )
        )

    return records


def rank_by_flatness(
    records: Iterable[TerrainScanRecord],
) -> list[TerrainScanRecord]:
    """Physical terrain ordering only; not an investment ranking."""
    return sorted(
        records,
        key=lambda record: (
            record.p90_slope_deg,
            record.mean_slope_deg,
            record.max_slope_deg,
            record.cell_id,
        ),
    )
