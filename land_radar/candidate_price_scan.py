from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path

import pandas as pd

from .inflation import CPIIndex, add_real_price_columns
from .pricing import PriceDataError, prepare_price_data, summarize_comparables


@dataclass(frozen=True)
class CandidatePriceScanResult:
    candidate_count: int
    known_count: int
    low_confidence_count: int
    no_comparable_count: int
    output_csv: str
    summary_json: str


def _bool_known(confidence: str) -> bool:
    return confidence in {"MEDIUM", "HIGH"}


def run_candidate_price_scan(
    *,
    candidate_csv: str | Path = "data/output/deep_scan/deep_scan_top30.csv",
    comparable_csv: str | Path,
    output_dir: str | Path = "data/output/price_scan",
    as_of_date: date,
    radius_km: float = 10.0,
    max_age_days: int = 730,
    land_type: str | None = None,
    cpi_csv: str | Path | None = None,
) -> CandidatePriceScanResult:
    candidate_path = Path(candidate_csv)
    comparable_path = Path(comparable_csv)
    if not candidate_path.exists():
        raise FileNotFoundError(f"Candidate CSV not found: {candidate_path}")
    if not comparable_path.exists():
        raise FileNotFoundError(f"Comparable CSV not found: {comparable_path}")
    if radius_km <= 0:
        raise ValueError("radius_km must be positive")

    candidates = pd.read_csv(candidate_path)
    required_candidate = {"cell_id", "center_lat", "center_lon"}
    missing = sorted(required_candidate - set(candidates.columns))
    if missing:
        raise ValueError(
            "Candidate CSV missing columns: " + ", ".join(missing)
        )

    comparables = pd.read_csv(comparable_path)
    cpi = None
    if cpi_csv is not None:
        cpi_path = Path(cpi_csv)
        if cpi_path.exists():
            cpi = CPIIndex.from_frame(pd.read_csv(cpi_path))

    rows: list[dict] = []
    for candidate in candidates.itertuples(index=False):
        cell_id = str(candidate.cell_id)
        lat = float(candidate.center_lat)
        lon = float(candidate.center_lon)

        try:
            prepared, input_rows = prepare_price_data(
                comparables,
                as_of_date=as_of_date,
                max_age_days=max_age_days,
                subject_lat=lat,
                subject_lon=lon,
                max_distance_km=radius_km,
                land_type=land_type,
                apply_outlier_filter=(cpi is None),
            )

            basis = "nominal"
            if cpi is not None and not prepared.empty:
                adjusted = add_real_price_columns(
                    prepared,
                    cpi,
                    reference_date=as_of_date,
                )
                adjusted["nominal_price_tl"] = adjusted["price_tl"]
                adjusted["nominal_price_per_m2"] = (
                    adjusted["price_tl"] / adjusted["area_m2"]
                )
                adjusted["price_tl"] = adjusted["real_price_tl"]
                prepared, _ = prepare_price_data(
                    adjusted,
                    as_of_date=as_of_date,
                    max_age_days=max_age_days,
                    subject_lat=lat,
                    subject_lon=lon,
                    max_distance_km=radius_km,
                    land_type=land_type,
                    apply_outlier_filter=True,
                )
                basis = f"real_{as_of_date.isoformat()}"

            if prepared.empty:
                raise PriceDataError(
                    "No comparable observations remain after filtering"
                )

            summary = summarize_comparables(
                prepared,
                input_rows=input_rows,
            )
            known = _bool_known(summary.confidence_label)
            rows.append(
                {
                    "cell_id": cell_id,
                    "checked": True,
                    "known": known,
                    "price_basis": basis,
                    "radius_km": radius_km,
                    "max_age_days": max_age_days,
                    "land_type": land_type,
                    "input_rows": summary.input_rows,
                    "used_rows": summary.used_rows,
                    "median_price_per_m2": summary.median_price_per_m2,
                    "p25_price_per_m2": summary.p25_price_per_m2,
                    "p75_price_per_m2": summary.p75_price_per_m2,
                    "iqr_price_per_m2": summary.iqr_price_per_m2,
                    "dispersion_ratio": summary.dispersion_ratio,
                    "median_age_days": summary.median_age_days,
                    "confidence_label": summary.confidence_label,
                    "source_mix": json.dumps(
                        dict(summary.source_mix),
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    "reason": (
                        ""
                        if known
                        else "comparable_confidence_below_medium"
                    ),
                }
            )
        except PriceDataError as exc:
            rows.append(
                {
                    "cell_id": cell_id,
                    "checked": True,
                    "known": False,
                    "price_basis": (
                        f"real_{as_of_date.isoformat()}"
                        if cpi is not None
                        else "nominal"
                    ),
                    "radius_km": radius_km,
                    "max_age_days": max_age_days,
                    "land_type": land_type,
                    "input_rows": len(comparables),
                    "used_rows": 0,
                    "median_price_per_m2": None,
                    "p25_price_per_m2": None,
                    "p75_price_per_m2": None,
                    "iqr_price_per_m2": None,
                    "dispersion_ratio": None,
                    "median_age_days": None,
                    "confidence_label": "NONE",
                    "source_mix": "{}",
                    "reason": str(exc),
                }
            )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_csv = output_dir / "price_top30.csv"
    summary_json = output_dir / "price_scan_summary.json"

    frame = pd.DataFrame(rows)
    frame.to_csv(
        output_csv,
        index=False,
        encoding="utf-8-sig",
    )

    known_count = int(frame["known"].fillna(False).sum())
    low_count = int((frame["confidence_label"] == "LOW").sum())
    none_count = int((frame["confidence_label"] == "NONE").sum())

    summary_json.write_text(
        json.dumps(
            {
                "candidate_count": len(frame),
                "known_count": known_count,
                "low_confidence_count": low_count,
                "no_comparable_count": none_count,
                "as_of_date": as_of_date.isoformat(),
                "radius_km": radius_km,
                "max_age_days": max_age_days,
                "land_type": land_type,
                "cpi_adjusted": cpi is not None,
                "known_rule": (
                    "Price layer is known only when comparable confidence is "
                    "MEDIUM or HIGH."
                ),
                "warning": (
                    "This is a local comparable reference distribution, not "
                    "a parcel valuation or Mispricing Score."
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return CandidatePriceScanResult(
        candidate_count=len(frame),
        known_count=known_count,
        low_confidence_count=low_count,
        no_comparable_count=none_count,
        output_csv=str(output_csv),
        summary_json=str(summary_json),
    )
