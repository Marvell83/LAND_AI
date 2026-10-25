import json
from pathlib import Path

import pandas as pd

from land_radar.selection_gate import run_selection_gate


def _packet(cell_id: str, *, planning: bool, price: bool):
    return {
        "cell_id": cell_id,
        "funnel": {
            "status": "PASS",
            "urban_rank": 1,
            "reasons": [],
        },
        "urban_history": {
            "acceleration_pp_per_year": 5.0,
        },
        "terrain": {"known": True},
        "hazard": {"known": True, "hard_veto": False},
        "catalyst": {"known": True},
        "sentinel_recent_change": {"delta_ndvi": -0.1},
        "planning_legal": {"known": planning},
        "price": {"known": price},
        "evidence_coverage": {"coverage_pct": 100.0},
    }


def test_gate_blocks_when_planning_missing(tmp_path: Path):
    payload = {
        "candidates": [
            _packet("A", planning=False, price=True),
            _packet("B", planning=True, price=True),
        ]
    }
    source = tmp_path / "packets.json"
    source.write_text(json.dumps(payload), encoding="utf-8")

    result = run_selection_gate(
        evidence_json=source,
        output_dir=tmp_path / "out",
        target_count=2,
    )

    assert result.eligible_count == 1
    assert result.selection_ready is False

    frame = pd.read_csv(result.output_csv)
    a = frame.loc[frame["cell_id"] == "A"].iloc[0]
    assert "planning_legal" in a["missing_required_layers"]


def test_gate_ready_when_target_has_all_evidence(tmp_path: Path):
    payload = {
        "candidates": [
            _packet("A", planning=True, price=True),
            _packet("B", planning=True, price=True),
        ]
    }
    source = tmp_path / "packets.json"
    source.write_text(json.dumps(payload), encoding="utf-8")

    result = run_selection_gate(
        evidence_json=source,
        output_dir=tmp_path / "out",
        target_count=2,
    )

    assert result.eligible_count == 2
    assert result.selection_ready is True
