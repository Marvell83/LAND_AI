from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Iterable

from bs4 import BeautifulSoup
import requests

from ..catalyst import Catalyst, CatalystStage
from ..models import Evidence


AYGM_RAIL_URL = "https://aygm.uab.gov.tr/demiryollari-daire-baskanliklari"


class AYGMRailProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class RailProjectRecord:
    name: str
    status_group: str
    source_url: str = AYGM_RAIL_URL


_GROUP_TO_STAGE = {
    "devam eden": CatalystStage.CONSTRUCTION_STARTED,
    "tamamlanan": CatalystStage.COMPLETED,
    "planlanan": CatalystStage.OFFICIAL_INTENT,
}


_TR_FOLD = str.maketrans({
    "ı": "i", "İ": "I",
    "ş": "s", "Ş": "S",
    "ğ": "g", "Ğ": "G",
    "ü": "u", "Ü": "U",
    "ö": "o", "Ö": "O",
    "ç": "c", "Ç": "C",
})


def normalize_project_name(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def _fold(value: str) -> str:
    return normalize_project_name(value).translate(_TR_FOLD).casefold()


def status_group_to_stage(group: str) -> CatalystStage:
    normalized = _fold(group)
    for key, stage in _GROUP_TO_STAGE.items():
        if key in normalized:
            return stage
    return CatalystStage.NONE_OR_RUMOR


def _heading_group(text: str) -> str | None:
    normalized = _fold(text)
    if "devam eden projeler" in normalized:
        return "devam eden"
    if "tamamlanan projeler" in normalized:
        return "tamamlanan"
    if "planlanan projeler" in normalized:
        return "planlanan"
    return None


def parse_aygm_rail_html(html: str) -> list[RailProjectRecord]:
    """Parse AYGM railway project groups conservatively.

    The official page groups project links beneath three headings. We only
    accept anchor text encountered after one of those headings and stop when
    another major section begins.
    """
    soup = BeautifulSoup(html, "html.parser")
    records: list[RailProjectRecord] = []
    current_group: str | None = None

    for node in soup.find_all(["h1", "h2", "h3", "h4", "h5", "strong", "p", "a"]):
        text = normalize_project_name(node.get_text(" ", strip=True))
        if not text:
            continue

        group = _heading_group(text)
        if group is not None:
            current_group = group
            continue

        lower = _fold(text)
        if any(
            marker in lower
            for marker in (
                "iletisim",
                "organizasyon semasi",
                "adres:",
            )
        ):
            if node.name != "a":
                current_group = None

        if node.name == "a" and current_group:
            href = (node.get("href") or "").strip()
            # Project links on the AYGM page have meaningful names. Avoid menu,
            # social and empty anchors.
            if len(text) < 8:
                continue
            if _fold(text) in {
                "ana sayfa",
                "tumunu gor",
                "detay",
                "iletisim",
            }:
                continue

            records.append(
                RailProjectRecord(
                    name=text,
                    status_group=current_group,
                    source_url=(
                        href
                        if href.startswith("http")
                        else AYGM_RAIL_URL
                    ),
                )
            )

    # De-duplicate repeated responsive/mobile anchors while preserving order.
    seen: set[tuple[str, str]] = set()
    unique: list[RailProjectRecord] = []
    for record in records:
        key = (record.name.casefold(), record.status_group)
        if key not in seen:
            seen.add(key)
            unique.append(record)
    return unique


def fetch_rail_projects(
    *,
    endpoint: str = AYGM_RAIL_URL,
    timeout: float = 30.0,
    session: requests.Session | None = None,
) -> list[RailProjectRecord]:
    client = session or requests.Session()
    try:
        response = client.get(
            endpoint,
            timeout=timeout,
            headers={"User-Agent": "LAND-RADAR/0.5 catalyst-research"},
        )
        response.raise_for_status()
        response.encoding = response.apparent_encoding or response.encoding
    except requests.RequestException as exc:
        raise AYGMRailProviderError(f"AYGM railway request failed: {exc}") from exc

    records = parse_aygm_rail_html(response.text)
    if not records:
        raise AYGMRailProviderError("AYGM page returned no parseable railway projects")
    return records


def filter_project_keywords(
    records: Iterable[RailProjectRecord],
    keywords: Iterable[str],
) -> list[RailProjectRecord]:
    tokens = [_fold(token) for token in keywords if token.strip()]
    if not tokens:
        return list(records)

    result: list[RailProjectRecord] = []
    for record in records:
        haystack = _fold(record.name)
        if any(token in haystack for token in tokens):
            result.append(record)
    return result


def record_to_catalyst(
    record: RailProjectRecord,
    *,
    observed_date: date | None = None,
) -> Catalyst:
    stage = status_group_to_stage(record.status_group)
    evidence: list[Evidence] = []

    if stage > CatalystStage.NONE_OR_RUMOR:
        evidence.append(
            Evidence(
                source="AYGM Demiryolları Daire Başkanlıkları",
                claim=(
                    f"{record.name} resmî proje grubu: "
                    f"{record.status_group}"
                ),
                observed_date=observed_date or date.today(),
                url=record.source_url,
                confidence=90.0,
            )
        )

    catalyst = Catalyst(
        catalyst_id=f"rail:{record.name}".casefold(),
        name=record.name,
        category="rail",
        stage=stage,
        evidence=evidence,
    )
    catalyst.validate()
    return catalyst
