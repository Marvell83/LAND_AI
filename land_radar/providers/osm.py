from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import requests


DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
MAJOR_HIGHWAYS = {"motorway", "trunk", "primary", "secondary"}


class OSMProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class RoadSummary:
    total_highway_ways: int
    major_highway_ways: int
    nearest_major_way_center_km: float | None
    highway_classes: tuple[tuple[str, int], ...]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = p2 - p1
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def build_highway_query(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> str:
    """Build bounded Overpass QL. Overpass bbox order is south, west, north, east."""
    return (
        "[out:json][timeout:25];\n"
        f"way[\"highway\"]({min_lat},{min_lon},{max_lat},{max_lon});\n"
        "out center tags;"
    )


def parse_road_summary(payload: dict[str, Any], center_lat: float, center_lon: float) -> RoadSummary:
    classes: dict[str, int] = {}
    major_distances: list[float] = []
    total = 0
    major = 0

    for element in payload.get("elements", []):
        if element.get("type") != "way":
            continue
        highway = (element.get("tags") or {}).get("highway")
        if not highway:
            continue

        total += 1
        classes[highway] = classes.get(highway, 0) + 1

        if highway in MAJOR_HIGHWAYS:
            major += 1
            center = element.get("center") or {}
            lat = center.get("lat")
            lon = center.get("lon")
            if lat is not None and lon is not None:
                major_distances.append(_haversine_km(center_lat, center_lon, float(lat), float(lon)))

    return RoadSummary(
        total_highway_ways=total,
        major_highway_ways=major,
        nearest_major_way_center_km=round(min(major_distances), 3) if major_distances else None,
        highway_classes=tuple(sorted(classes.items(), key=lambda item: (-item[1], item[0]))),
    )


def fetch_road_summary(
    bbox: tuple[float, float, float, float],
    center_lat: float,
    center_lon: float,
    *,
    endpoint: str = DEFAULT_OVERPASS_URL,
    timeout: float = 35.0,
    session: requests.Session | None = None,
) -> RoadSummary:
    min_lon, min_lat, max_lon, max_lat = bbox
    query = build_highway_query(min_lon, min_lat, max_lon, max_lat)
    client = session or requests.Session()

    try:
        response = client.post(
            endpoint,
            data={"data": query},
            timeout=timeout,
            headers={"User-Agent": "LAND-RADAR/0.2 research-probe"},
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise OSMProviderError(f"OSM/Overpass query failed: {exc}") from exc

    return parse_road_summary(payload, center_lat=center_lat, center_lon=center_lon)
