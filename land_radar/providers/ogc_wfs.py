from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


class OGCWFSError(RuntimeError):
    pass


@dataclass(frozen=True)
class WFSQueryResult:
    features: tuple[dict[str, Any], ...]
    pages: int
    source_url: str
    type_name: str


def query_wfs_geojson(
    service_url: str,
    type_name: str,
    bbox: tuple[float, float, float, float],
    *,
    version: str = "2.0.0",
    page_size: int = 1000,
    timeout: float = 60.0,
    session: requests.Session | None = None,
) -> WFSQueryResult:
    if not service_url.startswith("https://"):
        raise ValueError("WFS service_url must use HTTPS")
    if not type_name.strip():
        raise ValueError("WFS type_name cannot be empty")
    if page_size <= 0 or page_size > 5000:
        raise ValueError("page_size must be between 1 and 5000")

    min_lon, min_lat, max_lon, max_lat = bbox
    if min_lon >= max_lon or min_lat >= max_lat:
        raise ValueError("Invalid bbox")

    client = session or requests.Session()
    features: list[dict[str, Any]] = []
    seen: set[str] = set()
    start_index = 0
    pages = 0

    while True:
        params = {
            "service": "WFS",
            "request": "GetFeature",
            "version": version,
            "typeNames": type_name,
            "srsName": "EPSG:4326",
            "bbox": f"{min_lon},{min_lat},{max_lon},{max_lat},EPSG:4326",
            "outputFormat": "application/json",
            "count": page_size,
            "startIndex": start_index,
        }
        try:
            response = client.get(
                service_url,
                params=params,
                timeout=timeout,
                headers={"User-Agent": "LAND-RADAR/0.18 official-wfs-research"},
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise OGCWFSError(
                f"WFS query failed for {service_url}: {exc}"
            ) from exc

        page = payload.get("features") or []
        if not isinstance(page, list):
            raise OGCWFSError("WFS response has invalid features payload")

        for feature in page:
            feature_id = str(
                feature.get("id")
                or (feature.get("properties") or {}).get("id")
                or feature
            )
            if feature_id not in seen:
                seen.add(feature_id)
                features.append(feature)

        pages += 1
        if len(page) < page_size or not page:
            break

        start_index += len(page)
        if pages >= 100:
            raise OGCWFSError("WFS pagination safety limit reached")

    return WFSQueryResult(
        features=tuple(features),
        pages=pages,
        source_url=service_url,
        type_name=type_name,
    )
