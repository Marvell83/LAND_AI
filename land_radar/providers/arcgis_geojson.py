from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


class ArcGISGeoJSONError(RuntimeError):
    pass


@dataclass(frozen=True)
class ArcGISQueryResult:
    features: tuple[dict[str, Any], ...]
    pages: int
    source_url: str


def query_layer_geojson(
    layer_url: str,
    bbox: tuple[float, float, float, float],
    *,
    where: str = "1=1",
    out_fields: str = "*",
    page_size: int = 1000,
    timeout: float = 60.0,
    session: requests.Session | None = None,
) -> ArcGISQueryResult:
    """Query an ArcGIS Feature Layer as GeoJSON with safe pagination."""
    if not layer_url.startswith("https://"):
        raise ValueError("ArcGIS layer_url must use HTTPS")
    if page_size <= 0 or page_size > 2000:
        raise ValueError("page_size must be between 1 and 2000")

    min_lon, min_lat, max_lon, max_lat = bbox
    if min_lon >= max_lon or min_lat >= max_lat:
        raise ValueError("Invalid bbox")

    client = session or requests.Session()
    query_url = layer_url.rstrip("/") + "/query"
    offset = 0
    pages = 0
    features: list[dict[str, Any]] = []
    seen_ids: set[tuple[str, str]] = set()

    while True:
        params = {
            "where": where,
            "geometry": f"{min_lon},{min_lat},{max_lon},{max_lat}",
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": out_fields,
            "returnGeometry": "true",
            "outSR": "4326",
            "resultOffset": offset,
            "resultRecordCount": page_size,
            "f": "geojson",
        }

        try:
            response = client.get(
                query_url,
                params=params,
                timeout=timeout,
                headers={"User-Agent": "LAND-RADAR/0.14 official-spatial-research"},
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise ArcGISGeoJSONError(
                f"ArcGIS GeoJSON query failed for {layer_url}: {exc}"
            ) from exc

        if "error" in payload:
            message = payload["error"].get("message", "ArcGIS service error")
            raise ArcGISGeoJSONError(f"{layer_url}: {message}")

        page_features = payload.get("features") or []
        if not isinstance(page_features, list):
            raise ArcGISGeoJSONError(
                f"ArcGIS response has invalid features payload: {layer_url}"
            )

        for feature in page_features:
            props = feature.get("properties") or {}
            oid = (
                props.get("OBJECTID")
                or props.get("ObjectId")
                or props.get("FID")
                or props.get("objectid")
            )
            key = (str(oid), str(feature.get("geometry")))
            if key not in seen_ids:
                seen_ids.add(key)
                features.append(feature)

        pages += 1

        exceeded = bool(
            payload.get("exceededTransferLimit")
            or payload.get("properties", {}).get("exceededTransferLimit")
        )

        if len(page_features) < page_size and not exceeded:
            break
        if not page_features:
            break

        offset += len(page_features)
        if pages >= 100:
            raise ArcGISGeoJSONError(
                f"ArcGIS pagination safety limit reached for {layer_url}"
            )

    return ArcGISQueryResult(
        features=tuple(features),
        pages=pages,
        source_url=layer_url,
    )
