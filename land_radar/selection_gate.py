from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import pandas as pd


DEFAULT_REQUIRED_LAYERS = (
    "urban_history",
    "terrain",
    "hazard",
    "catalyst",
    "sentinel_recent_change",
    "planning_legal",
    "price",
)


@dataclass(frozen=True)
class SelectionGateResult:
    candidate_count: int
    eligible_count: int
    target_count: int
    selection_ready: bool
    output_csv: str
    summary_json: str


def _layer_known(packet: dict, layer: str) -> bool:
    if layer == "urban_history":
        return (
            packet.get("urban_history", {}).get("acceleration_pp_per_year")
            is not None
        )
    if layer == "terrain":
        return bool(packet.get("terrain", {}).get("known", False))
    if layer == "hazard":
        return bool(packet.get("hazard", {}).get("known", False))
    if layer == "catalyst":
        return bool(packet.get("catalyst", {}).get("known", False))
    if layer == "sentinel_recent_change":
        return packet.get("sentinel_recent_change") is not None
    if layer == "planning_legal":
        return bool(packet.get("planning_legal", {}).get("known", False))
    if layer == "price":
        return bool(packet.get("price", {}).get("known", False))
    raise ValueError(f"Unsupported required evidence layer: {layer}")


def run_selection_gate(
    *,
    evidence_json: str | Path = "data/output/evidence_packets/candidate_evidence_packets.json",
    output_dir: str | Path = "data/output/selection_gate",
    target_count: int = 10,
    required_layers: tuple[str, ...] = DEFAULT_REQUIRED_LAYERS,
) -> SelectionGateResult:
    if target_count <= 0:
        raise ValueError("target_count must be positive")

    path = Path(evidence_json)
    if not path.exists():
        raise FileNotFoundError(f"Evidence packet JSON not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    candidates = payload.get("candidates") or []
    if not isinstance(candidates, list):
        raise ValueError("Evidence packet JSON has invalid candidates payload")

    rows: list[dict] = []
    blocker_counts = {layer: 0 for layer in required_layers}
    blocker_counts["hard_veto"] = 0
    blocker_counts["funnel_drop"] = 0

    for packet in candidates:
        cell_id = str(packet.get("cell_id") or "")
        funnel = packet.get("funnel") or {}
        status = str(funnel.get("status") or "")
        hard_veto = bool(
            (packet.get("hazard") or {}).get("hard_veto", False)
        )

        missing = [
            layer
            for layer in required_layers
            if not _layer_known(packet, layer)
        ]
        blockers: list[str] = []

        if status == "DROP":
            blockers.append("funnel_drop")
            blocker_counts["funnel_drop"] += 1
        if hard_veto:
            blockers.append("hard_veto")
            blocker_counts["hard_veto"] += 1

        for layer in missing:
            blockers.append(f"missing:{layer}")
            blocker_counts[layer] += 1

        eligible = not blockers

        rows.append(
            {
                "cell_id": cell_id,
                "funnel_status": status,
                "hard_veto": hard_veto,
                "eligible_for_top10_review": eligible,
                "missing_required_layers": ", ".join(missing),
                "blockers": ", ".join(blockers),
                "evidence_coverage_pct": (
                    (packet.get("evidence_coverage") or {}).get(
                        "coverage_pct"
                    )
                ),
                "urban_rank": funnel.get("urban_rank"),
            }
        )

    frame = pd.DataFrame(rows)
    eligible_count = int(
        frame["eligible_for_top10_review"].fillna(False).sum()
        if not frame.empty
        else 0
    )
    selection_ready = eligible_count >= target_count

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_csv = output_dir / "selection_gate.csv"
    summary_json = output_dir / "selection_gate_summary.json"

    frame.to_csv(output_csv, index=False, encoding="utf-8-sig")
    summary_json.write_text(
        json.dumps(
            {
                "candidate_count": len(frame),
                "eligible_count": eligible_count,
                "target_count": target_count,
                "selection_ready": selection_ready,
                "required_layers": list(required_layers),
                "blocker_counts": blocker_counts,
                "warning": (
                    "This gate does not rank or select investments. It only "
                    "checks whether enough candidates have the required evidence "
                    "to begin a Top-10 review."
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return SelectionGateResult(
        candidate_count=len(frame),
        eligible_count=eligible_count,
        target_count=target_count,
        selection_ready=selection_ready,
        output_csv=str(output_csv),
        summary_json=str(summary_json),
    )
