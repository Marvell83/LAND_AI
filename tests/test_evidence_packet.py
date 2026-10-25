import json
from pathlib import Path

import pandas as pd

from land_radar.evidence_packet import build_evidence_packets


def test_evidence_packet_marks_missing_price_and_planning(tmp_path: Path):
    deep = tmp_path / "deep.csv"
    pd.DataFrame(
        [
            {
                "cell_id": "A",
                "center_lat": 40.0,
                "center_lon": 29.0,
                "urban_rank": 1,
                "acceleration_pp_per_year": 5.0,
                "cagr_2015_2020_pct": 12.0,
                "p90_slope_deg": 5.0,
                "nearest_catalyst_km": 4.0,
                "catalyst_stage_max": 4,
                "hard_veto": False,
                "max_hazard_severity": 2,
                "status": "PASS",
                "reasons": "",
            }
        ]
    ).to_csv(deep, index=False)

    sentinel = tmp_path / "sentinel.csv"
    pd.DataFrame(
        [
            {
                "cell_id": "A",
                "center_lat": 40.0,
                "center_lon": 29.0,
                "delta_ndvi": -0.1,
                "delta_ndbi": 0.05,
            }
        ]
    ).to_csv(sentinel, index=False)

    result = build_evidence_packets(
        deep_scan_csv=deep,
        sentinel_csv=sentinel,
        output_dir=tmp_path / "out",
    )

    payload = json.loads(
        Path(result.output_master_json).read_text(encoding="utf-8")
    )
    packet = payload["candidates"][0]

    assert packet["sentinel_recent_change"] is not None
    assert packet["evidence_coverage"]["coverage_pct"] == 71.4
    assert "planning_legal" in packet["evidence_coverage"]["missing_layers"]
    assert "price" in packet["evidence_coverage"]["missing_layers"]


def test_evidence_packet_preserves_unknown_hazard(tmp_path: Path):
    deep = tmp_path / "deep.csv"
    pd.DataFrame(
        [
            {
                "cell_id": "A",
                "center_lat": 40.0,
                "center_lon": 29.0,
                "urban_rank": 1,
                "acceleration_pp_per_year": 5.0,
                "cagr_2015_2020_pct": 12.0,
                "p90_slope_deg": None,
                "nearest_catalyst_km": None,
                "catalyst_stage_max": None,
                "hard_veto": False,
                "max_hazard_severity": None,
                "status": "PASS_WITH_GAPS",
                "reasons": "terrain_unknown, hazard_unknown, catalyst_unknown",
            }
        ]
    ).to_csv(deep, index=False)

    result = build_evidence_packets(
        deep_scan_csv=deep,
        sentinel_csv=None,
        output_dir=tmp_path / "out",
    )
    payload = json.loads(
        Path(result.output_master_json).read_text(encoding="utf-8")
    )
    packet = payload["candidates"][0]

    assert packet["hazard"]["known"] is False
    assert packet["terrain"]["known"] is False
    assert packet["catalyst"]["known"] is False
    assert packet["evidence_coverage"]["known_layers"] == 1


def test_evidence_packet_includes_partial_official_constraints(tmp_path: Path):
    deep = tmp_path / "deep.csv"
    pd.DataFrame(
        [
            {
                "cell_id": "A",
                "center_lat": 40.0,
                "center_lon": 29.0,
                "urban_rank": 1,
                "acceleration_pp_per_year": 5.0,
                "cagr_2015_2020_pct": 12.0,
                "p90_slope_deg": 5.0,
                "nearest_catalyst_km": 4.0,
                "catalyst_stage_max": 4,
                "hard_veto": False,
                "max_hazard_severity": 2,
                "status": "PASS",
                "reasons": "",
            }
        ]
    ).to_csv(deep, index=False)

    protected = tmp_path / "protected.csv"
    pd.DataFrame(
        [
            {
                "cell_id": "A",
                "checked": True,
                "finding_count": 1,
                "intersecting_count": 1,
                "legal_review_required": True,
                "max_overlap_ratio": 0.25,
                "nearest_constraint_km": 0.0,
            }
        ]
    ).to_csv(protected, index=False)

    flood = tmp_path / "flood.csv"
    pd.DataFrame(
        [
            {
                "cell_id": "A",
                "checked": True,
                "finding_count": 1,
                "max_severity": 3,
                "max_overlap_ratio": 0.10,
                "nearest_hazard_km": 0.0,
            }
        ]
    ).to_csv(flood, index=False)

    result = build_evidence_packets(
        deep_scan_csv=deep,
        sentinel_csv=None,
        protected_csv=protected,
        flood_csv=flood,
        output_dir=tmp_path / "out",
    )

    payload = json.loads(
        Path(result.output_master_json).read_text(encoding="utf-8")
    )
    packet = payload["candidates"][0]

    assert packet["planning_legal"]["protected_area"]["checked"] is True
    assert packet["planning_legal"]["protected_area"]["legal_review_required"] is True
    assert packet["planning_legal"]["eplan"]["checked"] is False
    assert packet["planning_legal"]["known"] is False
    assert packet["hazard"]["official_flood"]["checked"] is True
    assert packet["hazard"]["official_flood"]["max_severity"] == 3
