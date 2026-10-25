from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

import pandas as pd

from .grid import GridCell
from .providers.kgm_highway import (
    KGMHighwayProject,
    fetch_highway_projects,
    record_to_catalyst,
)
from .spatial.batch import batch_link_catalysts
from .spatial.registry import load_geometry_registry


@dataclass(frozen=True)
class KGMHighwayScanResult:
    candidate_count: int
    project_count: int
    geometry_project_count: int
    linked_candidate_count: int
    projects_csv: str
    links_csv: str
    candidate_csv: str
    summary_json: str


def _cells(path: str | Path, cell_km: float) -> list[GridCell]:
    frame = pd.read_csv(path)
    required = {"cell_id", "center_lat", "center_lon"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(
            "Candidate CSV missing columns: " + ", ".join(missing)
        )
    return [
        GridCell(
            cell_id=str(row.cell_id),
            center_lat=float(row.center_lat),
            center_lon=float(row.center_lon),
            size_km=cell_km,
        )
        for row in frame.itertuples(index=False)
    ]


def _project_row(project: KGMHighwayProject) -> dict:
    return {
        "project_id": project.project_id,
        "name": project.name,
        "stage": int(project.stage),
        "stage_name": project.stage.name,
        "stage_claim": project.stage_claim,
        "detail_url": project.detail_url,
        "observed_date": project.observed_date.isoformat(),
    }


def run_kgm_highway_scan(
    *,
    candidate_csv: str | Path = "data/output/deep_scan/deep_scan_top30.csv",
    geometry_registry_path: str | Path = "data/processed/geometry_registry.geojson",
    output_dir: str | Path = "data/output/kgm_highway_scan",
    cell_km: float = 5.0,
    max_distance_km: float = 30.0,
    projects: list[KGMHighwayProject] | None = None,
) -> KGMHighwayScanResult:
    if max_distance_km <= 0:
        raise ValueError("max_distance_km must be positive")

    cells = _cells(candidate_csv, cell_km)
    if not cells:
        raise ValueError("Candidate CSV is empty")

    project_list = list(projects) if projects is not None else fetch_highway_projects()
    catalysts = {
        project.project_id: record_to_catalyst(project)
        for project in project_list
    }

    registry_path = Path(geometry_registry_path)
    registry = load_geometry_registry(registry_path) if registry_path.exists() else []
    kgm_entries = [
        entry
        for entry in registry
        if entry.catalyst_id.startswith("road:kgm:")
    ]
    geometry_project_ids = {
        entry.catalyst_id
        for entry in kgm_entries
    }

    spatial = batch_link_catalysts(
        cells,
        catalysts,
        kgm_entries,
        max_distance_km=max_distance_km,
    )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    projects_csv = output_dir / "kgm_highway_projects.csv"
    links_csv = output_dir / "kgm_highway_links.csv"
    candidate_csv_out = output_dir / "kgm_highway_top30.csv"
    summary_json = output_dir / "kgm_highway_scan_summary.json"

    pd.DataFrame(
        [_project_row(project) for project in project_list]
    ).to_csv(
        projects_csv,
        index=False,
        encoding="utf-8-sig",
    )

    link_rows = [asdict(link) for link in spatial.links]
    pd.DataFrame(link_rows).to_csv(
        links_csv,
        index=False,
        encoding="utf-8-sig",
    )

    links_by_cell: dict[str, list] = {}
    for link in spatial.links:
        links_by_cell.setdefault(link.cell_id, []).append(link)

    candidate_rows = []
    for cell in cells:
        links = sorted(
            links_by_cell.get(cell.cell_id, []),
            key=lambda item: (
                item.distance_km,
                -item.catalyst_stage,
                item.catalyst_id,
            ),
        )
        nearest = links[0] if links else None
        candidate_rows.append(
            {
                "cell_id": cell.cell_id,
                "status_checked": True,
                "geometry_registry_checked": registry_path.exists(),
                "kgm_geometry_count": len(geometry_project_ids),
                "linked_project_count": len(links),
                "spatial_known": nearest is not None,
                "nearest_project_id": (
                    nearest.catalyst_id if nearest else None
                ),
                "nearest_project_name": (
                    nearest.catalyst_name if nearest else None
                ),
                "nearest_project_stage": (
                    nearest.catalyst_stage if nearest else None
                ),
                "nearest_project_distance_km": (
                    nearest.distance_km if nearest else None
                ),
                "nearest_influence_code": (
                    nearest.influence_code if nearest else None
                ),
                "nearest_influence_label": (
                    nearest.influence_label if nearest else None
                ),
                "nearest_evidence_complete": (
                    nearest.evidence_complete if nearest else False
                ),
            }
        )

    pd.DataFrame(candidate_rows).to_csv(
        candidate_csv_out,
        index=False,
        encoding="utf-8-sig",
    )

    linked_candidate_count = sum(
        row["spatial_known"]
        for row in candidate_rows
    )
    summary_json.write_text(
        json.dumps(
            {
                "candidate_count": len(cells),
                "project_count": len(project_list),
                "geometry_project_count": len(geometry_project_ids),
                "linked_candidate_count": linked_candidate_count,
                "max_distance_km": max_distance_km,
                "missing_status_for_geometry": list(
                    spatial.missing_catalysts
                ),
                "projects_without_geometry": list(
                    spatial.missing_geometries
                ),
                "warning": (
                    "KGM project status and route geometry are separate evidence "
                    "channels. No distance is calculated without a geometry-registry "
                    "entry matching the KGM project id."
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return KGMHighwayScanResult(
        candidate_count=len(cells),
        project_count=len(project_list),
        geometry_project_count=len(geometry_project_ids),
        linked_candidate_count=int(linked_candidate_count),
        projects_csv=str(projects_csv),
        links_csv=str(links_csv),
        candidate_csv=str(candidate_csv_out),
        summary_json=str(summary_json),
    )
