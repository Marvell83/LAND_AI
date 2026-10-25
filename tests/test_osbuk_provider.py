from datetime import date

from land_radar.catalyst import CatalystStage
from land_radar.providers.osbuk import (
    OSBRecord,
    filter_provinces,
    parse_osb_list_html,
    record_to_catalyst,
    status_to_stage,
)


def test_status_mapping_is_conservative():
    assert status_to_stage("İŞLETMEDE (FAALİYETTE)") == CatalystStage.COMPLETED
    assert status_to_stage("ALTYAPI HAZIRLANIYOR") == CatalystStage.CONSTRUCTION_STARTED
    assert status_to_stage("KAMULAŞTIRMA YAPILIYOR") == CatalystStage.PLAN_OR_APPROVAL
    assert status_to_stage("PLANLAMA AŞAMASINDA") == CatalystStage.OFFICIAL_INTENT
    assert status_to_stage("BİLİNMİYOR") == CatalystStage.NONE_OR_RUMOR


def test_parse_osbuk_html():
    html = """
    <table>
      <tr><th>No</th><th>İl</th><th>OSB</th><th>Telefon</th><th>Durum</th><th>E-posta</th><th>Web</th><th>Adres</th></tr>
      <tr>
        <td>1</td><td>Bolu</td><td>Yeniçağa</td><td>123</td>
        <td>ALTYAPI HAZIRLANIYOR</td><td>x@example.com</td><td>www.example.com</td>
        <td>Yeniçağa / Bolu</td>
      </tr>
      <tr>
        <td>2</td><td>Balıkesir</td><td>Test OSB</td><td>456</td>
        <td>İŞLETMEDE (FAALİYETTE)</td><td>y@example.com</td><td>www.example.org</td>
        <td>Balıkesir</td>
      </tr>
    </table>
    """
    records = parse_osb_list_html(html)
    assert len(records) == 2
    assert records[0].province == "Bolu"
    assert records[0].name == "Yeniçağa"
    assert records[0].address == "Yeniçağa / Bolu"


def test_filter_and_convert_to_catalyst():
    records = [
        OSBRecord("Bolu", "Yeniçağa", "ALTYAPI HAZIRLANIYOR", "Bolu"),
        OSBRecord("Balıkesir", "X", "PLANLAMA AŞAMASINDA", "Balıkesir"),
    ]
    filtered = filter_provinces(records, ["Bolu"])
    assert len(filtered) == 1

    catalyst = record_to_catalyst(filtered[0], observed_date=date(2026, 10, 25))
    assert catalyst.stage == CatalystStage.CONSTRUCTION_STARTED
    assert len(catalyst.evidence) == 1
    assert catalyst.evidence[0].observed_date == date(2026, 10, 25)
