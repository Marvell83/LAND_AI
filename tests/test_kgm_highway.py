from datetime import date

from land_radar.catalyst import CatalystStage
from land_radar.providers.kgm_highway import (
    infer_stage,
    parse_project_detail,
    parse_project_index,
    record_to_catalyst,
)


def test_parse_project_index_accepts_only_kgm_detail_pages():
    html = """
    <html><body>
      <a href="/Sayfalar/KGM/SiteTr/Projeler/OtoyolProjeleri/KinaliMalkara.aspx">
        KINALI - MALKARA OTOYOLU
      </a>
      <a href="/Sayfalar/KGM/SiteTr/Projeler/Projeler-Otoyol.aspx">
        Otoyol Projeleri
      </a>
      <a href="https://example.com/x.aspx">External</a>
    </body></html>
    """
    result = parse_project_index(html)
    assert len(result) == 1
    assert result[0][0] == "KINALI - MALKARA OTOYOLU"


def test_stage_construction_has_precedence():
    stage, _ = infer_stage(
        "İhalenin ardından uygulama sözleşmesi imzalanmıştır. "
        "Projede yapım çalışmaları devam etmektedir."
    )
    assert stage == CatalystStage.CONSTRUCTION_STARTED


def test_stage_completed_requires_explicit_project_claim():
    stage, _ = infer_stage(
        "Proje 18 Mart 2022 tarihinde işletmeye açılmıştır."
    )
    assert stage == CatalystStage.COMPLETED


def test_unstaged_official_project_stays_official_intent():
    stage, _ = infer_stage(
        "Otoyol güzergahı kuzeyden ilerleyerek bağlantı yolunda sonlanacaktır."
    )
    assert stage == CatalystStage.OFFICIAL_INTENT


def test_detail_converts_to_evidenced_catalyst():
    html = """
    <html><body>
      <div id="content">
        ANKARA-KIRIKKALE-DELİCE OTOYOLU PROJESİ.
        İhalesi 14.12.2023 tarihinde yapılmıştır.
        Projede yapım çalışmaları devam etmektedir.
      </div>
    </body></html>
    """
    record = parse_project_detail(
        "Ankara-Kırıkkale-Delice Otoyolu",
        "https://www.kgm.gov.tr/Sayfalar/KGM/SiteTr/Projeler/OtoyolProjeleri/AnkaraKirikkaleDelice.aspx",
        html,
        observed_date=date(2026, 10, 25),
    )
    catalyst = record_to_catalyst(record)

    assert record.stage == CatalystStage.CONSTRUCTION_STARTED
    assert catalyst.catalyst_id == "road:kgm:ankarakirikkaledelice"
    assert catalyst.evidence
    assert catalyst.evidence[0].confidence == 95.0


def test_related_completed_road_does_not_complete_current_project():
    stage, _ = infer_stage(
        "Kınalı-Malkara Otoyolu güzergahı batı yönünde ilerlemektedir. "
        "Malkara-Çanakkale Otoyolu yapım çalışmaları tamamlanarak işletmeye açılan "
        "kesime bağlanmaktadır."
    )
    assert stage == CatalystStage.OFFICIAL_INTENT
