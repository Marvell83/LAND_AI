from pathlib import Path

import pandas as pd

from land_radar.deep_scan import run_deep_scan


def _first_scan_csv(path: Path) -> None:
    rows = []
    for rank in range(1, 6):
        rows.append(
            {
                "rank": rank,
                "cell_id": f"C{rank}",
                "center_lat": 40.0 + rank * 0.01,
                "center_lon": 29.0,
                "built_2010_m2": 100.0,
                "built_2015_m2": 150.0,
                "built_2020_m2": 200.0 + rank * 10,
                "cagr_2010_2015_pct": 8.0,
                "cagr_2015_2020_pct": 10.0 + rank,
                "acceleration_pp_per_year": 1.0 + rank,
                "occupied_share_acceleration_pp": 2.0,
                "signal": "accelerating",
            }
        )
    pd.DataFrame(rows).to_csv(path, index=False)


def test_deep_scan_preserves_unknown_layers_as_gaps(tmp_path: Path):
    input_csv = tmp_path / "first.csv"
    _first_scan_csv(input_csv)

    result = run_deep_scan(
        first_scan_csv=input_csv,
        output_dir=tmp_path / "out",
        cell_km=5.0,
        final_top_n=3,
        terrain_client=None,
        hazard_registry_path=None,
        geometry_registry_path=None,
    )

    assert result.input_candidates == 5
    assert result.pass_count == 0
    assert result.pass_with_gaps_count == 5
    assert result.drop_count == 0
    assert result.finalists == 3
    assert "terrain_missing" in result.notes
    assert "hazard_registry_missing" in result.notes
    assert "geometry_registry_missing" in result.notes

    final_frame = pd.read_csv(result.output_final_csv)
    assert len(final_frame) == 3
    assert all(final_frame["status"] == "PASS_WITH_GAPS")
    assert all(final_frame["reasons"].str.contains("terrain_unknown"))
    assert all(final_frame["reasons"].str.contains("hazard_unknown"))
