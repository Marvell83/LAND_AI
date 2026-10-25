from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

from .spatial.geometry import GeometryEvidence, geometry_from_geojson
from .spatial.registry import (
    GeometryRegistryEntry,
    load_geometry_registry,
    save_geometry_registry,
)


class GeometryImportError(ValueError):
    pass


ALLOWED_ROLES = {
    "official_vector_route",
    "digitized_official_map",
    "schematic_route",
    "official_boundary",
    "observed_geometry",
}


@dataclass(frozen=True)
class RawGeometry:
    name: str
    geometry_geojson: dict[str, Any]
    feature_id: str | None = None


def _validate_source_url(url: str) -> str:
    value = str(url or "").strip()
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise GeometryImportError(
            "Geometry source_url must be an HTTPS source URL"
        )
    return value


def _validate_role(
    role: str,
    confidence: float,
    manual_verified: bool,
) -> None:
    if role not in ALLOWED_ROLES:
        raise GeometryImportError(
            f"Unsupported geometry role: {role}. "
            f"Allowed: {', '.join(sorted(ALLOWED_ROLES))}"
        )
    if not 0 <= confidence <= 100:
        raise GeometryImportError("confidence must be between 0 and 100")

    if role == "digitized_official_map":
        if not manual_verified:
            raise GeometryImportError(
                "digitized_official_map requires manual_verified=true"
            )
        if confidence > 80:
            raise GeometryImportError(
                "digitized_official_map confidence cannot exceed 80"
            )

    if role == "schematic_route":
        if not manual_verified:
            raise GeometryImportError(
                "schematic_route requires manual_verified=true"
            )
        if confidence > 60:
            raise GeometryImportError(
                "schematic_route confidence cannot exceed 60"
            )


def _validate_geometry_for_role(
    geometry: dict[str, Any],
    role: str,
) -> None:
    shape = geometry_from_geojson(geometry)
    geom_type = shape.geom_type

    if role in {
        "official_vector_route",
        "digitized_official_map",
        "schematic_route",
    } and geom_type not in {"LineString", "MultiLineString"}:
        raise GeometryImportError(
            f"{role} requires LineString/MultiLineString, got {geom_type}"
        )

    if role == "official_boundary" and geom_type not in {
        "Polygon",
        "MultiPolygon",
    }:
        raise GeometryImportError(
            f"official_boundary requires Polygon/MultiPolygon, got {geom_type}"
        )


def raw_geojson_geometries(
    payload: dict[str, Any],
) -> list[RawGeometry]:
    payload_type = payload.get("type")
    items: list[RawGeometry] = []

    if payload_type == "FeatureCollection":
        features = payload.get("features") or []
    elif payload_type == "Feature":
        features = [payload]
    else:
        geometry_from_geojson(payload)
        return [
            RawGeometry(
                name="Imported geometry",
                geometry_geojson=payload,
            )
        ]

    for index, feature in enumerate(features, start=1):
        if feature.get("type") != "Feature":
            raise GeometryImportError(
                f"GeoJSON item {index} is not a Feature"
            )
        geometry = feature.get("geometry")
        if not geometry:
            continue
        props = feature.get("properties") or {}
        name = str(
            props.get("name")
            or props.get("title")
            or props.get("feature_name")
            or f"Imported feature {index}"
        ).strip()
        feature_id = feature.get("id") or props.get("id")
        geometry_from_geojson(geometry)
        items.append(
            RawGeometry(
                name=name,
                geometry_geojson=geometry,
                feature_id=(
                    str(feature_id)
                    if feature_id is not None
                    else None
                ),
            )
        )

    if not items:
        raise GeometryImportError("GeoJSON contains no usable geometries")
    return items


def _parse_coordinates(text: str) -> list[list[float]]:
    coords: list[list[float]] = []
    for token in str(text or "").replace("\n", " ").split():
        parts = token.split(",")
        if len(parts) < 2:
            continue
        coords.append([float(parts[0]), float(parts[1])])
    if not coords:
        raise GeometryImportError("KML geometry has no valid coordinates")
    return coords


