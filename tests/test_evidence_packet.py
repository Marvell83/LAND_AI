import json
from pathlib import Path

import pandas as pd

from land_radar.evidence_packet import build_evidence_packets


def test_evidence_packet_marks_missing_price_and_planning(tmp_path: Path):
    deep = tmp_path / "deep.csv"
    pd.DataFrame(
        [
            {
                "cell_id": "A",
                "center_lat": 40.0,
                "center_lon": 29.0,
                "urban_rank": 1,
                "acceleration_pp_per_year": 5.0,
                "cagr_2015_2020_pct": 12.0,
                "p90_slope_deg": 5.0,
                "nearest_catalyst_km": 4.0,
                "catalyst_stage_max": 4,
                "hard_veto": False,
                "max_hazard_severity": 2,
                "status": "PASS",
                "reasons": "",
            }
        ]
    ).to_csv(deep, index=False)

    sentinel = tmp_path / "sentinel.csv"
    pd.DataFrame(
        [
            {
                "cell_id": "A",
                "center_lat": 40.0,
                "center_lon": 29.0,
                "delta_ndvi": -0.1,
                "delta_ndbi": 0.05,
            }
        ]
    ).to_csv(sentinel, index=False)

    result = build_evidence_packets(
        deep_scan_csv=deep,
        sentinel_csv=sentinel,
        output_dir=tmp_path / "out",
    )

    payload = json.loads(
        Path(result.output_master_json).read_text(encoding="utf-8")
    )
    packet = payload["candidates"][0]

    assert packet["sentinel_recent_change"] is not None
    assert packet["evidence_coverage"]["coverage_pct"] == 71.4
    assert "planning_legal" in packet["evidence_coverage"]["missing_layers"]
    assert "price" in packet["evidence_coverage"]["missing_layers"]


def test_evidence_packet_preserves_unknown_hazard(tmp_path: Path):
    deep = tmp_path / "deep.csv"
    pd.DataFrame(
        [
            {
                "cell_id": "A",
                "center_lat": 40.0,
                "center_lon": 29.0,
                "urban_rank": 1,
                "acceleration_pp_per_year": 5.0,
                "cagr_2015_2020_pct": 12.0,
                "p90_slope_deg": None,
                "nearest_catalyst_km": None,
                "catalyst_stage_max": None,
                "hard_veto": False,
                "max_hazard_severity": None,
                "status": "PASS_WITH_GAPS",
                "reasons": "terrain_unknown, hazard_unknown, catalyst_unknown",
            }
        ]
    ).to_csv(deep, index=False)

    result = build_evidence_packets(
        deep_scan_csv=deep,
        sentinel_csv=None,
        output_dir=tmp_path / "out",
    )
    payload = json.loads(
        Path(result.output_master_json).read_text(encoding="utf-8")
    )
    packet = payload["candidates"][0]

    assert packet["hazard"]["known"] is False
    assert packet["terrain"]["known"] is False
    assert packet["catalyst"]["known"] is False
    assert packet["evidence_coverage"]["known_layers"] == 1


def test_evidence_packet_includes_partial_official_constraints(tmp_path: Path):
    deep = tmp_path / "deep.csv"
    pd.DataFrame(
        [
            {
                "cell_id": "A",
                "center_lat": 40.0,
                "center_lon": 29.0,
                "urban_rank": 1,
                "acceleration_pp_per_year": 5.0,
                "cagr_2015_2020_pct": 12.0,
                "p90_slope_deg": 5.0,
                "nearest_catalyst_km": 4.0,
                "catalyst_stage_max": 4,
                "hard_veto": False,
                "max_hazard_severity": 2,
                "status": "PASS",
                "reasons": "",
            }
        ]
    ).to_csv(deep, index=False)

    protected = tmp_path / "protected.csv"
    pd.DataFrame(
        [
            {
                "cell_id": "A",
                "checked": True,
                "finding_count": 1,
                "intersecting_count": 1,
                "legal_review_required": True,
                "max_overlap_ratio": 0.25,
                "nearest_constraint_km": 0.0,
            }
        ]
    ).to_csv(protected, index=False)

    flood = tmp_path / "flood.csv"
    pd.DataFrame(
        [
            {
                "cell_id": "A",
                "checked": True,
                "finding_count": 1,
                "max_severity": 3,
                "max_overlap_ratio": 0.10,
                "nearest_hazard_km": 0.0,
            }
        ]
    ).to_csv(flood, index=False)

    result = build_evidence_packets(
        deep_scan_csv=deep,
        sentinel_csv=None,
        protected_csv=protected,
        flood_csv=flood,
        output_dir=tmp_path / "out",
    )

    payload = json.loads(
        Path(result.output_master_json).read_text(encoding="utf-8")
    )
    packet = payload["candidates"][0]

    assert packet["planning_legal"]["protected_area"]["checked"] is True
    assert packet["planning_legal"]["protected_area"]["legal_review_required"] is True
    assert packet["planning_legal"]["eplan"]["checked"] is False
    assert packet["planning_legal"]["known"] is False
    assert packet["hazard"]["official_flood"]["checked"] is True
    assert packet["hazard"]["official_flood"]["max_severity"] == 3


