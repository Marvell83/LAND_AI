from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math
from typing import Iterable

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = ("observed_date", "price_tl", "area_m2")
OPTIONAL_COLUMNS = (
    "source_type",
    "lat",
    "lon",
    "land_type",
    "province",
    "district",
    "neighborhood",
    "listing_id",
)


class PriceDataError(ValueError):
    pass


@dataclass(frozen=True)
class ComparableSummary:
    input_rows: int
    valid_rows: int
    used_rows: int
    median_price_per_m2: float
    p25_price_per_m2: float
    p75_price_per_m2: float
    iqr_price_per_m2: float
    dispersion_ratio: float
    median_age_days: float
    source_mix: tuple[tuple[str, int], ...]
    confidence_label: str


@dataclass(frozen=True)
class ComparableGap:
    subject_price_per_m2: float
    comparable_median_price_per_m2: float
    gap_pct: float
    label: str


def _haversine_km(
    lat1: float,
    lon1: float,
    lat2: np.ndarray,
    lon2: np.ndarray,
) -> np.ndarray:
    radius = 6371.0088
    p1 = math.radians(lat1)
    p2 = np.radians(lat2)
    dlat = p2 - p1
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlon / 2) ** 2
    return radius * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def prepare_price_data(
    frame: pd.DataFrame,
    *,
    as_of_date: date,
    max_age_days: int = 730,
    subject_lat: float | None = None,
    subject_lon: float | None = None,
    max_distance_km: float | None = None,
    land_type: str | None = None,
) -> tuple[pd.DataFrame, int]:
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise PriceDataError(
            "Missing required price columns: " + ", ".join(missing)
        )
    if max_age_days <= 0:
        raise PriceDataError("max_age_days must be positive")
    if max_distance_km is not None and max_distance_km <= 0:
        raise PriceDataError("max_distance_km must be positive")

    df = frame.copy()
    input_rows = len(df)

    df["observed_date"] = pd.to_datetime(
        df["observed_date"],
        errors="coerce",
    ).dt.date
    df["price_tl"] = pd.to_numeric(df["price_tl"], errors="coerce")
    df["area_m2"] = pd.to_numeric(df["area_m2"], errors="coerce")

    valid = (
        df["observed_date"].notna()
        & df["price_tl"].gt(0)
        & df["area_m2"].gt(0)
    )
    df = df.loc[valid].copy()

    # Point-in-time discipline: never use observations after the analysis cutoff.
    df = df.loc[df["observed_date"] <= as_of_date].copy()
    df["age_days"] = df["observed_date"].map(
        lambda value: (as_of_date - value).days
    )
    df = df.loc[df["age_days"].between(0, max_age_days)].copy()

    if land_type and "land_type" in df.columns:
        target = land_type.casefold().strip()
        df = df.loc[
            df["land_type"].fillna("").astype(str).str.casefold().str.strip() == target
        ].copy()

    df["price_per_m2"] = df["price_tl"] / df["area_m2"]

    if (
        subject_lat is not None
        and subject_lon is not None
        and max_distance_km is not None
        and "lat" in df.columns
        and "lon" in df.columns
    ):
        lat = pd.to_numeric(df["lat"], errors="coerce")
        lon = pd.to_numeric(df["lon"], errors="coerce")
        geo_valid = lat.notna() & lon.notna()
        df = df.loc[geo_valid].copy()
        lat = lat.loc[geo_valid].to_numpy(dtype="float64")
        lon = lon.loc[geo_valid].to_numpy(dtype="float64")
        df["distance_km"] = _haversine_km(
            float(subject_lat),
            float(subject_lon),
            lat,
            lon,
        )
        df = df.loc[df["distance_km"] <= max_distance_km].copy()

    # Robust outlier control on log price/m². This avoids a few extreme listings
    # dominating the comparable distribution.
    if len(df) >= 5:
        log_values = np.log(df["price_per_m2"].to_numpy(dtype="float64"))
        median_log = float(np.median(log_values))
        mad = float(np.median(np.abs(log_values - median_log)))
        if mad > 1e-12:
            robust_z = 0.6745 * (log_values - median_log) / mad
            df["robust_z_log_ppm"] = robust_z
            df = df.loc[np.abs(robust_z) <= 3.5].copy()

    return df.reset_index(drop=True), input_rows


def summarize_comparables(
    prepared: pd.DataFrame,
    *,
    input_rows: int | None = None,
) -> ComparableSummary:
    if prepared.empty:
        raise PriceDataError("No comparable observations remain after filtering")

    values = prepared["price_per_m2"].to_numpy(dtype="float64")
    median_ppm = float(np.median(values))
    p25 = float(np.percentile(values, 25))
    p75 = float(np.percentile(values, 75))
    iqr = p75 - p25
    dispersion = iqr / median_ppm if median_ppm > 0 else float("inf")
    median_age = float(np.median(prepared["age_days"].to_numpy(dtype="float64")))

    if "source_type" in prepared.columns:
        source_counts = (
            prepared["source_type"]
            .fillna("unspecified")
            .astype(str)
            .value_counts()
            .to_dict()
        )
    else:
        source_counts = {"unspecified": len(prepared)}

    n = len(prepared)
    if n >= 20 and dispersion <= 0.30 and median_age <= 180:
        confidence = "HIGH"
    elif n >= 8 and dispersion <= 0.60 and median_age <= 365:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    return ComparableSummary(
        input_rows=int(input_rows if input_rows is not None else n),
        valid_rows=n,
        used_rows=n,
        median_price_per_m2=round(median_ppm, 2),
        p25_price_per_m2=round(p25, 2),
        p75_price_per_m2=round(p75, 2),
        iqr_price_per_m2=round(iqr, 2),
        dispersion_ratio=round(dispersion, 4),
        median_age_days=round(median_age, 1),
        source_mix=tuple(sorted(source_counts.items())),
        confidence_label=confidence,
    )


def comparable_gap(
    *,
    subject_price_tl: float,
    subject_area_m2: float,
    comparable_median_price_per_m2: float,
) -> ComparableGap:
    if subject_price_tl <= 0 or subject_area_m2 <= 0:
        raise PriceDataError("Subject price and area must be positive")
    if comparable_median_price_per_m2 <= 0:
        raise PriceDataError("Comparable median price/m² must be positive")

    subject_ppm = subject_price_tl / subject_area_m2
    gap = (comparable_median_price_per_m2 / subject_ppm - 1.0) * 100.0

    if gap >= 15:
        label = "below_comparable_median"
    elif gap <= -15:
        label = "above_comparable_median"
    else:
        label = "near_comparable_median"

    return ComparableGap(
        subject_price_per_m2=round(subject_ppm, 2),
        comparable_median_price_per_m2=round(comparable_median_price_per_m2, 2),
        gap_pct=round(gap, 2),
        label=label,
    )


def expected_csv_columns() -> tuple[str, ...]:
    return REQUIRED_COLUMNS + OPTIONAL_COLUMNS
