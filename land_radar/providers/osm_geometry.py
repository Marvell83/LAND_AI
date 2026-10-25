from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Any, Iterable

from shapely.geometry import LineString, MultiLineString, Point, Polygon, mapping
import requests

from ..spatial.geometry import GeometryEvidence


DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter"


class OSMGeometryProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class OSMGeometryFeature:
    osm_type: str
    osm_id: int
    name: str
    tags: dict[str, str]
    geometry_geojson: dict[str, Any]
    geometry_role: str
    confidence: float

    @property
    def feature_id(self) -> str:
        return f"osm:{self.osm_type}:{self.osm_id}"


def build_industrial_geometry_query(
    bbox: tuple[float, float, float, float],
) -> str:
    min_lon, min_lat, max_lon, max_lat = bbox
    south, west, north, east = min_lat, min_lon, max_lat, max_lon
    return (
        "[out:json][timeout:35];\n"
        "(\n"
        f'  way["landuse"="industrial"]["name"]({south},{west},{north},{east});\n'
        f'  relation["landuse"="industrial"]["name"]({south},{west},{north},{east});\n'
        f'  way["industrial"]["name"]({south},{west},{north},{east});\n'
        f'  relation["industrial"]["name"]({south},{west},{north},{east});\n'
        ");\n"
        "out body geom;"
    )


def build_rail_geometry_query(
    bbox: tuple[float, float, float, float],
) -> str:
    min_lon, min_lat, max_lon, max_lat = bbox
    south, west, north, east = min_lat, min_lon, max_lat, max_lon
    return (
        "[out:json][timeout:35];\n"
        "(\n"
        f'  way["railway"~"^(rail|construction|proposed)$"]({south},{west},{north},{east});\n'
        f'  relation["railway"~"^(rail|construction|proposed)$"]({south},{west},{north},{east});\n'
        ");\n"
        "out body geom;"
    )


def _coordinates_from_geometry(items: Iterable[dict[str, Any]]) -> list[tuple[float, float]]:
    coords: list[tuple[float, float]] = []
    for item in items:
        lat = item.get("lat")
        lon = item.get("lon")
        if lat is None or lon is None:
            continue
        coords.append((float(lon), float(lat)))
    return coords


def _way_geometry(element: dict[str, Any]):
    coords = _coordinates_from_geometry(element.get("geometry") or [])
    if len(coords) < 2:
        return None, "missing_geometry", 0.0

    if len(coords) >= 4 and coords[0] == coords[-1]:
        polygon = Polygon(coords)
        if polygon.is_valid and not polygon.is_empty:
            return polygon, "full_way_polygon", 70.0

    line = LineString(coords)
    if line.is_empty:
        return None, "missing_geometry", 0.0
    return line, "full_way_line", 65.0


def _relation_geometry(element: dict[str, Any]):
    lines: list[LineString] = []
    for member in element.get("members") or []:
        coords = _coordinates_from_geometry(member.get("geometry") or [])
        if len(coords) >= 2:
            line = LineString(coords)
            if not line.is_empty:
                lines.append(line)

    if lines:
        if len(lines) == 1:
            return lines[0], "relation_member_geometry", 55.0
        return MultiLineString(lines), "relation_member_geometry", 55.0

    bounds = element.get("bounds") or {}
    needed = ("minlat", "minlon", "maxlat", "maxlon")
    if all(key in bounds for key in needed):
        lat = (float(bounds["minlat"]) + float(bounds["maxlat"])) / 2.0
        lon = (float(bounds["minlon"]) + float(bounds["maxlon"])) / 2.0
        return Point(lon, lat), "relation_bounds_center_fallback", 30.0

    center = element.get("center") or {}
    if "lat" in center and "lon" in center:
        return (
            Point(float(center["lon"]), float(center["lat"])),
            "relation_center_fallback",
            25.0,
        )

    return None, "missing_geometry", 0.0


