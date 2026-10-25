from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import os
from typing import Any

from ..hazard import HazardGeometry, HazardSeverity
from .ogc_wfs import OGCWFSError, query_wfs_geojson


class MTALandslideConfigError(ValueError):
    pass


@dataclass(frozen=True)
class MTALandslideConfig:
    service_url: str
    type_name: str


def resolve_mta_landslide_config(
    env: dict[str, str] | None = None,
) -> MTALandslideConfig | None:
    source = env or os.environ
    url = str(source.get("MTA_LANDSLIDE_WFS_URL") or "").strip()
    type_name = str(source.get("MTA_LANDSLIDE_TYPENAME") or "").strip()

    if not url and not type_name:
        return None
    if not url or not type_name:
        raise MTALandslideConfigError(
            "MTA_LANDSLIDE_WFS_URL and MTA_LANDSLIDE_TYPENAME must be set together"
        )
    if not url.startswith("https://"):
        raise MTALandslideConfigError("MTA landslide WFS URL must use HTTPS")

    return MTALandslideConfig(
        service_url=url,
        type_name=type_name,
    )


def _feature_id(feature: dict[str, Any], fallback: int) -> str:
    props = feature.get("properties") or {}
    for key in ("OBJECTID", "objectid", "FID", "fid", "id"):
        if props.get(key) is not None:
            return str(props[key])
    if feature.get("id") is not None:
        return str(feature["id"])
    return str(fallback)


def feature_to_landslide_hazard(
    feature: dict[str, Any],
    *,
    index: int,
    source_url: str,
    observed_date: date | None = None,
) -> HazardGeometry | None:
    geometry = feature.get("geometry")
    if not geometry:
        return None

    props = feature.get("properties") or {}
    details = []
    for key in (
        "TIP", "TYPE", "DURUM", "STATUS", "SINIF", "CLASS",
        "AKTIF", "ACTIVE", "ADI", "NAME",
    ):
        value = props.get(key)
        if value not in (None, ""):
            details.append(f"{key}={value}")

    note = (
        "MTA/TUCBS heyelan envanter geometrisi. Envanter kaydı, güncel "
        "heyelan duyarlılığı veya parsel bazlı yapılaşma yasağı değildir."
    )
    if details:
        note += " " + "; ".join(details)

    return HazardGeometry(
        hazard_id=f"mta:landslide:{_feature_id(feature, index)}",
        category="landslide_inventory",
        severity=HazardSeverity.UNKNOWN,
        geometry_geojson=geometry,
        source="MTA / TUCBS Heyelan Envanteri WFS",
        observed_date=observed_date or date.today(),
        source_url=source_url,
        hard_veto=False,
        confidence=90.0,
        note=note,
    )


def fetch_landslide_hazards(
    bbox: tuple[float, float, float, float],
    config: MTALandslideConfig,
) -> list[HazardGeometry]:
    result = query_wfs_geojson(
        config.service_url,
        config.type_name,
        bbox,
    )
    hazards: list[HazardGeometry] = []
    for index, feature in enumerate(result.features, start=1):
        hazard = feature_to_landslide_hazard(
            feature,
            index=index,
            source_url=config.service_url,
        )
        if hazard is not None:
            hazards.append(hazard)
    return hazards


__all__ = [
    "MTALandslideConfig",
    "MTALandslideConfigError",
    "OGCWFSError",
    "resolve_mta_landslide_config",
    "fetch_landslide_hazards",
    "feature_to_landslide_hazard",
]
