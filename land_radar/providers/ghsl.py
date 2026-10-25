from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable

import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds


GHSL_EPOCH_RE = re.compile(r"_E(\d{4})_")


class GHSLProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class BuiltUpSummary:
    epoch: int | None
    total_built_up_m2: float
    mean_built_up_m2_per_pixel: float
    occupied_pixel_share: float
    valid_pixels: int
    source_path: str


@dataclass(frozen=True)
class BuiltUpChange:
    start_epoch: int | None
    end_epoch: int | None
    absolute_change_m2: float
    percent_change: float | None
    occupied_share_change_pp: float


def epoch_from_filename(path: str | Path) -> int | None:
    match = GHSL_EPOCH_RE.search(Path(path).name)
    return int(match.group(1)) if match else None


def discover_epoch_files(directory: str | Path, epoch: int) -> tuple[Path, ...]:
    """Return every GeoTIFF tile for the requested GHSL epoch."""
    directory = Path(directory)
    if not directory.exists():
        return tuple()

    return tuple(
        sorted(
            p
            for p in directory.rglob("*.tif")
            if epoch_from_filename(p) == epoch
        )
    )


def discover_epoch_file(directory: str | Path, epoch: int) -> Path | None:
    """Backward-compatible helper returning the first matching tile."""
    matches = discover_epoch_files(directory, epoch)
    return matches[0] if matches else None


