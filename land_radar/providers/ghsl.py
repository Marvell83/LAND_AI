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


def discover_epoch_file(directory: str | Path, epoch: int) -> Path | None:
    directory = Path(directory)
    if not directory.exists():
        return None

    matches = sorted(
        p for p in directory.rglob("*.tif")
        if epoch_from_filename(p) == epoch
    )
    return matches[0] if matches else None


def _summarize_dataset(
    src,
    source_path: str | Path,
    bbox_wgs84: tuple[float, float, float, float],
) -> BuiltUpSummary:
    if src.crs is None:
        raise GHSLProviderError("GHSL raster has no CRS metadata")

    min_lon, min_lat, max_lon, max_lat = bbox_wgs84
    if str(src.crs).upper() in {"EPSG:4326", "OGC:CRS84"}:
        left, bottom, right, top = min_lon, min_lat, max_lon, max_lat
    else:
        left, bottom, right, top = transform_bounds(
            "EPSG:4326",
            src.crs,
            min_lon,
            min_lat,
            max_lon,
            max_lat,
            densify_pts=21,
        )

    window = from_bounds(left, bottom, right, top, transform=src.transform)
    data = src.read(1, window=window, masked=True, boundless=True)

    if data.size == 0:
        raise GHSLProviderError("Requested bbox returned no raster pixels")

    compressed = data.compressed().astype("float64")
    if compressed.size == 0:
        raise GHSLProviderError("Requested bbox contains only NoData pixels")

    total = float(np.sum(compressed))
    mean = float(np.mean(compressed))
    occupied_share = float(np.count_nonzero(compressed > 0) / compressed.size)

    return BuiltUpSummary(
        epoch=epoch_from_filename(source_path),
        total_built_up_m2=round(total, 2),
        mean_built_up_m2_per_pixel=round(mean, 4),
        occupied_pixel_share=round(occupied_share, 6),
        valid_pixels=int(compressed.size),
        source_path=str(source_path),
    )


def summarize_built_up(
    raster_path: str | Path,
    bbox_wgs84: tuple[float, float, float, float],
) -> BuiltUpSummary:
    """Summarize a GHSL built-up raster inside a WGS84 bbox.

    GHSL GHS-BUILT-S pixel values represent square metres of built-up surface.
    The function supports source rasters in any CRS that rasterio can transform.
    """
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
    """Open multiple GHSL epochs once and reuse them across many grid cells."""

    def __init__(self, directory: str | Path, epochs: Iterable[int] = (2010, 2015, 2020)):
        self.directory = Path(directory)
        self.epochs = tuple(int(epoch) for epoch in epochs)
        self.paths: dict[int, Path] = {}
        self.datasets: dict[int, object] = {}
        self._stack: ExitStack | None = None

        for epoch in self.epochs:
            path = discover_epoch_file(self.directory, epoch)
            if path is not None:
                self.paths[epoch] = path

    @property
    def missing_epochs(self) -> tuple[int, ...]:
        return tuple(epoch for epoch in self.epochs if epoch not in self.paths)

    def __enter__(self) -> "GHSLRasterStack":
        self._stack = ExitStack()
        try:
            for epoch, path in self.paths.items():
                self.datasets[epoch] = self._stack.enter_context(rasterio.open(path))
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
            raise GHSLProviderError("GHSLRasterStack must be used as a context manager")
        if epoch not in self.datasets:
            raise GHSLProviderError(f"GHSL epoch {epoch} is not available")

        try:
            return _summarize_dataset(
                self.datasets[epoch],
                self.paths[epoch],
                bbox_wgs84,
            )
        except GHSLProviderError:
            raise
        except Exception as exc:
            raise GHSLProviderError(f"Failed to read GHSL epoch {epoch}: {exc}") from exc


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
