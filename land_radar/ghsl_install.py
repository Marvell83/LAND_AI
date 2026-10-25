from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import tempfile
from typing import Iterable
from urllib.parse import urlparse
import zipfile

import rasterio
import requests

from .providers.ghsl import epoch_from_filename


OFFICIAL_HOST_SUFFIXES = (
    ".ec.europa.eu",
    ".europa.eu",
)

EXPECTED_NAME_PARTS = (
    "GHS_BUILT_S_E",
    "_GLOBE_R2023A_54009_100_",
)


class GHSLInstallError(RuntimeError):
    pass


@dataclass(frozen=True)
class InstalledRaster:
    epoch: int
    source_name: str
    destination: str
    crs: str
    dtype: str
    nodata: float | int | None
    width: int
    height: int


def _is_official_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    host = parsed.hostname.casefold()
    return any(
        host == suffix.lstrip(".") or host.endswith(suffix)
        for suffix in OFFICIAL_HOST_SUFFIXES
    )


def _safe_member_name(name: str) -> str:
    normalized = name.replace("\\", "/")
    path = Path(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise GHSLInstallError(f"Unsafe ZIP member path: {name}")
    return path.name


def _is_target_tif(name: str, epochs: set[int]) -> bool:
    upper = Path(name).name.upper()
    if not upper.endswith((".TIF", ".TIFF")):
        return False
    if not all(part in upper for part in EXPECTED_NAME_PARTS):
        return False
    epoch = epoch_from_filename(Path(name).name)
    return epoch in epochs


def validate_ghsl_raster(path: str | Path) -> InstalledRaster:
    path = Path(path)
    epoch = epoch_from_filename(path.name)
    if epoch is None:
        raise GHSLInstallError(f"Cannot determine GHSL epoch from filename: {path.name}")

    upper = path.name.upper()
    if not all(part in upper for part in EXPECTED_NAME_PARTS):
        raise GHSLInstallError(
            "Raster filename is not expected GHS-BUILT-S R2023A Mollweide 100m: "
            + path.name
        )

    try:
        with rasterio.open(path) as src:
            crs = str(src.crs) if src.crs is not None else ""
            if "54009" not in crs and "MOLLWEIDE" not in crs.upper():
                raise GHSLInstallError(
                    f"Unexpected CRS for {path.name}: {crs or 'missing'}"
                )
            if src.count != 1:
                raise GHSLInstallError(
                    f"Expected one raster band in {path.name}, got {src.count}"
                )
            dtype = str(src.dtypes[0])
            if dtype not in {"uint16", "int16", "uint32", "int32"}:
                raise GHSLInstallError(
                    f"Unexpected GHSL dtype for {path.name}: {dtype}"
                )

            return InstalledRaster(
                epoch=epoch,
                source_name=path.name,
                destination=str(path),
                crs=crs,
                dtype=dtype,
                nodata=src.nodata,
                width=src.width,
                height=src.height,
            )
    except GHSLInstallError:
        raise
    except Exception as exc:
        raise GHSLInstallError(
            f"Failed to validate GHSL raster {path}: {exc}"
        ) from exc


def install_from_zip(
    zip_path: str | Path,
    destination_dir: str | Path,
    *,
    epochs: Iterable[int] = (2010, 2015, 2020),
) -> list[InstalledRaster]:
    zip_path = Path(zip_path)
    destination_dir = Path(destination_dir)
    epoch_set = {int(epoch) for epoch in epochs}

    if not zip_path.exists():
        raise GHSLInstallError(f"ZIP not found: {zip_path}")

    destination_dir.mkdir(parents=True, exist_ok=True)
    installed: list[InstalledRaster] = []

    try:
        with zipfile.ZipFile(zip_path) as archive:
            members = [
                info
                for info in archive.infolist()
                if not info.is_dir() and _is_target_tif(info.filename, epoch_set)
            ]
            if not members:
                raise GHSLInstallError(
                    f"No target GHS-BUILT-S R2023A 100m epochs found in {zip_path.name}"
                )

            for info in members:
                filename = _safe_member_name(info.filename)
                target = destination_dir / filename

                if target.exists():
                    installed.append(validate_ghsl_raster(target))
                    continue

                with archive.open(info, "r") as source, target.open("wb") as sink:
                    shutil.copyfileobj(source, sink)

                installed.append(validate_ghsl_raster(target))
    except zipfile.BadZipFile as exc:
        raise GHSLInstallError(f"Invalid ZIP file: {zip_path}") from exc

    return installed


def download_official_zip(
    url: str,
    destination: str | Path,
    *,
    timeout: float = 120.0,
    session: requests.Session | None = None,
) -> Path:
    if not _is_official_url(url):
        raise GHSLInstallError(
            "Only HTTPS European Commission / europa.eu GHSL URLs are accepted"
        )

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    client = session or requests.Session()

    try:
        with client.get(
            url,
            stream=True,
            timeout=timeout,
            allow_redirects=True,
            headers={"User-Agent": "LAND-RADAR/0.10 ghsl-installer"},
        ) as response:
            response.raise_for_status()
            final_url = str(response.url)
            if not _is_official_url(final_url):
                raise GHSLInstallError(
                    f"Download redirected outside official EU domains: {final_url}"
                )

            content_type = (response.headers.get("Content-Type") or "").lower()
            if (
                "zip" not in content_type
                and not final_url.lower().endswith(".zip")
            ):
                raise GHSLInstallError(
                    f"Expected ZIP download, got Content-Type={content_type!r}"
                )

            with destination.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
    except GHSLInstallError:
        if destination.exists():
            destination.unlink()
        raise
    except requests.RequestException as exc:
        if destination.exists():
            destination.unlink()
        raise GHSLInstallError(f"GHSL download failed: {exc}") from exc

    return destination


def install_sources(
    *,
    zip_paths: Iterable[str | Path] = (),
    urls: Iterable[str] = (),
    destination_dir: str | Path = "data/raw/ghsl",
    epochs: Iterable[int] = (2010, 2015, 2020),
) -> list[InstalledRaster]:
    destination_dir = Path(destination_dir)
    installed: list[InstalledRaster] = []

    for zip_path in zip_paths:
        installed.extend(
            install_from_zip(
                zip_path,
                destination_dir,
                epochs=epochs,
            )
        )

    urls = list(urls)
    if urls:
        with tempfile.TemporaryDirectory(prefix="land-radar-ghsl-") as temp_dir:
            for index, url in enumerate(urls, start=1):
                archive = download_official_zip(
                    url,
                    Path(temp_dir) / f"source_{index}.zip",
                )
                installed.extend(
                    install_from_zip(
                        archive,
                        destination_dir,
                        epochs=epochs,
                    )
                )

    unique: dict[str, InstalledRaster] = {
        item.destination: item
        for item in installed
    }
    return sorted(
        unique.values(),
        key=lambda item: (item.epoch, item.destination),
    )