def _bbox_in_source_crs(
    src,
    bbox_wgs84: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    if src.crs is None:
        raise GHSLProviderError("GHSL raster has no CRS metadata")

    min_lon, min_lat, max_lon, max_lat = bbox_wgs84
    if str(src.crs).upper() in {"EPSG:4326", "OGC:CRS84"}:
        return min_lon, min_lat, max_lon, max_lat

    return transform_bounds(
        "EPSG:4326",
        src.crs,
        min_lon,
        min_lat,
        max_lon,
        max_lat,
        densify_pts=21,
    )


def _bounds_intersect(
    left: float,
    bottom: float,
    right: float,
    top: float,
    src,
) -> bool:
    bounds = src.bounds
    return not (
        right <= bounds.left
        or left >= bounds.right
        or top <= bounds.bottom
        or bottom >= bounds.top
    )


def _read_values(
    src,
    bbox_wgs84: tuple[float, float, float, float],
) -> np.ndarray:
    left, bottom, right, top = _bbox_in_source_crs(src, bbox_wgs84)

    if not _bounds_intersect(left, bottom, right, top, src):
        return np.array([], dtype="float64")

    clipped_left = max(left, src.bounds.left)
    clipped_bottom = max(bottom, src.bounds.bottom)
    clipped_right = min(right, src.bounds.right)
    clipped_top = min(top, src.bounds.top)

    if clipped_left >= clipped_right or clipped_bottom >= clipped_top:
        return np.array([], dtype="float64")

    window = from_bounds(
        clipped_left,
        clipped_bottom,
        clipped_right,
        clipped_top,
        transform=src.transform,
    )
    data = src.read(1, window=window, masked=True, boundless=False)

    if data.size == 0:
        return np.array([], dtype="float64")

    return data.compressed().astype("float64")


def _summary_from_values(
    values: np.ndarray,
    *,
    epoch: int | None,
    source_path: str,
) -> BuiltUpSummary:
    if values.size == 0:
        raise GHSLProviderError("Requested bbox contains no valid GHSL pixels")

    total = float(np.sum(values))
    mean = float(np.mean(values))
    occupied_share = float(np.count_nonzero(values > 0) / values.size)

    return BuiltUpSummary(
        epoch=epoch,
        total_built_up_m2=round(total, 2),
        mean_built_up_m2_per_pixel=round(mean, 4),
        occupied_pixel_share=round(occupied_share, 6),
        valid_pixels=int(values.size),
        source_path=source_path,
    )


def _summarize_dataset(
    src,
    source_path: str | Path,
    bbox_wgs84: tuple[float, float, float, float],
) -> BuiltUpSummary:
    values = _read_values(src, bbox_wgs84)
    return _summary_from_values(
        values,
        epoch=epoch_from_filename(source_path),
        source_path=str(source_path),
    )


def summarize_built_up(
    raster_path: str | Path,
    bbox_wgs84: tuple[float, float, float, float],
) -> BuiltUpSummary:
    """Summarize a single GHSL built-up GeoTIFF inside a WGS84 bbox."""
    raster_path = Path(raster_path)
    if not raster_path.exists():
        raise GHSLProviderError(f"GHSL raster not found: {raster_path}")

    try:
        with rasterio.open(raster_path) as src:
            return _summarize_dataset(src, raster_path, bbox_wgs84)
    except GHSLProviderError:
        raise
    except Exception as exc:
        raise GHSLProviderError(f"Failed to read GHSL raster: {exc}") from exc


class GHSLRasterStack:
    """Open all GHSL tiles for multiple epochs once and reuse them across cells."""

    def __init__(
        self,
        directory: str | Path,
        epochs: Iterable[int] = (2010, 2015, 2020),
    ):
        self.directory = Path(directory)
        self.epochs = tuple(int(epoch) for epoch in epochs)
        self.paths: dict[int, tuple[Path, ...]] = {
            epoch: discover_epoch_files(self.directory, epoch)
            for epoch in self.epochs
        }
        self.datasets: dict[int, list[tuple[Path, object]]] = {}
        self._stack: ExitStack | None = None

    @property
    def missing_epochs(self) -> tuple[int, ...]:
        return tuple(
            epoch
            for epoch in self.epochs
            if not self.paths.get(epoch)
        )

    def __enter__(self) -> "GHSLRasterStack":
        self._stack = ExitStack()
        try:
            for epoch, paths in self.paths.items():
                opened: list[tuple[Path, object]] = []
                for path in paths:
                    dataset = self._stack.enter_context(rasterio.open(path))
                    opened.append((path, dataset))
                self.datasets[epoch] = opened
        except Exception:
            self._stack.close()
            self._stack = None
            self.datasets.clear()
            raise
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._stack is not None:
            self._stack.close()
        self._stack = None
        self.datasets.clear()

    def summarize(
        self,
        epoch: int,
        bbox_wgs84: tuple[float, float, float, float],
    ) -> BuiltUpSummary:
        if self._stack is None:
            raise GHSLProviderError(
                "GHSLRasterStack must be used as a context manager"
            )
        if epoch not in self.datasets or not self.datasets[epoch]:
            raise GHSLProviderError(f"GHSL epoch {epoch} is not available")

        values: list[np.ndarray] = []
        contributing_paths: list[str] = []

        try:
            for path, dataset in self.datasets[epoch]:
                tile_values = _read_values(dataset, bbox_wgs84)
                if tile_values.size == 0:
                    continue
                values.append(tile_values)
                contributing_paths.append(str(path))

            if not values:
                raise GHSLProviderError(
                    f"Requested bbox is not covered by loaded GHSL epoch {epoch} tiles"
                )

            combined = (
                values[0]
                if len(values) == 1
                else np.concatenate(values)
            )
            return _summary_from_values(
                combined,
                epoch=epoch,
                source_path=";".join(contributing_paths),
            )
        except GHSLProviderError:
            raise
        except Exception as exc:
            raise GHSLProviderError(
                f"Failed to read GHSL epoch {epoch}: {exc}"
            ) from exc


def compare_built_up(start: BuiltUpSummary, end: BuiltUpSummary) -> BuiltUpChange:
    absolute = end.total_built_up_m2 - start.total_built_up_m2
    percent = None
    if start.total_built_up_m2 > 0:
        percent = absolute / start.total_built_up_m2 * 100.0

    return BuiltUpChange(
        start_epoch=start.epoch,
        end_epoch=end.epoch,
        absolute_change_m2=round(absolute, 2),
        percent_change=round(percent, 3) if percent is not None else None,
        occupied_share_change_pp=round(
            (end.occupied_pixel_share - start.occupied_pixel_share) * 100.0,
            3,
        ),
    )
