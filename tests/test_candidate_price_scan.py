from datetime import date
from pathlib import Path

import pandas as pd

from land_radar.candidate_price_scan import run_candidate_price_scan


def _candidates(path: Path):
    pd.DataFrame(
        [
            {"cell_id": "A", "center_lat": 40.0, "center_lon": 29.0},
            {"cell_id": "B", "center_lat": 41.0, "center_lon": 30.0},
        ]
    ).to_csv(path, index=False)


def test_candidate_price_scan_distinguishes_known_and_missing(tmp_path: Path):
    candidates = tmp_path / "candidates.csv"
    comparables = tmp_path / "comparables.csv"
    _candidates(candidates)

    rows = []
    for i in range(10):
        rows.append(
            {
                "observed_date": f"2026-0{1 + (i % 6)}-01",
                "price_tl": 1_000_000 + i * 10_000,
                "area_m2": 1000,
                "source_type": "asking",
                "lat": 40.0 + (i % 3) * 0.001,
                "lon": 29.0 + (i % 3) * 0.001,
                "land_type": "tarla",
            }
        )
    pd.DataFrame(rows).to_csv(comparables, index=False)

    result = run_candidate_price_scan(
        candidate_csv=candidates,
        comparable_csv=comparables,
        output_dir=tmp_path / "out",
        as_of_date=date(2026, 10, 25),
        radius_km=10.0,
        max_age_days=365,
        land_type="tarla",
    )

    frame = pd.read_csv(result.output_csv)
    a = frame.loc[frame["cell_id"] == "A"].iloc[0]
    b = frame.loc[frame["cell_id"] == "B"].iloc[0]

    assert a["used_rows"] >= 8
    assert a["confidence_label"] in {"MEDIUM", "HIGH"}
    assert bool(a["known"]) is True
    assert b["confidence_label"] == "NONE"
    assert bool(b["known"]) is False
