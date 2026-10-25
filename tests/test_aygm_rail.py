from datetime import date

from land_radar.catalyst import CatalystStage
from land_radar.providers.aygm_rail import (
    RailProjectRecord,
    filter_project_keywords,
    parse_aygm_rail_html,
    record_to_catalyst,
    status_group_to_stage,
)


def test_status_groups_map_conservatively():
    assert status_group_to_stage("devam eden") == CatalystStage.CONSTRUCTION_STARTED
    assert status_group_to_stage("tamamlanan") == CatalystStage.COMPLETED
    assert status_group_to_stage("planlanan") == CatalystStage.OFFICIAL_INTENT
    assert status_group_to_stage("belirsiz") == CatalystStage.NONE_OR_RUMOR


def test_parse_grouped_project_links():
    html = """
    <h3>DEVAM EDEN PROJELER</h3>
    <a href="/bandirma-bursa">BANDIRMA-BURSA-YENİŞEHİR-OSMANELİ HIZLI TREN PROJESİ</a>
    <a href="/ankara-izmir">ANKARA-İZMİR HIZLI TREN PROJESİ</a>
    <h3>TAMAMLANAN PROJELER</h3>
    <a href="/kemalpasa">KEMALPAŞA ORGANİZE SANAYİ BÖLGESİ DEMİRYOLU BAĞLANTISI</a>
    <h3>PLANLANAN PROJELER</h3>
    <a href="/super-hizli">ANKARA-İSTANBUL SÜPER HIZLI TREN PROJESİ</a>
    <h3>İLETİŞİM</h3>
    <a href="/contact">İletişim bilgileri</a>
    """
    records = parse_aygm_rail_html(html)
    assert len(records) == 4
    assert records[0].status_group == "devam eden"
    assert records[2].status_group == "tamamlanan"
    assert records[3].status_group == "planlanan"


def test_filter_and_convert():
    records = [
        RailProjectRecord("BANDIRMA-BURSA-YENİŞEHİR-OSMANELİ HIZLI TREN PROJESİ", "devam eden"),
        RailProjectRecord("ANKARA-İZMİR HIZLI TREN PROJESİ", "devam eden"),
    ]
    filtered = filter_project_keywords(records, ["bandırma", "bursa"])
    assert len(filtered) == 1

    catalyst = record_to_catalyst(filtered[0], observed_date=date(2026, 10, 25))
    assert catalyst.stage == CatalystStage.CONSTRUCTION_STARTED
    assert catalyst.evidence[0].confidence == 90.0
