from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .providers.ghsl import discover_epoch_files


@dataclass(frozen=True)
class ReadinessItem:
    key: str
    status: str
    required: bool
    detail: str


@dataclass(frozen=True)
class ReadinessReport:
    items: tuple[ReadinessItem, ...]

    @property
    def required_ready(self) -> bool:
        return all(
            item.status == "READY"
            for item in self.items
            if item.required
        )

    @property
    def ready_count(self) -> int:
        return sum(item.status == "READY" for item in self.items)


def check_data_readiness(
    *,
    ghsl_dir: str | Path = "data/raw/ghsl",
    ghsl_epochs: Iterable[int] = (2010, 2015, 2020),
    cdse_credentials_available: bool = False,
    hazard_registry_path: str | Path = "data/processed/hazard_registry.geojson",
    geometry_registry_path: str | Path = "data/processed/geometry_registry.geojson",
    price_csv_path: str | Path = "data/processed/comparables.csv",
) -> ReadinessReport:
    items: list[ReadinessItem] = []

    ghsl_dir = Path(ghsl_dir)
    for epoch in ghsl_epochs:
        paths = discover_epoch_files(ghsl_dir, int(epoch))
        items.append(
            ReadinessItem(
                key=f"ghsl_{epoch}",
                status="READY" if paths else "MISSING",
                required=True,
                detail=(
                    f"{len(paths)} tile bulundu"
                    if paths
                    else f"{epoch} epoch GeoTIFF bulunamadı: {ghsl_dir}"
                ),
            )
        )

    items.append(
        ReadinessItem(
            key="cdse_oauth",
            status="READY" if cdse_credentials_available else "MISSING",
            required=False,
            detail=(
                "Copernicus DEM/Sentinel Process API hazır"
                if cdse_credentials_available
                else "CDSE_CLIENT_ID / CDSE_CLIENT_SECRET bulunamadı"
            ),
        )
    )

    optional_paths = (
        ("hazard_registry", Path(hazard_registry_path), "Resmî risk/hazard registry"),
        ("geometry_registry", Path(geometry_registry_path), "Katalizör geometry registry"),
        ("price_dataset", Path(price_csv_path), "Emsal fiyat CSV"),
    )
    for key, path, label in optional_paths:
        items.append(
            ReadinessItem(
                key=key,
                status="READY" if path.exists() else "OPTIONAL_MISSING",
                required=False,
                detail=(
                    f"{label}: {path}"
                    if path.exists()
                    else f"{label} henüz yok: {path}"
                ),
            )
        )

    return ReadinessReport(items=tuple(items))
