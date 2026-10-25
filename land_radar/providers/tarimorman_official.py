from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Any

from ..hazard import HazardGeometry, HazardSeverity
from ..planning import LegalEffect, PlanningConstraint
from .arcgis_geojson import ArcGISGeoJSONError, query_layer_geojson


PROTECTED_BASE = (
    "https://cbs1.tarimorman.gov.tr/server/rest/services/"
    "KorunanAlanlarWFS/MapServer"
)
FLOOD_LAYER_URL = (
    "https://cbs1.tarimorman.gov.tr/server/rest/services/"
    "SYGM_USBS/SYGM_USBS/MapServer/5"
)


@dataclass(frozen=True)
class ProtectedLayer:
    layer_id: int
    category: str
    label: str


PROTECTED_LAYERS = (
    ProtectedLayer(0, "national_park", "Milli Park"),
    ProtectedLayer(1, "nature_park", "Tabiat Parkı"),
    ProtectedLayer(2, "nature_conservation_area", "Tabiatı Koruma Alanı"),
    ProtectedLayer(3, "natural_monument", "Tabiat Anıtı"),
    ProtectedLayer(5, "ramsar_wetland", "Ramsar Sulak Alanı"),
    ProtectedLayer(6, "national_importance_wetland", "Ulusal Öneme Haiz Sulak Alan"),
    ProtectedLayer(7, "local_importance_wetland", "Mahalli Öneme Haiz Sulak Alan"),
    ProtectedLayer(8, "wildlife_development_area", "Yaban Hayatı Geliştirme Sahası"),
)


def _object_id(properties: dict[str, Any], fallback: int) -> str:
    for key in ("OBJECTID", "ObjectId", "objectid", "FID"):
        value = properties.get(key)
        if value is not None:
            return str(value)
    return str(fallback)


def _name(properties: dict[str, Any]) -> str | None:
    for key in ("SITENAME", "NAMESPAC", "ALAN_ADI", "NAME", "ADI", "AD"):
        value = properties.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def feature_to_protected_constraint(
    feature: dict[str, Any],
    layer: ProtectedLayer,
    *,
    observed_date: date | None = None,
) -> PlanningConstraint | None:
    geometry = feature.get("geometry")
    if not geometry:
        return None

    props = feature.get("properties") or {}
    oid = _object_id(props, 0)
    site_name = _name(props)
    note = (
        f"Resmî {layer.label} geometrisi. "
        "Bu eşleşme otomatik yapılaşma yasağı/hard-veto sayılmaz; "
        "parsel bazında mevzuat ve plan notu incelemesi gerekir."
    )
    if site_name:
        note += f" Alan: {site_name}."

    return PlanningConstraint(
        constraint_id=f"tarimorman:{layer.category}:{oid}",
        category=layer.category,
        geometry_geojson=geometry,
        source="Tarım ve Orman Bakanlığı KorunanAlanlarWFS",
        legal_effect=LegalEffect.REVIEW_REQUIRED,
        observed_date=observed_date or date.today(),
        source_url=f"{PROTECTED_BASE}/{layer.layer_id}",
        hard_veto=False,
        confidence=95.0,
        note=note,
        properties={str(k): v for k, v in props.items()},
    )


def fetch_protected_constraints(
    bbox: tuple[float, float, float, float],
) -> list[PlanningConstraint]:
    constraints: list[PlanningConstraint] = []
    for layer in PROTECTED_LAYERS:
        result = query_layer_geojson(
            f"{PROTECTED_BASE}/{layer.layer_id}",
            bbox,
            page_size=1000,
        )
        for index, feature in enumerate(result.features, start=1):
            constraint = feature_to_protected_constraint(
                feature,
                layer,
            )
            if constraint is not None:
                constraints.append(constraint)
    return constraints


_TR_FOLD = str.maketrans({
    "ı": "i", "İ": "I",
    "ş": "s", "Ş": "S",
    "ğ": "g", "Ğ": "G",
    "ü": "u", "Ü": "U",
    "ö": "o", "Ö": "O",
    "ç": "c", "Ç": "C",
})


def _fold(value: Any) -> str:
    text = str(value or "").translate(_TR_FOLD).casefold()
    return re.sub(r"\s+", " ", text).strip()


def flood_severity_from_properties(
    properties: dict[str, Any],
) -> HazardSeverity:
    category = _fold(properties.get("KATEGORI"))
    if "cok yuksek" in category:
        return HazardSeverity.CRITICAL
    if "yuksek" in category:
        return HazardSeverity.HIGH
    if "orta" in category:
        return HazardSeverity.MEDIUM
    if "dusuk" in category:
        return HazardSeverity.LOW
    return HazardSeverity.UNKNOWN


def feature_to_flood_hazard(
    feature: dict[str, Any],
    *,
    observed_date: date | None = None,
) -> HazardGeometry | None:
    geometry = feature.get("geometry")
    if not geometry:
        return None

    props = feature.get("properties") or {}
    oid = _object_id(props, 0)
    severity = flood_severity_from_properties(props)
    category_text = props.get("KATEGORI")
    area_name = props.get("ALAN_ADI")

    details = []
    if area_name:
        details.append(f"alan={area_name}")
    if category_text:
        details.append(f"kategori={category_text}")
    for key in (
        "RISK50", "RISK100", "RISK500",
        "RISK50_ENUM", "RISK100_ENUM", "RISK500_ENUM",
    ):
        value = props.get(key)
        if value is not None:
            details.append(f"{key}={value}")

    note = (
        "USBS resmî taşkın risk poligonu. "
        "Hard-veto otomatik verilmez; parsel/plan ve güncel risk dokümanı ayrıca incelenmelidir."
    )
    if details:
        note += " " + "; ".join(details)

    return HazardGeometry(
        hazard_id=f"usbs:flood:{oid}",
        category="flood_risk",
        severity=severity,
        geometry_geojson=geometry,
        source="Tarım ve Orman Bakanlığı / USBS Taşkın Risk Haritaları",
        observed_date=observed_date or date.today(),
        source_url=FLOOD_LAYER_URL,
        hard_veto=False,
        confidence=95.0,
        note=note,
    )


def fetch_flood_hazards(
    bbox: tuple[float, float, float, float],
) -> list[HazardGeometry]:
    result = query_layer_geojson(
        FLOOD_LAYER_URL,
        bbox,
        out_fields=(
            "OBJECTID,ALAN_ADI,KATEGORI,"
            "RISK50,RISK100,RISK500,"
            "RISK50_ENUM,RISK100_ENUM,RISK500_ENUM"
        ),
        page_size=1000,
    )
    hazards: list[HazardGeometry] = []
    for feature in result.features:
        hazard = feature_to_flood_hazard(feature)
        if hazard is not None:
            hazards.append(hazard)
    return hazards


__all__ = [
    "ArcGISGeoJSONError",
    "PROTECTED_LAYERS",
    "FLOOD_LAYER_URL",
    "fetch_protected_constraints",
    "fetch_flood_hazards",
    "feature_to_protected_constraint",
    "feature_to_flood_hazard",
    "flood_severity_from_properties",
]
