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
    DataSource("Copernicus DEM GLO-90", "terrain", "Elevation, slope and cached batch terrain scan", "batch_engine_ready"),
    DataSource("OpenStreetMap / Overpass", "access", "Road/access context plus industrial and rail geometry evidence", "spatial_geometry_ready"),
    DataSource("OSBÜK OSB listesi", "catalyst", "Current OSB status feed and stage mapping", "status_feed_ready"),
    DataSource("KGM official data", "catalyst", "Road infrastructure evidence", "planned"),
    DataSource("AYGM / UAB railway projects", "catalyst", "Official railway project status groups", "status_feed_ready"),
    DataSource("Tarım ve Orman KorunanAlanlarWFS", "planning", "Official protected-area geometry and legal-review context", "direct_service_ready"),
    DataSource("e-Plan official evidence registry", "planning", "Point-in-time plan lifecycle, finalized UIP/NIP verification and Top-30 planning scan", "registry_engine_ready"),
    DataSource("TUCBS / ULASAV plan WMS", "planning", "Verified regional CDP WMS context", "partial_service_registry_ready"),
    DataSource("Tarım ve Orman / USBS flood risk", "risk", "Official flood-risk polygon query", "direct_service_ready"),
    DataSource("MTA / TUCBS landslide inventory", "risk", "Configurable WFS inventory screening for Top-30", "configurable_wfs_ready"),
    DataSource("AFAD landslide susceptibility", "risk", "Restricted/not publicly configured susceptibility evidence", "restricted"),
    DataSource("AFAD / TUCBS / other official hazard export", "risk", "GeoJSON hazard registry, overlap, distance and explicit hard-veto", "manual_registry_ready"),
    DataSource("User / institutional comparable dataset", "price", "Robust local comparable distribution plus Top-30 batch evidence", "candidate_batch_ready"),
)


def source_status() -> dict[str, int]:
    counts: dict[str, int] = {}
    for source in SOURCES:
        counts[source.status] = counts.get(source.status, 0) + 1
    return counts
