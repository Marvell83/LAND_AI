from pathlib import Path

import pandas as pd

from land_radar.hazard import HazardGeometry, HazardSeverity
from land_radar.providers.mta_landslide import MTALandslideConfig
import land_radar.landslide_scan as module


def test_landslide_scan_marks_checked_even_with_zero_nearby(tmp_path: Path, monkeypatch):
    candidates = tmp_path / "candidates.csv"
    pd.DataFrame(
        [
            {"cell_id": "A", "center_lat": 40.0, "center_lon": 29.0},
            {"cell_id": "B", "center_lat": 41.0, "center_lon": 30.0},
        ]
    ).to_csv(candidates, index=False)

    monkeypatch.setattr(
        module,
        "fetch_landslide_hazards",
        lambda bbox, config: [
            HazardGeometry(
                hazard_id="mta:1",
                category="landslide_inventory",
                severity=HazardSeverity.UNKNOWN,
                geometry_geojson={
                    "type": "Point",
                    "coordinates": [29.0, 40.0],
                },
                source="MTA/TUCBS",
                hard_veto=False,
                confidence=90,
            )
        ],
    )

    result = module.run_landslide_scan(
        candidate_csv=candidates,
        output_dir=tmp_path / "out",
        config=MTALandslideConfig(
            service_url="https://example.gov.tr/wfs",
            type_name="mta:landslide",
        ),
    )

    frame = pd.read_csv(result.output_csv)
    assert len(frame) == 2
    assert frame["checked"].all()
    assert frame.loc[frame["cell_id"] == "A", "finding_count"].iloc[0] >= 1
