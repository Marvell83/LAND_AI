from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InfluenceBand:
    code: str
    label: str
    max_distance_km: float | None


@dataclass(frozen=True)
class InfluenceProfile:
    """Context-only distance bands.

    These bands do NOT claim an economic effect and must not be interpreted as
    valuation weights. They only make spatial proximity explicit and are
    intentionally configurable per catalyst type.
    """

    name: str
    bands: tuple[InfluenceBand, ...]

    def __post_init__(self) -> None:
        finite = [
            band.max_distance_km
            for band in self.bands
            if band.max_distance_km is not None
        ]
        if any(value is None or value <= 0 for value in finite):
            raise ValueError("Finite influence distances must be positive")
        if finite != sorted(finite):
            raise ValueError("Influence bands must be ordered by distance")


DEFAULT_CONTEXT_PROFILE = InfluenceProfile(
    name="context-only",
    bands=(
        InfluenceBand("INTERSECTS", "Hücreyle kesişiyor", 0.0001),
        InfluenceBand("VERY_NEAR", "Çok yakın", 2.0),
        InfluenceBand("NEAR", "Yakın", 5.0),
        InfluenceBand("CORRIDOR", "Koridor bağlamı", 10.0),
        InfluenceBand("REGIONAL", "Bölgesel bağlam", 20.0),
        InfluenceBand("OUTSIDE", "Tanımlı bağlam dışında", None),
    ),
)


def classify_influence(
    distance_km: float,
    *,
    intersects_cell: bool = False,
    profile: InfluenceProfile = DEFAULT_CONTEXT_PROFILE,
) -> InfluenceBand:
    if distance_km < 0:
        raise ValueError("distance_km cannot be negative")

    if intersects_cell:
        for band in profile.bands:
            if band.code == "INTERSECTS":
                return band

    for band in profile.bands:
        if band.code == "INTERSECTS":
            continue
        if band.max_distance_km is None or distance_km <= band.max_distance_km:
            return band

    raise RuntimeError("Influence profile has no terminal band")
