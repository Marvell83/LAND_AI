from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DataSource:
    name: str
    category: str
    purpose: str
    status: str
    point_in_time_required: bool = True


SOURCES = (
    DataSource("GHSL GHS-BUILT-S R2023A", "urban", "Historical built-up structural baseline", "local_engine_ready"),
    DataSource("Copernicus Data Space / Sentinel-2 L2A", "satellite", "Scene discovery plus two-period spectral/SCL change", "spectral_engine_ready"),
    DataSource("Copernicus DEM GLO-90", "terrain", "Elevation and slope", "oauth_adapter_ready"),
    DataSource("OpenStreetMap / Overpass", "access", "Road and accessibility context", "probe_integrated"),
    DataSource("OSBÜK OSB listesi", "catalyst", "Current OSB status feed and stage mapping", "status_feed_ready"),
    DataSource("KGM official data", "catalyst", "Road infrastructure evidence", "planned"),
    DataSource("TCDD / UAB official data", "catalyst", "Rail and transport evidence", "planned"),
    DataSource("Municipal / e-Plan sources", "planning", "Planning decisions and maturity", "planned"),
    DataSource("AFAD / MTA / official hazard data", "risk", "Flood, landslide, geology and hazards", "planned"),
    DataSource("Market / comparable price dataset", "price", "Relative price and mispricing", "unresolved"),
)


def source_status() -> dict[str, int]:
    counts: dict[str, int] = {}
    for source in SOURCES:
        counts[source.status] = counts.get(source.status, 0) + 1
    return counts
