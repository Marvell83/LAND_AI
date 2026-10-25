from pathlib import Path

import pandas as pd

from land_radar.hazard import HazardGeometry, HazardSeverity
from land_radar.planning import LegalEffect, PlanningConstraint
import land_radar.official_constraints_scan as module


def _deep_scan(path: Path):
    pd.DataFrame(
        [
            {
                "cell_id": "A",
                "center_lat": 40.0,
                "center_lon": 29.0,
            },
            {
                "cell_id": "B",
                "center_lat": 40.1,
                "center_lon": 29.1,
            },
        ]
    ).to_csv(path, index=False)


def _polygon():
    return {
        "type": "Polygon",
        "coordinates": [[
            [28.99, 39.99],
            [29.01, 39.99],
            [29.01, 40.01],
            [28.99, 40.01],
            [28.99, 39.99],
        ]],
    }


def test_official_scan_writes_checked_rows(tmp_path: Path, monkeypatch):
    deep = tmp_path / "deep.csv"
    _deep_scan(deep)

    monkeypatch.setattr(
        module,
        "fetch_protected_constraints",
        lambda bbox: [
            PlanningConstraint(
                constraint_id="park:1",
                category="national_park",
                geometry_geojson=_polygon(),
                source="official",
                legal_effect=LegalEffect.REVIEW_REQUIRED,
                confidence=95,
            )
        ],
    )
    monkeypatch.setattr(
        module,
        "fetch_flood_hazards",
        lambda bbox: [
            HazardGeometry(
                hazard_id="flood:1",
                category="flood_risk",
                severity=HazardSeverity.HIGH,
                geometry_geojson=_polygon(),
                source="official",
                confidence=95,
            )
        ],
    )

    result = module.run_official_constraints_scan(
        deep_scan_csv=deep,
        output_dir=tmp_path / "out",
        cell_km=5.0,
    )

    protected = pd.read_csv(result.protected_csv)
    flood = pd.read_csv(result.flood_csv)

    assert len(protected) == 2
    assert len(flood) == 2
    assert protected["checked"].all()
    assert flood["checked"].all()
    assert protected.loc[protected["cell_id"] == "A", "legal_review_required"].iloc[0]
