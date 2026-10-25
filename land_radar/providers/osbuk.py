from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Iterable

from bs4 import BeautifulSoup
import requests

from ..catalyst import Catalyst, CatalystStage
from ..models import Evidence


OSBUK_LIST_URL = "https://osbuk.org/view/osb/osbliste.php"


class OSBUKProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class OSBRecord:
    province: str
    name: str
    status: str
    address: str | None
    source_url: str = OSBUK_LIST_URL


_STATUS_PATTERNS: tuple[tuple[re.Pattern[str], CatalystStage], ...] = (
    (re.compile(r"İŞLETMEDE|FAALİYETTE", re.I), CatalystStage.COMPLETED),
    (re.compile(r"ALTYAPI\s+HAZIRLANIYOR", re.I), CatalystStage.CONSTRUCTION_STARTED),
    (re.compile(r"KAMULAŞTIRMA\s+YAPILIYOR", re.I), CatalystStage.PLAN_OR_APPROVAL),
    (re.compile(r"PLANLAMA\s+AŞAMASINDA", re.I), CatalystStage.OFFICIAL_INTENT),
)


def status_to_stage(status: str) -> CatalystStage:
    normalized = " ".join(status.split())
    for pattern, stage in _STATUS_PATTERNS:
        if pattern.search(normalized):
            return stage
    return CatalystStage.NONE_OR_RUMOR


def _clean(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())


def parse_osb_list_html(html: str) -> list[OSBRecord]:
    soup = BeautifulSoup(html, "html.parser")
    records: list[OSBRecord] = []

    for row in soup.find_all("tr"):
        cells = [_clean(cell.get_text(" ", strip=True)) for cell in row.find_all("td")]
        if len(cells) < 4:
            continue

        status_index = None
        for idx, value in enumerate(cells):
            if status_to_stage(value) != CatalystStage.NONE_OR_RUMOR:
                status_index = idx
                break

        if status_index is None:
            continue

        # Current OSBÜK list layout starts with sequence number, province, OSB name.
        # We keep the parser conservative: if those fields are not present, skip.
        if len(cells) < 3:
            continue
        province = cells[1]
        name = cells[2]
        status = cells[status_index]

        address = None
        if len(cells) >= 8:
            candidate = cells[-1]
            if candidate and "@" not in candidate and not candidate.lower().startswith("www"):
                address = candidate

        if province and name:
            records.append(
                OSBRecord(
                    province=province,
                    name=name,
                    status=status,
                    address=address,
                )
            )

    return records


def fetch_osb_list(
    *,
    endpoint: str = OSBUK_LIST_URL,
    timeout: float = 30.0,
    session: requests.Session | None = None,
) -> list[OSBRecord]:
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
        raise OSBUKProviderError(f"OSBÜK list request failed: {exc}") from exc

    records = parse_osb_list_html(response.text)
    if not records:
        raise OSBUKProviderError("OSBÜK list returned no parseable OSB records")
    return records


def filter_provinces(
    records: Iterable[OSBRecord],
    provinces: Iterable[str],
) -> list[OSBRecord]:
    wanted = {p.casefold().strip() for p in provinces}
    return [r for r in records if r.province.casefold().strip() in wanted]


def record_to_catalyst(
    record: OSBRecord,
    *,
    observed_date: date | None = None,
) -> Catalyst:
    stage = status_to_stage(record.status)
    evidence: list[Evidence] = []

    if stage > CatalystStage.NONE_OR_RUMOR:
        evidence.append(
            Evidence(
                source="OSBÜK OSB listesi",
                claim=(
                    f"{record.province} / {record.name} OSB durumu: "
                    f"{record.status}"
                ),
                observed_date=observed_date or date.today(),
                url=record.source_url,
                confidence=80.0,
            )
        )

    catalyst = Catalyst(
        catalyst_id=f"osb:{record.province}:{record.name}".casefold(),
        name=record.name,
        category="industrial_osb",
        stage=stage,
        evidence=evidence,
    )
    catalyst.validate()
    return catalyst
