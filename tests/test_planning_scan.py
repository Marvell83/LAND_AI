from datetime import date
from pathlib import Path

import pandas as pd

from land_radar.plan_evidence import PlanEvidence, PlanStage
from land_radar.plan_registry import save_plan_registry
from land_radar.planning_scan import run_planning_scan


def _candidates(path: Path):
    pd.DataFrame(
        [
            {
                "cell_id": "A",
                "center_lat": 40.0,
                "center_lon": 27.5,
            },
            {
                "cell_id": "B",
                "center_lat": 38.0,
                "center_lon": 35.0,
            },
        ]
    ).to_csv(path, index=False)


def test_planning_scan_distinguishes_context_from_verified_uip(tmp_path: Path):
    candidates = tmp_path / "candidates.csv"
    _candidates(candidates)

    registry = tmp_path / "plans.json"
    save_plan_registry(
        [
            PlanEvidence(
                plan_id="UIP-1",
                title="Finalized test UIP",
                plan_type="UIP",
                stage=PlanStage.FINALIZED,
                source="e-Plan",
                source_url="https://eplan.csb.gov.tr/",
                scale_denominator=1000,
                published_date=date(2026, 1, 1),
                confidence=95,
                geometry_verified=True,
                properties={"cell_id": "A"},
            )
        ],
        registry,
    )

    result = run_planning_scan(
        candidate_csv=candidates,
        plan_registry_path=registry,
        output_dir=tmp_path / "out",
        as_of_date=date(2026, 10, 25),
    )
    frame = pd.read_csv(result.output_csv)

    a = frame.loc[frame["cell_id"] == "A"].iloc[0]
    b = frame.loc[frame["cell_id"] == "B"].iloc[0]

    assert bool(a["cdp_wms_covered"]) is True
    assert bool(a["planning_known"]) is True
    assert a["finalized_uip_nip_verified_count"] == 1

    assert bool(b["cdp_wms_covered"]) is False
    assert bool(b["planning_known"]) is False
