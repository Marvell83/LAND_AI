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
    DataSource("GHSL", "urban", "Historical built-up / settlement change", "planned"),
    DataSource("Copernicus Data Space / Sentinel-2", "satellite", "Recent land-surface change confirmation", "planned"),
    DataSource("Copernicus DEM", "terrain", "Elevation and slope", "planned"),
    DataSource("OpenStreetMap", "access", "Road and accessibility context", "planned"),
    DataSource("OSB official data", "catalyst", "Industrial zones and expansion evidence", "planned"),
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
