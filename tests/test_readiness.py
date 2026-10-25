from pathlib import Path

from land_radar.readiness import check_data_readiness


def test_readiness_reports_missing_required_ghsl(tmp_path: Path):
    report = check_data_readiness(
        ghsl_dir=tmp_path / "ghsl",
        hazard_registry_path=tmp_path / "hazards.geojson",
        geometry_registry_path=tmp_path / "geometry.geojson",
        price_csv_path=tmp_path / "prices.csv",
    )
    assert report.required_ready is False
    assert all(
        item.status == "MISSING"
        for item in report.items
        if item.key.startswith("ghsl_")
    )


def test_optional_files_do_not_control_required_ready(tmp_path: Path):
    ghsl = tmp_path / "ghsl"
    ghsl.mkdir()
    for epoch in (2010, 2015, 2020):
        (ghsl / f"GHS_BUILT_S_E{epoch}_TEST.tif").write_bytes(b"placeholder")

    report = check_data_readiness(
        ghsl_dir=ghsl,
        cdse_credentials_available=False,
        hazard_registry_path=tmp_path / "missing.geojson",
        geometry_registry_path=tmp_path / "missing2.geojson",
        price_csv_path=tmp_path / "missing.csv",
    )

    assert report.required_ready is True
    assert any(
        item.status == "OPTIONAL_MISSING"
        for item in report.items
    )
