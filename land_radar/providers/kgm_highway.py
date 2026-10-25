from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import PurePosixPath
import re
from typing import Iterable
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
import requests

from ..catalyst import Catalyst, CatalystStage
from ..models import Evidence


KGM_HIGHWAY_INDEX_URL = (
    "https://www.kgm.gov.tr/Sayfalar/KGM/SiteTr/Projeler/"
    "Projeler-Otoyol.aspx"
)


class KGMHighwayProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class KGMHighwayProject:
    project_id: str
    name: str
    detail_url: str
    stage: CatalystStage
    stage_claim: str
    observed_date: date


_TR_FOLD = str.maketrans({
    "ı": "i", "İ": "I",
    "ş": "s", "Ş": "S",
    "ğ": "g", "Ğ": "G",
    "ü": "u", "Ü": "U",
    "ö": "o", "Ö": "O",
    "ç": "c", "Ç": "C",
})


def _clean(value: str) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def _fold(value: str) -> str:
    return _clean(value).translate(_TR_FOLD).casefold()


def _slug_from_url(url: str) -> str:
    path = PurePosixPath(urlparse(url).path)
    stem = path.stem.strip()
    if not stem:
        raise ValueError(f"Cannot derive KGM project id from URL: {url}")
    return re.sub(r"[^a-z0-9]+", "-", _fold(stem)).strip("-")


def parse_project_index(
    html: str,
    *,
    base_url: str = KGM_HIGHWAY_INDEX_URL,
) -> list[tuple[str, str]]:
    """Parse official KGM highway-project links from the index page."""
    soup = BeautifulSoup(html, "html.parser")
    records: list[tuple[str, str]] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a"):
        name = _clean(anchor.get_text(" ", strip=True))
        href = str(anchor.get("href") or "").strip()
        if not name or not href:
            continue

        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.hostname not in {"kgm.gov.tr", "www.kgm.gov.tr"}:
            continue

        folded_path = _fold(parsed.path)
        if "/projeler/otoyolprojeleri/" not in folded_path:
            continue
        if not parsed.path.lower().endswith(".aspx"):
            continue

        project_id = _slug_from_url(absolute)
        if project_id in seen:
            continue
        seen.add(project_id)
        records.append((name, absolute))

    return records


_CONSTRUCTION_PATTERNS = (
    re.compile(r"projede\s+yapim\s+calismalari\s+devam\s+etmektedir"),
    re.compile(r"yapim\s+calismalari\s+(?:devam\s+etmekte|surmektedir|surdurulmektedir)"),
    re.compile(r"insa(?:at)?\s+calismalari\s+(?:devam\s+etmekte|surmektedir|surdurulmektedir)"),
)
_COMPLETED_PATTERNS = (
    re.compile(r"proje[^.]{0,140}?isletmeye\s+acilmistir"),
    re.compile(r"proje[^.]{0,140}?hizmete\s+acilmistir"),
    re.compile(r"proje[^.]{0,140}?tamamlanmistir"),
    re.compile(r"proje[^.]{0,140}?tamamlanarak[^.]{0,100}?isletmeye\s+acil"),
)
_TENDER_PATTERNS = (
    re.compile(r"ihalesi[^.]{0,100}?yapilmistir"),
    re.compile(r"uygulama\s+sozlesmesi[^.]{0,120}?imzalan"),
    re.compile(r"sozlesme[^.]{0,100}?yururluge\s+girm"),
)
_APPROVAL_PATTERNS = (
    re.compile(r"proje[^.]{0,100}?onaylan"),
    re.compile(r"ced[^.]{0,100}?olumlu"),
)


