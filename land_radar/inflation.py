from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd


class InflationDataError(ValueError):
    pass


@dataclass(frozen=True)
class CPIIndex:
    by_month: dict[str, float]

    @classmethod
    def from_frame(cls, frame: pd.DataFrame) -> "CPIIndex":
        required = {"date", "index"}
        missing = sorted(required - set(frame.columns))
        if missing:
            raise InflationDataError(
                "Missing CPI columns: " + ", ".join(missing)
            )

        df = frame.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["index"] = pd.to_numeric(df["index"], errors="coerce")
        df = df.loc[df["date"].notna() & df["index"].gt(0)].copy()
        if df.empty:
            raise InflationDataError("CPI dataset contains no valid rows")

        df["month"] = df["date"].dt.to_period("M").astype(str)
        df = df.sort_values("date").drop_duplicates("month", keep="last")
        return cls(
            by_month={
                str(row.month): float(row.index)
                for row in df[["month", "index"]].itertuples(index=False)
            }
        )

    @staticmethod
    def month_key(value: date) -> str:
        return f"{value.year:04d}-{value.month:02d}"

    def value(self, value_date: date) -> float:
        key = self.month_key(value_date)
        if key not in self.by_month:
            raise InflationDataError(f"CPI index missing for month {key}")
        return self.by_month[key]

    def factor(self, from_date: date, to_date: date) -> float:
        source = self.value(from_date)
        target = self.value(to_date)
        return target / source

    def adjust(self, amount: float, from_date: date, to_date: date) -> float:
        if amount < 0:
            raise InflationDataError("Amount cannot be negative")
        return amount * self.factor(from_date, to_date)


def add_real_price_columns(
    price_frame: pd.DataFrame,
    cpi: CPIIndex,
    *,
    reference_date: date,
) -> pd.DataFrame:
    required = {"observed_date", "price_tl", "area_m2"}
    missing = sorted(required - set(price_frame.columns))
    if missing:
        raise InflationDataError(
            "Price dataset missing columns: " + ", ".join(missing)
        )

    df = price_frame.copy()
    observed = pd.to_datetime(df["observed_date"], errors="coerce").dt.date
    if observed.isna().any():
        raise InflationDataError("Price dataset contains invalid observed_date")

    real_prices: list[float] = []
    for amount, obs_date in zip(
        pd.to_numeric(df["price_tl"], errors="coerce"),
        observed,
    ):
        if pd.isna(amount) or float(amount) <= 0:
            raise InflationDataError("Price dataset contains invalid price_tl")
        real_prices.append(
            cpi.adjust(float(amount), obs_date, reference_date)
        )

    area = pd.to_numeric(df["area_m2"], errors="coerce")
    if area.isna().any() or (area <= 0).any():
        raise InflationDataError("Price dataset contains invalid area_m2")

    df["real_price_tl"] = real_prices
    df["real_price_per_m2"] = df["real_price_tl"] / area
    df["real_price_reference_date"] = reference_date.isoformat()
    return df
