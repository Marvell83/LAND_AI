from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class PlanWMSService:
    service_id: str
    label: str
    plan_type: str
    url: str
    bounds: tuple[float, float, float, float]
    source: str = "TUCBS / ULASAV"
    confidence: float = 90.0

    def covers(self, lat: float, lon: float) -> bool:
        min_lon, min_lat, max_lon, max_lat = self.bounds
        return min_lon <= lon <= max_lon and min_lat <= lat <= max_lat


# Only endpoints with a currently documented public WMS URL are listed.
# This registry is deliberately incomplete; missing regions remain UNKNOWN.
VERIFIED_PLAN_WMS = (
    PlanWMSService(
        service_id="csb_cdp_cb",
        label="Balıkesir-Çanakkale Çevre Düzeni Planı",
        plan_type="CDP",
        url="https://tucbs-public-api.csb.gov.tr/csb_cdp_cb_wms",
        bounds=(25.155116, 38.818504, 29.863585, 42.064769),
    ),
    PlanWMSService(
        service_id="csb_cdp_bilecik",
        label="Bilecik Çevre Düzeni Planı",
        plan_type="CDP",
        url="https://tucbs-public-api.csb.gov.tr/csb_cdp_bilecik_wms",
        bounds=(29.697089, 39.632060, 30.678411, 40.521301),
    ),
    PlanWMSService(
        service_id="csb_cdp_bolu",
        label="Bolu Çevre Düzeni Planı",
        plan_type="CDP",
        url="https://tucbs-public-api.csb.gov.tr/csb_cdp_bolu_wms",
        bounds=(30.550151, 40.144285, 32.568856, 41.055657),
    ),
)


def services_for_point(
    lat: float,
    lon: float,
    services: Iterable[PlanWMSService] = VERIFIED_PLAN_WMS,
) -> list[PlanWMSService]:
    return [
        service
        for service in services
        if service.covers(lat, lon)
    ]
