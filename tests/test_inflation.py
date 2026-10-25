from datetime import date

import pandas as pd
import pytest

from land_radar.inflation import CPIIndex, InflationDataError, add_real_price_columns


def test_cpi_factor_and_adjustment():
    frame = pd.DataFrame(
        [
            {"date": "2025-07-01", "index": 100.0},
            {"date": "2026-07-01", "index": 130.0},
        ]
    )
    cpi = CPIIndex.from_frame(frame)
    assert cpi.factor(date(2025, 7, 15), date(2026, 7, 20)) == 1.3
    assert cpi.adjust(1_000_000, date(2025, 7, 1), date(2026, 7, 1)) == 1_300_000


def test_missing_month_rejected():
    cpi = CPIIndex.from_frame(
        pd.DataFrame([{"date": "2025-07-01", "index": 100.0}])
    )
    with pytest.raises(InflationDataError):
        cpi.factor(date(2025, 7, 1), date(2026, 7, 1))


def test_add_real_price_columns():
    cpi = CPIIndex.from_frame(
        pd.DataFrame(
            [
                {"date": "2025-07-01", "index": 100.0},
                {"date": "2026-07-01", "index": 125.0},
            ]
        )
    )
    prices = pd.DataFrame(
        [
            {
                "observed_date": "2025-07-10",
                "price_tl": 1_000_000,
                "area_m2": 1000,
            }
        ]
    )
    adjusted = add_real_price_columns(
        prices,
        cpi,
        reference_date=date(2026, 7, 15),
    )
    assert adjusted.loc[0, "real_price_tl"] == 1_250_000
    assert adjusted.loc[0, "real_price_per_m2"] == 1250.0