def test_evidence_packet_marks_price_known_only_when_scan_says_known(tmp_path: Path):
    deep = tmp_path / "deep.csv"
    pd.DataFrame(
        [
            {
                "cell_id": "A",
                "center_lat": 40.0,
                "center_lon": 29.0,
                "urban_rank": 1,
                "acceleration_pp_per_year": 5.0,
                "cagr_2015_2020_pct": 12.0,
                "p90_slope_deg": 5.0,
                "nearest_catalyst_km": 4.0,
                "catalyst_stage_max": 4,
                "hard_veto": False,
                "max_hazard_severity": 2,
                "status": "PASS",
                "reasons": "",
            }
        ]
    ).to_csv(deep, index=False)

    sentinel = tmp_path / "sentinel.csv"
    pd.DataFrame(
        [{"cell_id": "A", "delta_ndvi": -0.1}]
    ).to_csv(sentinel, index=False)

    price = tmp_path / "price.csv"
    pd.DataFrame(
        [
            {
                "cell_id": "A",
                "checked": True,
                "known": True,
                "price_basis": "nominal",
                "used_rows": 12,
                "median_price_per_m2": 1500,
                "p25_price_per_m2": 1300,
                "p75_price_per_m2": 1700,
                "dispersion_ratio": 0.2667,
                "median_age_days": 120,
                "confidence_label": "MEDIUM",
                "reason": "",
            }
        ]
    ).to_csv(price, index=False)

    result = build_evidence_packets(
        deep_scan_csv=deep,
        sentinel_csv=sentinel,
        price_csv=price,
        output_dir=tmp_path / "out",
    )
    payload = json.loads(
        Path(result.output_master_json).read_text(encoding="utf-8")
    )
    packet = payload["candidates"][0]

    assert packet["price"]["checked"] is True
    assert packet["price"]["known"] is True
    assert packet["price"]["confidence_label"] == "MEDIUM"
    assert packet["evidence_coverage"]["coverage_pct"] == 85.7


def test_evidence_packet_marks_verified_planning_known(tmp_path: Path):
    deep = tmp_path / "deep.csv"
    pd.DataFrame(
        [{
            "cell_id": "A",
            "center_lat": 40.0,
            "center_lon": 29.0,
            "urban_rank": 1,
            "acceleration_pp_per_year": 5.0,
            "cagr_2015_2020_pct": 12.0,
            "p90_slope_deg": 5.0,
            "nearest_catalyst_km": 4.0,
            "catalyst_stage_max": 4,
            "hard_veto": False,
            "max_hazard_severity": 2,
            "status": "PASS",
            "reasons": "",
        }]
    ).to_csv(deep, index=False)

    planning = tmp_path / "planning.csv"
    pd.DataFrame(
        [{
            "cell_id": "A",
            "checked": True,
            "cdp_wms_covered": True,
            "cdp_wms_services": "csb_cdp_cb",
            "registry_match_count": 1,
            "active_plan_count": 1,
            "finalized_uip_nip_verified_count": 1,
            "planning_known": True,
            "matched_plan_ids": "UIP-123",
            "matched_plan_stages": "FINALIZED",
        }]
    ).to_csv(planning, index=False)

    result = build_evidence_packets(
        deep_scan_csv=deep,
        sentinel_csv=None,
        planning_csv=planning,
        output_dir=tmp_path / "out",
    )
    payload = json.loads(
        Path(result.output_master_json).read_text(encoding="utf-8")
    )
    packet = payload["candidates"][0]

    assert packet["planning_legal"]["known"] is True
    assert packet["planning_legal"]["eplan"]["checked"] is True
    assert packet["planning_legal"]["eplan"]["matched_plan_ids"] == "UIP-123"
    assert "planning_legal" not in packet["evidence_coverage"]["missing_layers"]


