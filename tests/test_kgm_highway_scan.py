from datetime import date
from pathlib import Path

import pandas as pd

from land_radar.catalyst import CatalystStage
from land_radar.providers.kgm_highway import KGMHighwayProject
from land_radar.spatial.geometry import GeometryEvidence
from land_radar.spatial.registry import (
    GeometryRegistryEntry,
    save_geometry_registry,
)
from land_radar.kgm_highway_scan import run_kgm_highway_scan


def test_kgm_scan_requires_matching_geometry_for_spatial_known(tmp_path: Path):
    candidates = tmp_path / "candidates.csv"
    pd.DataFrame(
        [
            {"cell_id": "A", "center_lat": 40.0, "center_lon": 29.0},
            {"cell_id": "B", "center_lat": 41.0, "center_lon": 30.0},
        ]
    ).to_csv(candidates, index=False)

    projects = [
        KGMHighwayProject(
            project_id="road:kgm:test-project",
            name="Test Highway",
            detail_url="https://www.kgm.gov.tr/test.aspx",
            stage=CatalystStage.CONSTRUCTION_STARTED,
            stage_claim="Projede yapım çalışmaları devam etmektedir.",
            observed_date=date(2026, 10, 25),
        ),
        KGMHighwayProject(
            project_id="road:kgm:no-geometry",
            name="No Geometry Highway",
            detail_url="https://www.kgm.gov.tr/test2.aspx",
            stage=CatalystStage.OFFICIAL_INTENT,
            stage_claim="Resmî proje.",
            observed_date=date(2026, 10, 25),
        ),
    ]

    registry = tmp_path / "geometry.geojson"
    save_geometry_registry(
        [
            GeometryRegistryEntry(
                catalyst_id="road:kgm:test-project",
                evidence=GeometryEvidence(
                    source="official/manual verified route",
                    feature_name="Test Highway",
                    geometry_geojson={
                        "type": "LineString",
                        "coordinates": [
                            [28.95, 40.0],
                            [29.05, 40.0],
                        ],
                    },
                    observed_date=date(2026, 10, 25),
                    source_url="https://www.kgm.gov.tr/test.aspx",
                    confidence=95,
                    geometry_role="project_route",
                ),
                manual_verified=True,
            )
        ],
        registry,
    )

    result = run_kgm_highway_scan(
        candidate_csv=candidates,
        geometry_registry_path=registry,
        output_dir=tmp_path / "out",
        projects=projects,
        max_distance_km=30,
    )

    frame = pd.read_csv(result.candidate_csv)
    a = frame.loc[frame["cell_id"] == "A"].iloc[0]
    b = frame.loc[frame["cell_id"] == "B"].iloc[0]

    assert bool(a["spatial_known"]) is True
    assert a["nearest_project_id"] == "road:kgm:test-project"
    assert bool(b["spatial_known"]) is False
    assert result.geometry_project_count == 1
