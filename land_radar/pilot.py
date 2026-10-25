from __future__ import annotations

from dataclasses import dataclass

from .grid import GridCell, generate_rectangular_grid


@dataclass(frozen=True)
class PilotArea:
    name: str
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float
    note: str


SAKARYA_CANAKKALE = PilotArea(
    name="Sakarya → Bursa/Balıkesir → Çanakkale",
    min_lat=39.35,
    min_lon=26.00,
    max_lat=41.35,
    max_lon=31.00,
    note=(
        "V0 araştırma zarfı. İl/idari sınır değildir; ilk taramada "
        "geniş ekonomik koridoru kapsamak için bilerek kaba tutulmuştur."
    ),
)


def build_pilot_grid(cell_km: float = 5.0) -> list[GridCell]:
    p = SAKARYA_CANAKKALE
    return generate_rectangular_grid(
        p.min_lat,
        p.min_lon,
        p.max_lat,
        p.max_lon,
        cell_km=cell_km,
    )