def test_official_flood_and_landslide_can_complete_core_hazard(tmp_path: Path):
    deep = tmp_path / "deep.csv"
    pd.DataFrame(
        [{
            "cell_id": "A",
            "center_lat": 40.0,
            "center_lon": 29.0,
            "urban_rank": 1,
            "acceleration_pp_per_year": 5.0,
            "cagr_2015_2020_pct": 12.0,
            "p90_slope_deg": 5.0,
            "nearest_catalyst_km": 4.0,
            "catalyst_stage_max": 4,
            "hard_veto": False,
            "max_hazard_severity": None,
            "status": "PASS_WITH_GAPS",
            "reasons": "hazard_unknown",
        }]
    ).to_csv(deep, index=False)

    flood = tmp_path / "flood.csv"
    pd.DataFrame(
        [{"cell_id": "A", "checked": True, "finding_count": 0, "max_severity": -1}]
    ).to_csv(flood, index=False)

    landslide = tmp_path / "landslide.csv"
    pd.DataFrame(
        [{"cell_id": "A", "checked": True, "finding_count": 0, "max_severity": -1}]
    ).to_csv(landslide, index=False)

    result = build_evidence_packets(
        deep_scan_csv=deep,
        sentinel_csv=None,
        flood_csv=flood,
        landslide_csv=landslide,
        output_dir=tmp_path / "out",
    )
    payload = json.loads(
        Path(result.output_master_json).read_text(encoding="utf-8")
    )
    packet = payload["candidates"][0]

    assert packet["hazard"]["known"] is True
    assert packet["hazard"]["official_flood"]["checked"] is True
    assert packet["hazard"]["official_landslide_inventory"]["checked"] is True
    assert packet["hazard"]["core_hazard_coverage"]["known"] is True
    assert "hazard" not in packet["evidence_coverage"]["missing_layers"]


def test_evidence_packet_includes_kgm_highway_sublayer(tmp_path: Path):
    deep = tmp_path / "deep.csv"
    pd.DataFrame(
        [{
            "cell_id": "A",
            "center_lat": 40.0,
            "center_lon": 29.0,
            "urban_rank": 1,
            "acceleration_pp_per_year": 5.0,
            "cagr_2015_2020_pct": 12.0,
            "p90_slope_deg": 5.0,
            "nearest_catalyst_km": 3.5,
            "catalyst_stage_max": 4,
            "hard_veto": False,
            "max_hazard_severity": 1,
            "status": "PASS",
            "reasons": "",
        }]
    ).to_csv(deep, index=False)

    highway = tmp_path / "kgm.csv"
    pd.DataFrame(
        [{
            "cell_id": "A",
            "status_checked": True,
            "geometry_registry_checked": True,
            "kgm_geometry_count": 1,
            "linked_project_count": 1,
            "spatial_known": True,
            "nearest_project_id": "road:kgm:test",
            "nearest_project_name": "Test Otoyolu",
            "nearest_project_stage": 4,
            "nearest_project_distance_km": 3.5,
            "nearest_influence_code": "NEAR",
            "nearest_influence_label": "Yakın",
            "nearest_evidence_complete": True,
        }]
    ).to_csv(highway, index=False)

    result = build_evidence_packets(
        deep_scan_csv=deep,
        kgm_highway_csv=highway,
        output_dir=tmp_path / "out",
    )
    payload = json.loads(
        Path(result.output_master_json).read_text(encoding="utf-8")
    )
    road = payload["candidates"][0]["catalyst"]["kgm_highway"]

    assert road["status_checked"] is True
    assert road["spatial_known"] is True
    assert road["nearest_project_id"] == "road:kgm:test"
    assert road["nearest_project_stage"] == 4
