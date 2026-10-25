from pathlib import Path
import zipfile

import numpy as np
import rasterio
from rasterio.transform import from_origin
import pytest

from land_radar.ghsl_install import (
    GHSLInstallError,
    install_from_zip,
    validate_ghsl_raster,
)


def _write_mollweide_raster(path: Path, epoch: int) -> Path:
    name = (
        f"GHS_BUILT_S_E{epoch}_GLOBE_R2023A_54009_100_V1_0_TEST.tif"
    )
    target = path / name
    values = np.full((4, 4), 10, dtype="uint16")
    with rasterio.open(
        target,
        "w",
        driver="GTiff",
        height=4,
        width=4,
        count=1,
        dtype="uint16",
        crs="+proj=moll +lon_0=0 +datum=WGS84 +units=m +no_defs",
        transform=from_origin(0.0, 400.0, 100.0, 100.0),
        nodata=65535,
    ) as dst:
        dst.write(values, 1)
    return target


def test_validate_expected_raster(tmp_path: Path):
    path = _write_mollweide_raster(tmp_path, 2020)
    item = validate_ghsl_raster(path)
    assert item.epoch == 2020
    assert item.dtype == "uint16"


def test_install_from_zip_extracts_requested_epochs(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    p2010 = _write_mollweide_raster(source_dir, 2010)
    p2015 = _write_mollweide_raster(source_dir, 2015)
    p2020 = _write_mollweide_raster(source_dir, 2020)

    archive = tmp_path / "ghsl.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for path in (p2010, p2015, p2020):
            zf.write(path, arcname=f"nested/{path.name}")
        zf.writestr("../../unsafe.txt", "bad")

    destination = tmp_path / "installed"
    installed = install_from_zip(
        archive,
        destination,
        epochs=(2010, 2015, 2020),
    )

    assert {item.epoch for item in installed} == {2010, 2015, 2020}
    assert len(list(destination.glob("*.tif"))) == 3


def test_install_rejects_zip_without_target_dataset(tmp_path: Path):
    archive = tmp_path / "other.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("readme.txt", "nothing here")

    with pytest.raises(GHSLInstallError):
        install_from_zip(archive, tmp_path / "dest")