def infer_stage(detail_text: str) -> tuple[CatalystStage, str]:
    """Infer only explicit KGM project lifecycle claims.

    Precedence is construction > completed > tender > approval > official
    intent. Construction is checked before completion because a page can
    mention a completed connecting motorway while describing a current project.
    Completion patterns are deliberately restricted to sentences whose subject
    includes the word 'proje'.
    """
    text = _fold(detail_text)

    for pattern in _CONSTRUCTION_PATTERNS:
        match = pattern.search(text)
        if match:
            return (
                CatalystStage.CONSTRUCTION_STARTED,
                _clean(detail_text)[max(0, match.start() - 80): match.end() + 120],
            )

    for pattern in _COMPLETED_PATTERNS:
        match = pattern.search(text)
        if match:
            return (
                CatalystStage.COMPLETED,
                _clean(detail_text)[max(0, match.start() - 80): match.end() + 120],
            )

    for pattern in _TENDER_PATTERNS:
        match = pattern.search(text)
        if match:
            return (
                CatalystStage.BUDGET_OR_TENDER,
                _clean(detail_text)[max(0, match.start() - 80): match.end() + 120],
            )

    for pattern in _APPROVAL_PATTERNS:
        match = pattern.search(text)
        if match:
            return (
                CatalystStage.PLAN_OR_APPROVAL,
                _clean(detail_text)[max(0, match.start() - 80): match.end() + 120],
            )

    return (
        CatalystStage.OFFICIAL_INTENT,
        "KGM Otoyol Projeleri sayfasında resmî proje olarak yayımlanıyor; "
        "daha ileri aşama için açık ifade bulunamadı.",
    )


def parse_project_detail(
    name: str,
    detail_url: str,
    html: str,
    *,
    observed_date: date | None = None,
) -> KGMHighwayProject:
    soup = BeautifulSoup(html, "html.parser")

    # KGM SharePoint pages contain substantial navigation text. Prefer the
    # page-content area when identifiable; otherwise use full visible text.
    content = soup.find(id=re.compile(r"(pagecontent|content)", re.I))
    text = _clean(
        (content or soup).get_text(" ", strip=True)
    )
    if len(text) < 20:
        raise KGMHighwayProviderError(
            f"KGM detail page has no usable text: {detail_url}"
        )

    stage, claim = infer_stage(text)
    return KGMHighwayProject(
        project_id=f"road:kgm:{_slug_from_url(detail_url)}",
        name=_clean(name),
        detail_url=detail_url,
        stage=stage,
        stage_claim=claim,
        observed_date=observed_date or date.today(),
    )


def fetch_highway_projects(
    *,
    index_url: str = KGM_HIGHWAY_INDEX_URL,
    timeout: float = 30.0,
    session: requests.Session | None = None,
    observed_date: date | None = None,
) -> list[KGMHighwayProject]:
    client = session or requests.Session()
    try:
        response = client.get(
            index_url,
            timeout=timeout,
            headers={"User-Agent": "LAND-RADAR/0.19 kgm-project-research"},
        )
        response.raise_for_status()
        response.encoding = response.apparent_encoding or response.encoding
    except requests.RequestException as exc:
        raise KGMHighwayProviderError(
            f"KGM highway index request failed: {exc}"
        ) from exc

    links = parse_project_index(response.text, base_url=index_url)
    if not links:
        raise KGMHighwayProviderError(
            "KGM highway index returned no parseable project links"
        )

    projects: list[KGMHighwayProject] = []
    for name, detail_url in links:
        try:
            detail = client.get(
                detail_url,
                timeout=timeout,
                headers={"User-Agent": "LAND-RADAR/0.19 kgm-project-research"},
            )
            detail.raise_for_status()
            detail.encoding = detail.apparent_encoding or detail.encoding
        except requests.RequestException as exc:
            raise KGMHighwayProviderError(
                f"KGM highway detail request failed for {name}: {exc}"
            ) from exc

        projects.append(
            parse_project_detail(
                name,
                detail_url,
                detail.text,
                observed_date=observed_date,
            )
        )

    return projects


def filter_project_keywords(
    records: Iterable[KGMHighwayProject],
    keywords: Iterable[str],
) -> list[KGMHighwayProject]:
    tokens = [_fold(token) for token in keywords if str(token).strip()]
    if not tokens:
        return list(records)

    return [
        record
        for record in records
        if any(token in _fold(record.name) for token in tokens)
    ]


def record_to_catalyst(record: KGMHighwayProject) -> Catalyst:
    evidence = [
        Evidence(
            source="Karayolları Genel Müdürlüğü / Otoyol Projeleri",
            claim=record.stage_claim,
            observed_date=record.observed_date,
            url=record.detail_url,
            confidence=95.0,
        )
    ]
    catalyst = Catalyst(
        catalyst_id=record.project_id,
        name=record.name,
        category="highway_project",
        stage=record.stage,
        evidence=evidence,
    )
    catalyst.validate()
    return catalyst
