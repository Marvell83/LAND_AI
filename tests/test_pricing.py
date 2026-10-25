from datetime import date

import pandas as pd
import pytest

from land_radar.pricing import (
    PriceDataError,
    comparable_gap,
    prepare_price_data,
    summarize_comparables,
)


def _frame():
    return pd.DataFrame(
        [
            {"observed_date": "2026-01-01", "price_tl": 1_000_000, "area_m2": 1000, "source_type": "asking", "lat": 40.0, "lon": 29.0, "land_type": "tarla"},
            {"observed_date": "2026-02-01", "price_tl": 1_100_000, "area_m2": 1000, "source_type": "asking", "lat": 40.01, "lon": 29.0, "land_type": "tarla"},
            {"observed_date": "2026-03-01", "price_tl": 900_000, "area_m2": 1000, "source_type": "asking", "lat": 40.0, "lon": 29.01, "land_type": "tarla"},
            {"observed_date": "2026-04-01", "price_tl": 1_050_000, "area_m2": 1000, "source_type": "asking", "lat": 40.01, "lon": 29.01, "land_type": "tarla"},
            {"observed_date": "2026-05-01", "price_tl": 100_000_000, "area_m2": 1000, "source_type": "asking", "lat": 40.0, "lon": 29.0, "land_type": "tarla"},
            {"observed_date": "2027-01-01", "price_tl": 1_200_000, "area_m2": 1000, "source_type": "asking", "lat": 40.0, "lon": 29.0, "land_type": "tarla"},
        ]
    )


def test_prepare_enforces_point_in_time_and_filters_future():
    prepared, input_rows = prepare_price_data(
        _frame(),
        as_of_date=date(2026, 12, 31),
        max_age_days=365,
        land_type="tarla",
    )
    assert input_rows == 6
    assert all(prepared["observed_date"] <= date(2026, 12, 31))
    assert len(prepared) == 4  # future row excluded; extreme outlier trimmed


def test_prepare_distance_filter():
    prepared, _ = prepare_price_data(
        _frame(),
        as_of_date=date(2026, 12, 31),
        max_age_days=365,
        subject_lat=40.0,
        subject_lon=29.0,
        max_distance_km=1.0,
        land_type="tarla",
    )
    assert "distance_km" in prepared.columns
    assert prepared["distance_km"].max() <= 1.0


def test_summary_and_gap():
    prepared, input_rows = prepare_price_data(
        _frame(),
        as_of_date=date(2026, 12, 31),
        max_age_days=365,
        land_type="tarla",
    )
    summary = summarize_comparables(prepared, input_rows=input_rows)
    assert 900 <= summary.median_price_per_m2 <= 1100
    assert summary.confidence_label in {"LOW", "MEDIUM", "HIGH"}

    gap = comparable_gap(
        subject_price_tl=800_000,
        subject_area_m2=1000,
        comparable_median_price_per_m2=summary.median_price_per_m2,
    )
    assert gap.subject_price_per_m2 == 800.0
    assert gap.gap_pct > 0
    assert gap.label == "below_comparable_median"


def test_missing_columns_rejected():
    with pytest.raises(PriceDataError):
        prepare_price_data(
            pd.DataFrame([{"price_tl": 1_000_000}]),
            as_of_date=date(2026, 1, 1),
        )
