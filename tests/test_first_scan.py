import json
from pathlib import Path

from land_radar.first_scan import export_first_scan
from land_radar.urban_scan import UrbanScanRecord


def _record(cell_id: str, acceleration: float, signal: str) -> UrbanScanRecord:
    return UrbanScanRecord(
        cell_id=cell_id,
        center_lat=40.0,
        center_lon=29.0,
        built_2010_m2=100.0,
        built_2015_m2=150.0,
        built_2020_m2=300.0,
        cagr_2010_2015_pct=8.0,
        cagr_2015_2020_pct=14.0,
        acceleration_pp_per_year=acceleration,
        occupied_share_acceleration_pp=5.0,
        signal=signal,
    )


def test_export_first_scan_outputs_csv_geojson_summary(tmp_path: Path):
    ranked = [
        _record("A", 5.0, "accelerating"),
        _record("B", 3.0, "accelerating"),
        _record("C", -1.0, "decelerating"),
    ]

    result = export_first_scan(
        ranked,
        top_n=2,
        output_dir=tmp_path,
    )

    assert result.scanned_cells == 3
    assert result.top_cells == 2
    assert Path(result.output_csv).exists()
    assert Path(result.output_geojson).exists()
    assert Path(result.output_summary_json).exists()

    payload = json.loads(
        Path(result.output_geojson).read_text(encoding="utf-8")
    )
    assert payload["type"] == "FeatureCollection"
    assert len(payload["features"]) == 2
    assert payload["features"][0]["properties"]["rank"] == 1

    summary = json.loads(
        Path(result.output_summary_json).read_text(encoding="utf-8")
    )
    assert summary["accelerating_cells"] == 2
    assert summary["decelerating_cells"] == 1
