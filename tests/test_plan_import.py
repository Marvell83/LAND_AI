from pathlib import Path

import pandas as pd
import pytest

from land_radar.plan_import import PlanImportError, import_plan_csv
from land_radar.plan_registry import load_plan_registry


def test_import_plan_csv_roundtrip(tmp_path: Path):
    source = tmp_path / "plans.csv"
    pd.DataFrame(
        [
            {
                "plan_id": "UIP-123",
                "title": "Example finalized UIP",
                "plan_type": "UİP",
                "stage": "kesinleşmiş",
                "source": "e-Plan",
                "source_url": "https://e-plan.gov.tr/",
                "scale_denominator": 1000,
                "published_date": "2026-01-10",
                "decision_date": "2026-01-05",
                "geometry_verified": True,
                "cell_id": "A",
            }
        ]
    ).to_csv(source, index=False)

    output = tmp_path / "registry.json"
    plans = import_plan_csv(source, output)
    restored = load_plan_registry(output)

    assert len(plans) == 1
    assert restored[0].plan_id == "UIP-123"
    assert restored[0].plan_type == "UIP"
    assert restored[0].geometry_verified is True
    assert restored[0].properties["cell_id"] == "A"


def test_import_rejects_non_https_source(tmp_path: Path):
    source = tmp_path / "plans.csv"
    pd.DataFrame(
        [
            {
                "plan_id": "UIP-1",
                "title": "Bad URL",
                "plan_type": "UIP",
                "stage": "kesinleşmiş",
                "source": "x",
                "source_url": "http://example.com",
            }
        ]
    ).to_csv(source, index=False)

    with pytest.raises(PlanImportError):
        import_plan_csv(source, tmp_path / "out.json")
