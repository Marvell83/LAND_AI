from __future__ import annotations

from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

from .plan_evidence import PlanEvidence, stage_from_text
from .plan_registry import save_plan_registry


class PlanImportError(ValueError):
    pass


REQUIRED_COLUMNS = (
    "plan_id",
    "title",
    "plan_type",
    "stage",
    "source",
    "source_url",
)


def _date_or_none(value):
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    return date.fromisoformat(str(value).strip())


def _bool_value(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or pd.isna(value):
        return False
    return str(value).strip().casefold() in {
        "1", "true", "yes", "evet", "verified", "dogrulandi", "doğrulandı"
    }


def _https_url(value: str) -> str:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise PlanImportError(f"Plan source_url must be HTTPS: {url}")
    return url


def import_plan_csv(
    csv_path: str | Path,
    output_path: str | Path = "data/processed/plan_registry.json",
) -> list[PlanEvidence]:
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Plan CSV not found: {csv_path}")

    frame = pd.read_csv(csv_path)
    missing = [
        column
        for column in REQUIRED_COLUMNS
        if column not in frame.columns
    ]
    if missing:
        raise PlanImportError(
            "Plan CSV missing columns: " + ", ".join(missing)
        )

    plans: list[PlanEvidence] = []
    for index, row in frame.iterrows():
        stage = stage_from_text(str(row["stage"]))
        if stage.name == "UNKNOWN":
            raise PlanImportError(
                f"Row {index + 2}: unsupported/unknown plan stage {row['stage']!r}"
            )

        properties = {}
        for key in (
            "cell_id",
            "province",
            "district",
            "neighborhood",
            "min_lon",
            "min_lat",
            "max_lon",
            "max_lat",
            "decision_no",
            "pin",
        ):
            if key in frame.columns and not pd.isna(row.get(key)):
                properties[key] = row.get(key)

        scale = None
        if "scale_denominator" in frame.columns and not pd.isna(
            row.get("scale_denominator")
        ):
            scale = int(row["scale_denominator"])

        confidence = 95.0
        if "confidence" in frame.columns and not pd.isna(row.get("confidence")):
            confidence = float(row["confidence"])

        plan = PlanEvidence(
            plan_id=str(row["plan_id"]).strip(),
            title=str(row["title"]).strip(),
            plan_type=str(row["plan_type"]).strip(),
            stage=stage,
            source=str(row["source"]).strip(),
            source_url=_https_url(row["source_url"]),
            scale_denominator=scale,
            published_date=_date_or_none(row.get("published_date")),
            decision_date=_date_or_none(row.get("decision_date")),
            effective_date=_date_or_none(row.get("effective_date")),
            suspension_start=_date_or_none(row.get("suspension_start")),
            suspension_end=_date_or_none(row.get("suspension_end")),
            observed_date=_date_or_none(row.get("observed_date")),
            confidence=confidence,
            geometry_verified=_bool_value(row.get("geometry_verified")),
            note=str(row.get("note") or "").strip(),
            properties=properties,
        )
        plans.append(plan)

    save_plan_registry(plans, output_path)
    return plans