def parse_osm_geometries(payload: dict[str, Any]) -> list[OSMGeometryFeature]:
    features: list[OSMGeometryFeature] = []

    for element in payload.get("elements", []):
        osm_type = str(element.get("type", ""))
        osm_id = element.get("id")
        tags = element.get("tags") or {}
        name = str(tags.get("name") or "").strip()

        if osm_id is None or not name:
            continue

        if osm_type == "way":
            geometry, role, confidence = _way_geometry(element)
        elif osm_type == "relation":
            geometry, role, confidence = _relation_geometry(element)
        elif osm_type == "node":
            lat = element.get("lat")
            lon = element.get("lon")
            if lat is None or lon is None:
                continue
            geometry = Point(float(lon), float(lat))
            role = "node_point"
            confidence = 50.0
        else:
            continue

        if geometry is None or geometry.is_empty:
            continue

        features.append(
            OSMGeometryFeature(
                osm_type=osm_type,
                osm_id=int(osm_id),
                name=name,
                tags={str(k): str(v) for k, v in tags.items()},
                geometry_geojson=mapping(geometry),
                geometry_role=role,
                confidence=confidence,
            )
        )

    return features


def _fetch_query(
    query: str,
    *,
    endpoint: str,
    timeout: float,
    session: requests.Session | None,
) -> list[OSMGeometryFeature]:
    client = session or requests.Session()
    try:
        response = client.post(
            endpoint,
            data={"data": query},
            timeout=timeout,
            headers={"User-Agent": "LAND-RADAR/0.8 spatial-research"},
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise OSMGeometryProviderError(f"OSM geometry query failed: {exc}") from exc

    return parse_osm_geometries(payload)


def fetch_industrial_geometries(
    bbox: tuple[float, float, float, float],
    *,
    endpoint: str = DEFAULT_OVERPASS_URL,
    timeout: float = 45.0,
    session: requests.Session | None = None,
) -> list[OSMGeometryFeature]:
    return _fetch_query(
        build_industrial_geometry_query(bbox),
        endpoint=endpoint,
        timeout=timeout,
        session=session,
    )


def fetch_rail_geometries(
    bbox: tuple[float, float, float, float],
    *,
    endpoint: str = DEFAULT_OVERPASS_URL,
    timeout: float = 45.0,
    session: requests.Session | None = None,
) -> list[OSMGeometryFeature]:
    return _fetch_query(
        build_rail_geometry_query(bbox),
        endpoint=endpoint,
        timeout=timeout,
        session=session,
    )


_TR_FOLD = str.maketrans({
    "ı": "i", "İ": "I",
    "ş": "s", "Ş": "S",
    "ğ": "g", "Ğ": "G",
    "ü": "u", "Ü": "U",
    "ö": "o", "Ö": "O",
    "ç": "c", "Ç": "C",
})

_GENERIC_TOKENS = {
    "organize", "organizeli", "sanayi", "bolgesi", "bolge", "osb",
    "demiryolu", "hizli", "tren", "projesi", "hatti", "hat",
    "baglantisi", "baglanti",
}


def _tokens(value: str) -> set[str]:
    folded = value.translate(_TR_FOLD).casefold()
    folded = re.sub(r"[^a-z0-9]+", " ", folded)
    return {
        token
        for token in folded.split()
        if len(token) >= 3 and token not in _GENERIC_TOKENS
    }


def name_similarity(left: str, right: str) -> float:
    a = _tokens(left)
    b = _tokens(right)
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return round(intersection / union, 4)


def best_name_matches(
    target_name: str,
    features: Iterable[OSMGeometryFeature],
    *,
    minimum_score: float = 0.25,
    limit: int = 5,
) -> list[tuple[OSMGeometryFeature, float]]:
    scored = [
        (feature, name_similarity(target_name, feature.name))
        for feature in features
    ]
    scored = [
        item
        for item in scored
        if item[1] >= minimum_score
    ]
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:limit]


def to_geometry_evidence(
    feature: OSMGeometryFeature,
    *,
    observed_date: date | None = None,
) -> GeometryEvidence:
    return GeometryEvidence(
        source="OpenStreetMap / Overpass",
        feature_name=feature.name,
        geometry_geojson=feature.geometry_geojson,
        observed_date=observed_date or date.today(),
        source_url="https://www.openstreetmap.org/",
        feature_id=feature.feature_id,
        confidence=feature.confidence,
        geometry_role=feature.geometry_role,
    )
