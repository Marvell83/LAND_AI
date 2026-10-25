from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from statistics import median
from typing import Any

import requests


STAC_SEARCH_URL = "https://stac.dataspace.copernicus.eu/v1/search"
SENTINEL_2_L2A = "sentinel-2-l2a"


class CopernicusSTACError(RuntimeError):
    pass


@dataclass(frozen=True)
class Scene:
    item_id: str
    datetime: str | None
    cloud_cover: float | None


@dataclass(frozen=True)
class SceneSummary:
    count: int
    min_cloud_cover: float | None
    median_cloud_cover: float | None
    scenes: tuple[Scene, ...]


def _iso_day(value: date) -> str:
    return value.isoformat() + "T00:00:00Z"


def build_search_payload(
    bbox: tuple[float, float, float, float],
    start_date: date,
    end_date: date,
    *,
    max_cloud_cover: float = 30.0,
    limit: int = 20,
) -> dict[str, Any]:
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")
    if not 0 <= max_cloud_cover <= 100:
        raise ValueError("max_cloud_cover must be between 0 and 100")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")

    return {
        "collections": [SENTINEL_2_L2A],
        "bbox": list(bbox),
        "datetime": f"{_iso_day(start_date)}/{_iso_day(end_date)}",
        "query": {"eo:cloud_cover": {"lte": float(max_cloud_cover)}},
        "limit": int(limit),
        "fields": {
            "include": ["id", "properties.datetime", "properties.eo:cloud_cover"],
            "exclude": ["geometry", "assets", "links"],
        },
    }


def parse_scene_summary(payload: dict[str, Any]) -> SceneSummary:
    scenes: list[Scene] = []
    clouds: list[float] = []

    for feature in payload.get("features", []):
        props = feature.get("properties") or {}
        cloud = props.get("eo:cloud_cover")
        cloud_value = float(cloud) if cloud is not None else None
        if cloud_value is not None:
            clouds.append(cloud_value)
        scenes.append(
            Scene(
                item_id=str(feature.get("id", "")),
                datetime=props.get("datetime"),
                cloud_cover=cloud_value,
            )
        )

    return SceneSummary(
        count=len(scenes),
        min_cloud_cover=round(min(clouds), 2) if clouds else None,
        median_cloud_cover=round(float(median(clouds)), 2) if clouds else None,
        scenes=tuple(scenes),
    )


def search_sentinel2_l2a(
    bbox: tuple[float, float, float, float],
    start_date: date,
    end_date: date,
    *,
    max_cloud_cover: float = 30.0,
    limit: int = 20,
    endpoint: str = STAC_SEARCH_URL,
    timeout: float = 35.0,
    session: requests.Session | None = None,
) -> SceneSummary:
    payload = build_search_payload(
        bbox,
        start_date,
        end_date,
        max_cloud_cover=max_cloud_cover,
        limit=limit,
    )
    client = session or requests.Session()

    try:
        response = client.post(
            endpoint,
            json=payload,
            timeout=timeout,
            headers={
                "User-Agent": "LAND-RADAR/0.2 research-probe",
                "Accept": "application/geo+json, application/json",
            },
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise CopernicusSTACError(f"Copernicus STAC query failed: {exc}") from exc

    return parse_scene_summary(data)