def raw_kml_geometries(kml_text: str) -> list[RawGeometry]:
    try:
        root = ET.fromstring(kml_text)
    except ET.ParseError as exc:
        raise GeometryImportError(f"Invalid KML: {exc}") from exc

    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    placemarks = root.findall(".//kml:Placemark", ns)
    if not placemarks:
        # Some producers omit namespace.
        placemarks = root.findall(".//Placemark")

    output: list[RawGeometry] = []
    for index, placemark in enumerate(placemarks, start=1):
        name_node = placemark.find("kml:name", ns)
        if name_node is None:
            name_node = placemark.find("name")
        name = (
            _clean_xml_text(name_node.text)
            if name_node is not None
            else f"KML Placemark {index}"
        )

        line_nodes = placemark.findall(".//kml:LineString", ns)
        if not line_nodes:
            line_nodes = placemark.findall(".//LineString")

        lines: list[list[list[float]]] = []
        for line in line_nodes:
            node = line.find("kml:coordinates", ns)
            if node is None:
                node = line.find("coordinates")
            if node is not None:
                lines.append(_parse_coordinates(node.text or ""))

        if lines:
            geometry = (
                {"type": "LineString", "coordinates": lines[0]}
                if len(lines) == 1
                else {"type": "MultiLineString", "coordinates": lines}
            )
            output.append(
                RawGeometry(
                    name=name,
                    geometry_geojson=geometry,
                    feature_id=f"kml:{index}",
                )
            )
            continue

        polygon_nodes = placemark.findall(".//kml:Polygon", ns)
        if not polygon_nodes:
            polygon_nodes = placemark.findall(".//Polygon")

        polygons: list[list[list[list[float]]]] = []
        for polygon in polygon_nodes:
            outer = polygon.find(
                ".//kml:outerBoundaryIs/kml:LinearRing/kml:coordinates",
                ns,
            )
            if outer is None:
                outer = polygon.find(
                    ".//outerBoundaryIs/LinearRing/coordinates"
                )
            if outer is None:
                continue
            rings = [_parse_coordinates(outer.text or "")]

            inner_nodes = polygon.findall(
                ".//kml:innerBoundaryIs/kml:LinearRing/kml:coordinates",
                ns,
            )
            if not inner_nodes:
                inner_nodes = polygon.findall(
                    ".//innerBoundaryIs/LinearRing/coordinates"
                )
            for inner in inner_nodes:
                rings.append(_parse_coordinates(inner.text or ""))
            polygons.append(rings)

        if polygons:
            geometry = (
                {"type": "Polygon", "coordinates": polygons[0]}
                if len(polygons) == 1
                else {"type": "MultiPolygon", "coordinates": polygons}
            )
            output.append(
                RawGeometry(
                    name=name,
                    geometry_geojson=geometry,
                    feature_id=f"kml:{index}",
                )
            )

    if not output:
        raise GeometryImportError(
            "KML contains no supported LineString or Polygon Placemark"
        )
    return output


def _clean_xml_text(value: str | None) -> str:
    return " ".join(str(value or "").split()) or "Unnamed geometry"


def make_registry_entries(
    geometries: Iterable[RawGeometry],
    *,
    catalyst_id: str,
    source: str,
    source_url: str,
    observed_date: date,
    confidence: float,
    geometry_role: str,
    manual_verified: bool,
) -> list[GeometryRegistryEntry]:
    catalyst_id = str(catalyst_id or "").strip()
    source = str(source or "").strip()
    if not catalyst_id:
        raise GeometryImportError("catalyst_id is required")
    if not source:
        raise GeometryImportError("source is required")

    url = _validate_source_url(source_url)
    confidence = float(confidence)
    _validate_role(
        geometry_role,
        confidence,
        manual_verified,
    )

    entries: list[GeometryRegistryEntry] = []
    for geometry in geometries:
        _validate_geometry_for_role(
            geometry.geometry_geojson,
            geometry_role,
        )
        entries.append(
            GeometryRegistryEntry(
                catalyst_id=catalyst_id,
                evidence=GeometryEvidence(
                    source=source,
                    feature_name=geometry.name,
                    geometry_geojson=geometry.geometry_geojson,
                    observed_date=observed_date,
                    source_url=url,
                    feature_id=geometry.feature_id,
                    confidence=confidence,
                    geometry_role=geometry_role,
                ),
                manual_verified=manual_verified,
            )
        )
    return entries


def append_registry_entries(
    path: str | Path,
    entries: Iterable[GeometryRegistryEntry],
) -> list[GeometryRegistryEntry]:
    path = Path(path)
    existing = load_geometry_registry(path)
    combined = list(existing)
    fingerprints = {
        (
            entry.catalyst_id,
            entry.evidence.feature_id,
            entry.evidence.feature_name,
        )
        for entry in existing
    }

    for entry in entries:
        fingerprint = (
            entry.catalyst_id,
            entry.evidence.feature_id,
            entry.evidence.feature_name,
        )
        if fingerprint not in fingerprints:
            combined.append(entry)
            fingerprints.add(fingerprint)

    save_geometry_registry(combined, path)
    return combined


def load_raw_geometry_file(
    path: str | Path,
) -> list[RawGeometry]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Geometry file not found: {path}")

    suffix = path.suffix.casefold()
    if suffix in {".geojson", ".json"}:
        return raw_geojson_geometries(
            json.loads(path.read_text(encoding="utf-8"))
        )
    if suffix == ".kml":
        return raw_kml_geometries(
            path.read_text(encoding="utf-8")
        )
    raise GeometryImportError(
        "Supported geometry formats: .geojson, .json, .kml"
    )
